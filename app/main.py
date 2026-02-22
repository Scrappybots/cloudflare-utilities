import os
import asyncio
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, selectinload
import httpx

# --- Configuration ---
DATABASE_URL = "sqlite+aiosqlite:///./dns_manager.db"

# --- Database Setup ---
Base = declarative_base()

class Zone(Base):
    __tablename__ = "zones"
    id = Column(String, primary_key=True)
    name = Column(String, index=True)
    status = Column(String)
    records = relationship("Record", back_populates="zone", cascade="all, delete-orphan")

class Record(Base):
    __tablename__ = "records"
    id = Column(String, primary_key=True)
    zone_id = Column(String, ForeignKey("zones.id"))
    type = Column(String, index=True)
    name = Column(String, index=True)
    content = Column(String)
    proxied = Column(Boolean)
    ttl = Column(Integer)
    zone = relationship("Zone", back_populates="records")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# --- App Setup ---
app = FastAPI(title="Cloudflare DNS Utility")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# --- Cloudflare Logic ---

class CFConfig(BaseModel):
    api_token: str

async def fetch_zones(client: httpx.AsyncClient):
    zones = []
    page = 1
    while True:
        try:
            response = await client.get(f"https://api.cloudflare.com/client/v4/zones?page={page}&per_page=50")
            response.raise_for_status()
            data = response.json()
            if not data['success']:
                break
            zones.extend(data['result'])
            info = data.get('result_info', {})
            if page >= info.get('total_pages', 1):
                break
            page += 1
        except Exception as e:
            print(f"Error fetching zones page {page}: {e}")
            break
    return zones

async def fetch_records(client: httpx.AsyncClient, zone_id: str):
    records = []
    page = 1
    while True:
        try:
            response = await client.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?page={page}&per_page=100")
            response.raise_for_status()
            data = response.json()
            if not data['success']:
                break
            records.extend(data['result'])
            info = data.get('result_info', {})
            if page >= info.get('total_pages', 1):
                break
            page += 1
        except Exception as e:
            print(f"Error fetching records for zone {zone_id} page {page}: {e}")
            break
    return records

class SyncState:
    def __init__(self):
        self.in_progress = False
        self.last_sync_at: Optional[datetime] = None
        self.last_error: Optional[str] = None

sync_state = SyncState()
sync_lock = asyncio.Lock()

async def sync_cloudflare_task(api_token: str):
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # Fetch Zones
        zones_data = await fetch_zones(client)
        
        async with AsyncSessionLocal() as session:
            # Snapshot sync: clear and re-insert to ensure deletions are reflected
            await session.execute(delete(Record))
            await session.execute(delete(Zone))
            await session.commit()

            for z_data in zones_data:
                zone = Zone(id=z_data['id'], name=z_data['name'], status=z_data['status'])
                session.add(zone)

            for z_data in zones_data:
                records_data = await fetch_records(client, z_data['id'])
                for r_data in records_data:
                    record = Record(
                        id=r_data['id'],
                        zone_id=z_data['id'],
                        type=r_data['type'],
                        name=r_data['name'],
                        content=r_data['content'],
                        proxied=r_data.get('proxied', False),
                        ttl=r_data['ttl']
                    )
                    session.add(record)

            await session.commit()
    print("Sync complete")

async def run_sync(api_token: str):
    async with sync_lock:
        if sync_state.in_progress:
            return
        sync_state.in_progress = True
        sync_state.last_error = None

    try:
        await sync_cloudflare_task(api_token)
        sync_state.last_sync_at = datetime.now(timezone.utc)
    except Exception as exc:
        sync_state.last_error = str(exc)
    finally:
        sync_state.in_progress = False

# --- Endpoints ---

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

class SyncRequest(BaseModel):
    api_token: str

@app.post("/api/sync")
async def sync_data(request: SyncRequest, background_tasks: BackgroundTasks):
    """Trigger a synchronization of Cloudflare data."""
    if sync_state.in_progress:
        return {"status": "in_progress", "message": "Synchronization already running."}
    background_tasks.add_task(run_sync, request.api_token)
    return {"status": "started", "message": "Synchronization started in background."}

@app.get("/api/sync/status")
async def sync_status():
    return {
        "in_progress": sync_state.in_progress,
        "last_sync_at": sync_state.last_sync_at.isoformat() if sync_state.last_sync_at else None,
        "last_error": sync_state.last_error,
    }

class RecordOut(BaseModel):
    id: str
    zone_id: str
    type: str
    name: str
    content: str
    proxied: bool
    ttl: int
    zone_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class UpdateRecordRequest(BaseModel):
    api_token: str
    name: str
    content: str
    ttl: int
    proxied: bool

@app.put("/api/records/{record_id}")
async def update_record(record_id: str, request: UpdateRecordRequest, db: AsyncSession = Depends(get_db)):
    """Update a DNS record directly in Cloudflare via the API."""
    result = await db.execute(select(Record).where(Record.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found in local database.")

    headers = {"Authorization": f"Bearer {request.api_token}", "Content-Type": "application/json"}
    payload = {
        "type": record.type,
        "name": request.name,
        "content": request.content,
        "ttl": request.ttl,
        "proxied": request.proxied,
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        response = await client.put(
            f"https://api.cloudflare.com/client/v4/zones/{record.zone_id}/dns_records/{record_id}",
            json=payload
        )
        data = response.json()
        if not data.get("success"):
            errors = data.get("errors", [])
            detail = "; ".join(e.get("message", str(e)) for e in errors) if errors else "Unknown Cloudflare error"
            raise HTTPException(status_code=400, detail=detail)

    return {"status": "success", "message": "Record updated successfully."}

@app.get("/api/records", response_model=List[RecordOut])
async def get_records(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Record).options(selectinload(Record.zone)))
    records = result.scalars().all()
    # Populate zone_name manually or via relationship serialization if Config allows?
    # Pydantic ORM mode usually handles relationships if names match, but here we want 'zone_name' from 'zone.name'.
    # Easiest is to just construct the response or use a property.
    # Let's just return a list of dicts or modify objects.
    out = []
    for r in records:
        r_out = RecordOut.model_validate(r)
        if r.zone:
            r_out.zone_name = r.zone.name
        out.append(r_out)
    return out

@app.get("/api/chains")
async def get_chains(db: AsyncSession = Depends(get_db)):
    """
    Map linked records together to help identify chains.
    Logic: Find CNAMEs that point to other records in our DB.
    """
    result = await db.execute(select(Record))
    all_records = result.scalars().all()
    
    # helper map: name -> list of records
    name_map = {}
    for r in all_records:
        if r.name not in name_map:
            name_map[r.name] = []
        name_map[r.name].append(r)
    
    chains = []
    
    # Pre-fetch zones to map ID to Name
    z_result = await db.execute(select(Zone))
    zones = {z.id: z.name for z in z_result.scalars().all()}

    chains_by_zone = {}

    # Check every CNAME
    for r in all_records:
        if r.type == "CNAME":
            chain = []
            current = r
            chain.append({
                "id": current.id,
                "name": current.name,
                "type": current.type,
                "content": current.content
            })
            
            # Follow the chain
            # Caution: prevent infinite loops
            visited = {current.id}
            
            next_name = current.content
            # Cloudflare CNAME content often ends with no dot, or dot. 
            # We need to match loosely or strictly? Usually strictly but handle trailing dot.
            
            while next_name:
                # Find record with this name
                # We might have multiple records for a name (e.g. round robin A records), 
                # but usually CNAME points to one canonical name effectively.
                
                # Check if next_name exists in our map
                targets = name_map.get(next_name)
                if not targets:
                    # Maybe try adding/removing trailing dot
                    if next_name.endswith('.'):
                        targets = name_map.get(next_name[:-1])
                    else:
                        targets = name_map.get(next_name + '.')
                
                if targets:
                    found_next = False
                    for t in targets:
                        if t.id in visited:
                            continue # Cycle detected
                        
                        visited.add(t.id)
                        chain.append({
                            "id": t.id,
                            "name": t.name,
                            "type": t.type,
                            "content": t.content
                        })
                        
                        if t.type == "CNAME":
                            next_name = t.content
                            if next_name == '@':
                                # Resolve to current zone name? 
                                # Using the zone relationship would be better but expensive here.
                                # For now, let's just mark as @ (Self)
                                next_name = None 
                            found_next = True
                            break # Follow the first CNAME found
                        else:
                            # End of chain (A, AAAA, etc)
                            next_name = None 
                            found_next = True
                            break
                    
                    if not found_next:
                         next_name = None
                else:
                    # Target not in our account/DB
                    chain.append({
                        "id": "EXTERNAL",
                        "name": next_name,
                        "type": "EXTERNAL",
                        "content": "External Resource"
                    })
                    next_name = None

            z_name = zones.get(r.zone_id, "Unknown Zone")
            if z_name not in chains_by_zone:
                chains_by_zone[z_name] = []
            chains_by_zone[z_name].append(chain)
            
    return chains_by_zone

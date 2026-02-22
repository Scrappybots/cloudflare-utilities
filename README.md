# Cloudflare DNS Utilities

A web-based utility to visualize, map, analyze, and edit your Cloudflare DNS records across all your zones. Identify CNAME chains, update records with a guided confirmation flow, export to CSV, and get a complete overview of your DNS configuration.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green.svg)
![Docker](https://img.shields.io/badge/Docker%20%2F%20Podman-ready-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- 🔄 **Sync DNS Records** - Pull all DNS records from all your Cloudflare zones
- ✏️ **Edit DNS Records** - Update any record directly from the dashboard with a 3-step preview → confirm flow
- 🗺️ **CNAME Chain Mapping** - Visualize CNAME chains and identify complex DNS configurations
- 📊 **Dashboard View** - Browse and search all your DNS records in one place
- 📥 **CSV Export** - Export your DNS records for backup or analysis
- 🔒 **Secure** - API token is stored only in your browser's local storage and never sent to a server database
- 🐳 **Docker / Podman Ready** - Easy deployment with pre-built containers

## Quick Start with Docker / Podman

### Using Pre-built Container (Recommended)

Pull and run the latest image from GitHub Container Registry:

```bash
# Pull the latest image
docker pull ghcr.io/scrappybots/cloudflare-utilities:latest

# Run (localhost only - recommended for local use)
docker run -d \
  --name cloudflare-utilities \
  -p 127.0.0.1:8000:8000 \
  ghcr.io/scrappybots/cloudflare-utilities:latest
```

> **Podman users** — replace `docker` with `podman` in all commands. Everything works identically.

Access the application at: **http://localhost:8000**

> ⚠️ **Security note:** Binding to `-p 127.0.0.1:8000:8000` restricts access to your local machine only. Using `-p 0.0.0.0:8000:8000` (or just `-p 8000:8000`) exposes the port to your network and the internet, which will attract automated scanner traffic and unnecessary load. Only use `0.0.0.0` if you have a reverse proxy (nginx, Caddy, Cloudflare Tunnel, etc.) sitting in front.

### Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  cloudflare-utilities:
    image: ghcr.io/scrappybots/cloudflare-utilities:latest
    container_name: cloudflare-utilities
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      # Optional: Persist the SQLite database
      - ./data:/app
    restart: unless-stopped
```

Then run:

```bash
docker compose up -d
```

### Running a Specific Version

```bash
docker pull ghcr.io/scrappybots/cloudflare-utilities:v1.0.0
docker run -d -p 127.0.0.1:8000:8000 ghcr.io/scrappybots/cloudflare-utilities:v1.0.0
```

---

## Building from Source

### Prerequisites

- **Python 3.11+** and **pip**
- **Git**
- **Docker** or **Podman** (for container builds)

### Clone the Repository

```bash
git clone https://github.com/scrappybots/cloudflare-utilities.git
cd cloudflare-utilities
```

### Option 1: Run with Python (Development)

1. **Create a virtual environment** (recommended):

   ```bash
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:

   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

4. Access at: **http://localhost:8000**

### Option 2: Build Container Image Locally

```bash
# Build
docker build -t cloudflare-utilities .
# or: podman build -t cloudflare-utilities .

# Run (localhost only)
docker run -d \
  --name cloudflare-utilities \
  -p 127.0.0.1:8000:8000 \
  cloudflare-utilities
```

Access at: **http://localhost:8000**

---

## Usage

### Step 1: Create a Cloudflare API Token

1. Log in to your [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Go to **My Profile** → **API Tokens**
3. Click **Create Token**
4. Use the **Custom token** template with the following permissions:

   | Resource | Permission | Required for |
   |----------|------------|--------------|
   | Zone → Zone | Read | Listing zones |
   | Zone → DNS | Read | Fetching records |
   | Zone → DNS | Edit | Updating records |

5. Set **Zone Resources** to all zones (or specific zones)
6. Click **Continue to summary** → **Create Token**
7. Copy your token — you won't see it again

> If you only need read-only access (no record editing), you can omit the `DNS:Edit` permission.

### Step 2: Sync Your DNS Records

1. Open the application at **http://localhost:8000**
2. Paste your Cloudflare API Token in the input field
3. Click **Start Sync**
4. Wait for the sync to complete (time depends on your zone count)

### Step 3: Explore and Manage Your Data

- **All Records** — Browse and search all DNS records across all zones
- **Chains Map** — Visualize CNAME chains and DNS relationships
- **Export CSV** — Download all visible records for external analysis
- **Refresh** — Re-sync all records from Cloudflare at any time

### Editing a DNS Record

1. On the **All Records** dashboard, click **Edit** on any record row
2. **Form** — Modify the Name, Content, TTL, and/or Proxied fields, then click **Preview Changes**
3. **Preview** — Review a diff of exactly what will change (old value struck through in red, new value in green). Click **Accept** to proceed
4. **Confirm** — Type `Yes` in the confirmation box and click **Confirm Update**
5. The record is updated live in Cloudflare and all DNS records automatically re-sync

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database path | `sqlite+aiosqlite:///./dns_manager.db` |

### Persisting Data

To retain the SQLite database between container restarts, mount the app directory:

```bash
docker run -d \
  --name cloudflare-utilities \
  -p 127.0.0.1:8000:8000 \
  -v $(pwd)/data:/app \
  ghcr.io/scrappybots/cloudflare-utilities:latest
```

---

## API Endpoints

The application exposes the following REST API endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web UI |
| `POST` | `/api/sync` | Trigger a full DNS sync (body: `{"api_token": "..."}`) |
| `GET` | `/api/sync/status` | Poll sync progress and last error |
| `GET` | `/api/records` | Get all synced DNS records |
| `GET` | `/api/chains` | Get CNAME chain analysis |
| `PUT` | `/api/records/{id}` | Update a DNS record in Cloudflare (body: `api_token`, `name`, `content`, `ttl`, `proxied`) |

### Example API Usage

```bash
# Trigger a sync
curl -X POST http://localhost:8000/api/sync \
  -H "Content-Type: application/json" \
  -d '{"api_token": "your_cloudflare_api_token"}'

# Get all records
curl http://localhost:8000/api/records

# Update a record
curl -X PUT http://localhost:8000/api/records/RECORD_ID \
  -H "Content-Type: application/json" \
  -d '{
    "api_token": "your_cloudflare_api_token",
    "name": "example.com",
    "content": "1.2.3.4",
    "ttl": 1,
    "proxied": true
  }'
```

---

## Project Structure

```
cloudflare-utilities/
├── app/
│   ├── main.py             # FastAPI application & API endpoints
│   ├── static/             # Static assets
│   │   ├── js/
│   │   └── style/
│   └── templates/
│       └── index.html      # Vue.js frontend (single-page app)
├── .github/
│   └── workflows/
│       └── docker-release.yml  # CI/CD pipeline
├── Dockerfile
├── requirements.txt
└── README.md
```

## Development

### Running with Hot Reload

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## Troubleshooting

**Port already in use:**
```bash
# Windows
netstat -ano | findstr :8000

# Linux/macOS
lsof -i :8000

# Use a different port
docker run -d -p 127.0.0.1:8080:8000 ghcr.io/scrappybots/cloudflare-utilities:latest
```

**Seeing lots of scanner traffic / high CPU in logs:**
Bind to `127.0.0.1` instead of `0.0.0.0`. See the security note in the Quick Start section above.

**API Token not working:**
- Ensure the token has `Zone:Zone:Read` and `Zone:DNS:Read` permissions
- For editing records, also add `Zone:DNS:Edit`
- Check the token hasn't expired and zone resources are set correctly

**Edit fails with a Cloudflare error:**
- Your token was likely created without `Zone:DNS:Edit` — create a new token with that permission added

**Permission denied for Docker (Linux):**
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Cloudflare API](https://api.cloudflare.com/) - DNS management API
- [Vue.js](https://vuejs.org/) - Frontend framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework

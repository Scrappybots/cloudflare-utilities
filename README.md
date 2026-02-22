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

## Quick Start with Docker

### Using Pre-built Container (Recommended)

Pull and run the latest image from GitHub Container Registry:

```bash
# Pull the latest image
docker pull ghcr.io/scrappybots/cloudflare-utilities:latest

# Run the container
docker run -d \
  --name cloudflare-utilities \
  -p 8000:8000 \
  ghcr.io/scrappybots/cloudflare-utilities:latest
```

Access the application at: **http://localhost:8000**

### Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  cloudflare-utilities:
    image: ghcr.io/scrappybots/cloudflare-utilities:latest
    container_name: cloudflare-utilities
    ports:
      - "8000:8000"
    volumes:
      # Optional: Persist the SQLite database
      - ./data:/app/data
    restart: unless-stopped
```

Then run:

```bash
docker compose up -d
```

### Running a Specific Version

```bash
# Pull a specific version
docker pull ghcr.io/scrappybots/cloudflare-utilities:v1.0.0

# Run with version tag
docker run -d -p 8000:8000 ghcr.io/scrappybots/cloudflare-utilities:v1.0.0
```

---

## Building from Source

### Prerequisites

- **Python 3.11+**
- **pip** (Python package manager)
- **Git**

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
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. **Access the application** at: **http://localhost:8000**

### Option 2: Build Docker Image Locally

1. **Build the image**:

   ```bash
   docker build -t cloudflare-utilities .
   ```

2. **Run the container**:

   ```bash
   docker run -d \
     --name cloudflare-utilities \
     -p 8000:8000 \
     cloudflare-utilities
   ```

3. **Access the application** at: **http://localhost:8000**

---

## Usage

### Step 1: Create a Cloudflare API Token

1. Log in to your [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Go to **My Profile** → **API Tokens**
3. Click **Create Token**
4. Use the **Custom token** template with the following permissions:
   - **Zone** → **Zone** → **Read**
   - **Zone** → **DNS** → **Read**
5. Set **Zone Resources** to include all zones (or specific zones)
6. Click **Continue to summary** → **Create Token**
7. Copy your token (you won't see it again!)

### Step 2: Sync Your DNS Records

1. Open the application at **http://localhost:8000**
2. Paste your Cloudflare API Token in the input field
3. Click **Start Sync**
4. Wait for the sync to complete (time depends on your zone count)

### Step 3: Explore Your Data

- **All Records** - View and search all DNS records across zones
- **Chains Map** - Visualize CNAME chains and DNS relationships
- **Export CSV** - Download all records for external analysis

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database path | `sqlite+aiosqlite:///./dns_manager.db` |

### Persisting Data with Docker

To persist the SQLite database between container restarts:

```bash
docker run -d \
  --name cloudflare-utilities \
  -p 8000:8000 \
  -v $(pwd)/data:/app \
  ghcr.io/scrappybots/cloudflare-utilities:latest
```

---

## API Endpoints

The application exposes the following REST API endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web UI |
| `POST` | `/api/sync` | Trigger DNS sync (requires `api_token` in body) |
| `GET` | `/api/records` | Get all synced DNS records |
| `GET` | `/api/zones` | Get all synced zones |
| `GET` | `/api/chains` | Get CNAME chain analysis |

### Example API Usage

```bash
# Trigger a sync
curl -X POST http://localhost:8000/api/sync \
  -H "Content-Type: application/json" \
  -d '{"api_token": "your_cloudflare_api_token"}'

# Get all records
curl http://localhost:8000/api/records
```

---

## Development

### Project Structure

```
cloudflare-utilities/
├── app/
│   ├── main.py           # FastAPI application
│   ├── static/           # CSS and JavaScript files
│   │   ├── js/
│   │   └── style/
│   └── templates/
│       └── index.html    # Vue.js frontend
├── .github/
│   └── workflows/
│       └── docker-release.yml  # CI/CD pipeline
├── Dockerfile
├── requirements.txt
└── README.md
```

### Running in Development Mode

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag enables hot reloading for development.

---

## Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Find process using port 8000
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# Use a different port
docker run -d -p 8080:8000 ghcr.io/scrappybots/cloudflare-utilities:latest
```

**Permission denied for Docker:**
```bash
# Add your user to the docker group (Linux)
sudo usermod -aG docker $USER
# Then log out and back in
```

**API Token not working:**
- Ensure your token has `Zone:Zone:Read` and `Zone:DNS:Read` permissions
- Check that the token hasn't expired
- Verify zone resources are set correctly

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

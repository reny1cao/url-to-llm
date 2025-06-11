# URL-to-LLM Quick Start Guide

## 🚀 Getting Started

Everything is managed through a single script: `url-to-llm.sh`

### First Time Setup
```bash
./url-to-llm.sh start
```

### Daily Commands

**Start the project:**
```bash
./url-to-llm.sh start
```

**Stop everything:**
```bash
./url-to-llm.sh stop
```

**Check status:**
```bash
./url-to-llm.sh status
```

**View logs:**
```bash
./url-to-llm.sh logs          # All logs
./url-to-llm.sh logs backend   # Backend only
./url-to-llm.sh logs frontend  # Frontend only
```

**Test system health:**
```bash
./url-to-llm.sh test
```

### Troubleshooting

**If something goes wrong:**
```bash
./url-to-llm.sh fix
```

**Restart everything:**
```bash
./url-to-llm.sh restart
```

**Scale workers:**
```bash
./url-to-llm.sh scale 4   # Scale to 4 workers
```

**Complete cleanup (removes all data):**
```bash
./url-to-llm.sh clean
```

### Access URLs

Once running, access the services at:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Test Crawler**: http://localhost:3000/test-crawler
- **MinIO Console**: http://localhost:9001 (user: minioadmin, pass: minioadmin)

### Help

For all available commands:
```bash
./url-to-llm.sh help
```
# AI Traffic Intelligence System - Copilot Instructions

## Architecture Overview
This is a multi-modal AI system for traffic light optimization using computer vision and reinforcement learning. The architecture follows an event-driven pattern with MQTT as the message backbone connecting specialized microservices:

- **MQTT Broker (Mosquitto)**: Central message hub for all inter-service communication
- **YOLO Detector**: Real-time vehicle detection from uploaded camera images 
- **Upload Server**: Flask endpoint receiving images from external cameras/Arduino
- **RL Agent**: Multi-armed bandit algorithm for traffic light control decisions
- **Telegraf**: Message transformation and InfluxDB ingestion pipeline
- **InfluxDB 3**: Time-series storage for metrics and model training data
- **Grafana**: Real-time dashboards for monitoring traffic patterns

## Key Data Flows

### Image Processing Pipeline
```
Camera/Arduino → Upload Server (/upload) → Shared Volume → YOLO Detector → MQTT (traffic/cars)
```

### RL Decision Loop
```
Traffic Data → MQTT (traffic/data) → RL Agent → MQTT (traffic/control) → External Systems
Feedback → MQTT (traffic/feedback) → RL Agent (model updates)
```

### Metrics Collection
```
MQTT Messages → Telegraf → Starlark Processor → InfluxDB 3 → Grafana Dashboards
```

## Critical Development Patterns

### MQTT Topic Conventions
- Input topics: `cam/new_image`, `traffic/data`, `traffic/feedback`
- Output topics: `traffic/cars`, `traffic/control`, `system/time/unix`
- Always use JSON payloads with timestamp fields (`Ta`, `Tstart`, `timestamp`)

### Docker Volume Sharing
- `C:/upload:/app/uploads` - Shared between upload-server and yolo-detector
- Config persistence: `./<service>/config:/app/.ultralytics` for YOLO settings
- InfluxDB and Grafana use named volumes for data persistence

### Environment Configuration
- Main config in `.env` (InfluxDB tokens, Grafana credentials, service ports)
- Service-specific config in `./rl-agent/config.env` 
- **Critical**: Update `INFLUXDB_TOKEN` after running token generation command
- Use container names for inter-service networking (e.g., `mosquitto:1883`)

## Essential Workflows

### Initial Setup
```bash
docker-compose up -d influxdb3-core
docker-compose exec influxdb3-core influxdb3 create token --admin
# Update .env with new token
docker-compose up -d
```

### Development Iteration
```bash
docker-compose logs <service>          # Debug individual services
docker-compose restart <service>       # Apply config changes
docker-compose down -v                 # Reset all data (destructive)
```

### GPU/CUDA Support
YOLO service requires NVIDIA runtime. Key config in `docker-compose.yml`:
```yaml
runtime: nvidia
environment:
  - NVIDIA_VISIBLE_DEVICES=all
```

## Service-Specific Notes

### Telegraf Processing
Uses Starlark scripting for complex JSON transformations. The processor converts raw MQTT traffic data into structured InfluxDB metrics with proper tagging (`id`, `name`) and timing fields (`recorded_at_ms`).

### RL Agent Implementation
Thompson Sampling multi-armed bandit in `bandit.py`. Context vector includes traffic queue differences, peak indicators. Model state persists in memory only - no checkpointing implemented.

### YOLO Integration
Pre-trained YOLOv8n model with CUDA acceleration. Vehicle detection focuses on specific classes: `{"car", "truck", "bus", "motorbike"}`. Image processing uses zone-based counting with configurable areas.

### Grafana Connection
Use SQL query language with InfluxDB 3 datasource. Example traffic query:
```sql
SELECT "cars", "state", "time" FROM "traffic_light" 
WHERE "time" >= $__timeFrom AND "id" = '0'
```

## Common Debugging Points

- MQTT connectivity issues: Check `mosquitto` container status first
- YOLO GPU errors: Verify NVIDIA Docker runtime installation  
- InfluxDB connection failures: Ensure token is properly escaped in environment files
- Missing image files: Verify volume mount paths match between services
- Telegraf parsing errors: Validate JSON structure matches Starlark processor expectations
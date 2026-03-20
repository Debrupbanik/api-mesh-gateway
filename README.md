# API Mesh Gateway

**AI-Powered API Gateway with intelligent routing, caching, and circuit breaking.**

A production-ready API gateway that uses AI to intelligently route requests, predict optimal cache TTL, balance load across services, and prevent cascading failures.

## Features

- **Intelligent Routing** - Route requests to multiple backend services based on path patterns
- **AI-Powered Load Balancing** - Predict traffic patterns and route to healthiest instances
- **Circuit Breaker** - Prevent cascading failures with automatic failover
- **Smart Caching** - Redis-backed caching with AI-predicted optimal TTL
- **Rate Limiting** - Sliding window rate limiting per client/route
- **Request Transformation** - Transform requests/responses on the fly
- **Prometheus Metrics** - Built-in metrics for monitoring
- **Docker Support** - Ready for containerized deployment

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Client    │────▶│  API Mesh    │────▶│  Backend        │
│             │◀────│  Gateway     │◀────│  Services       │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌───────────┐  ┌─────────────┐
    │  Circuit   │  │   Redis   │  │    AI      │
    │  Breaker   │  │   Cache   │  │  Predictor  │
    └────────────┘  └───────────┘  └─────────────┘
```

## Installation

```bash
# Clone the repository
git clone https://github.com/Debrupbanik/api-mesh-gateway.git
cd api-mesh-gateway

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

## Quick Start

```bash
# Start with Docker Compose (includes Redis)
docker compose up

# Or run directly
uvicorn apimesh.main:gateway_app --reload
```

## Configuration

Set environment variables or create a `.env` file:

```env
APIMESH_HOST=0.0.0.0
APIMESH_PORT=8000
APIMESH_REDIS_URL=redis://localhost:6379/0
APIMESH_DEBUG=false
APIMESH_RATE_LIMIT_REQUESTS=100
APIMESH_RATE_LIMIT_WINDOW=60
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Gateway status |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/api/{path}` | * | Proxied requests to backend |

## Development

```bash
# Run tests
pytest tests/ -v

# Format code
black apimesh tests

# Lint code
ruff check apimesh tests

# Type check
mypy apimesh
```

## Project Structure

```
apimesh/
├── __init__.py          # Package init
├── config.py            # Configuration
├── main.py              # FastAPI application
├── cli.py               # CLI entry point
├── circuit/             # Circuit breaker
├── cache/               # Redis caching
├── limiter/             # Rate limiting
├── ai/                  # Traffic prediction
├── routing/             # Request routing
└── core/                # Core types
```

## License

MIT License - See [LICENSE](LICENSE) for details.

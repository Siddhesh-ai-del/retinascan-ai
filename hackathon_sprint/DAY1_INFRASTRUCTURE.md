# Day 1: Infrastructure & CI/CD

## Completed
- [x] Set up GitHub Actions CI pipeline
- [x] Docker Compose for local development
- [x] Pre-commit hooks (black, ruff, mypy)
- [x] Project structure finalization

## Key Decisions
- FastAPI backend (async, auto-docs)
- React 19 frontend (modern hooks)
- ONNX Runtime for inference (CPU/GPU flexibility)
- SQLite for visit history (lightweight, portable)

## Files Created
- `.github/workflows/ci.yml` - CI pipeline
- `docker-compose.yml` - Local dev environment
- `.pre-commit-config.yaml` - Code quality hooks

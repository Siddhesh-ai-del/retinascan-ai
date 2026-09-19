# Day 8: API & Backend Polish

## Completed
- [x] FastAPI endpoints with auto-docs
- [x] Batch prediction endpoint
- [x] Visit history with SQLite
- [x] Error handling & validation
- [x] Rate limiting & CORS

## API Endpoints

### Core
- `POST /api/predict` - Single image analysis
- `POST /api/batch-predict` - Batch analysis (up to 20)
- `GET /api/visit-history` - Patient visit history
- `GET /api/visit/{id}` - Single visit details

### FHIR
- `GET /fhir/Report/{id}` - FHIR R4 diagnostic report

### Admin
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## Request/Response Format

### Single Prediction
```json
// Request
POST /api/predict
Content-Type: multipart/form-data
Body: file=<image>

// Response
{
  "status": "ok",
  "classification": {
    "stage": 2,
    "stage_name": "Moderate NPDR",
    "confidence": 0.87,
    "probabilities": [0.02, 0.05, 0.87, 0.04, 0.02]
  },
  "segmentation": {
    "lesions": ["microaneurysm", "hemorrhage"],
    "area_percent": 2.3
  },
  "referral": {
    "urgency": "urgent",
    "action": "Refer within 1 month"
  }
}
```

### Batch Prediction
```json
// Request
POST /api/batch-predict
Content-Type: multipart/form-data
Body: files=<image1>,<image2>,...

// Response
{
  "batch_id": "batch_abc123",
  "results": [...],  // Sorted by severity
  "summary": {
    "total": 10,
    "urgent": 2,
    "routine": 8
  }
}
```

## Error Handling
- 400: Invalid image format
- 413: Image too large (max 10MB)
- 422: Unprocessable image (IQA rejection)
- 500: Internal server error

## Performance
- Async processing with FastAPI
- Background tasks for batch processing
- Connection pooling for SQLite
- CORS configured for frontend

## Files Modified
- `src/api/server.py` - All endpoints
- `src/api/models.py` - Pydantic schemas
- `src/db/visit_history.py` - SQLite operations

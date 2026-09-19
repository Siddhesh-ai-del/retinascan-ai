# Day 5: Batch Triage Mode

## Completed
- [x] `/api/batch-predict` endpoint (up to 20 images)
- [x] Severity-sorted results (highest urgency first)
- [x] Frontend batch upload UI
- [x] Batch results table with sorting

## API Design
```python
@app.post("/api/batch-predict")
async def batch_predict(files: List[UploadFile]):
    # Process up to 20 images
    # Return severity-sorted results
    # Include per-image metrics
```

## Batch Processing Flow
1. Upload multiple images (max 20)
2. Process each image through pipeline
3. Sort results by severity (Stage 4 → Stage 0)
4. Return batch ID + individual results
5. Frontend displays sortable table

## Clinical Value
- **Triage**: Most urgent cases first
- **Efficiency**: Process clinic batch in one go
- **Prioritization**: Focus on severe cases

## Files Modified
- `src/api/server.py` - Batch endpoint
- `frontend/src/components/BatchUpload.jsx` - Batch UI
- `frontend/src/components/BatchResults.jsx` - Results table

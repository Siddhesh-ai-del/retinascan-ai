# Day 6: Safety & Clinical Integration

## Completed
- [x] Image Quality Gate (IQA) - rejects ungradable images
- [x] Abstention Logic - flags uncertain cases for human review
- [x] Referral Urgency mapping (ICDR stage → clinical action)
- [x] FHIR R4 diagnostic report generation
- [x] SNOMED CT coded findings

## Safety Features

### 1. Image Quality Gate
- **Purpose**: Reject images too poor for reliable analysis
- **Criteria**: Blur, brightness, contrast, field quality
- **Action**: Returns "ungradable" status, recommends retake

### 2. Abstention Logic
- **Purpose**: Flag uncertain predictions for human review
- **Threshold**: Confidence < 70% triggers "uncertain" flag
- **Action**: Marks case for ophthalmologist review

### 3. Referral Urgency
| ICDR Stage | Urgency | Action |
|------------|---------|--------|
| 0 - No DR | Routine | Annual screening |
| 1 - Mild NPDR | Routine | Annual screening |
| 2 - Moderate NPDR | Urgent | Refer within 1 month |
| 3 - Severe NPDR | Urgent | Refer within 1 week |
| 4 - Proliferative DR | Emergency | Refer immediately |

### 4. FHIR R4 Integration
```json
{
  "resourceType": "DiagnosticReport",
  "status": "final",
  "code": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "77477-2",
      "display": "Diabetic retinopathy screening"
    }]
  },
  "conclusion": "Moderate Nonproliferative Diabetic Retinopathy"
}
```

## Clinical Value
- **Safety**: Multiple safeguards against misdiagnosis
- **Interoperability**: FHIR R4 works with any EHR
- **Standards**: SNOMED CT coded for billing/analytics
- **Transparency**: Confidence scores for all predictions

## Files Modified
- `src/inference/predictor.py` - IQA, abstention, urgency
- `src/api/server.py` - FHIR R4 endpoint
- `src/fhir/diagnostic_report.py` - Report generation

from datetime import datetime, timezone

SNOMED_CODES = {
    0: ("714811003", "No diabetic retinopathy"),
    1: ("714812005", "Mild nonproliferative diabetic retinopathy"),
    2: ("714813000", "Moderate nonproliferative diabetic retinopathy"),
    3: ("714814006", "Severe nonproliferative diabetic retinopathy"),
    4: ("55235003", "Proliferative diabetic retinopathy"),
}


def generate_fhir_report(patient_id, classification_result, lesion_summary):
    stage = classification_result["stage"]
    label = classification_result["label"]
    snomed_code, snomed_display = SNOMED_CODES.get(stage, ("00000000", "Unspecified"))

    def lesion_ext(key, url):
        info = lesion_summary.get(key)
        return {"url": url, "valueBoolean": bool(info and info["detected"])}

    report = {
        "resourceType": "DiagnosticReport",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "18748-4",
                        "display": "Ophthalmology studies",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "408151003",
                    "display": "Diabetic retinopathy screening",
                }
            ]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
        "issued": datetime.now(timezone.utc).isoformat(),
        "conclusion": f"ICDR Stage {stage}: {label} (confidence {classification_result['confidence']:.0%})",
        "conclusionCode": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": snomed_code,
                    "display": snomed_display,
                }
            ]
        },
        "result": [
            {
                "resourceType": "Observation",
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "imaging",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": snomed_code,
                            "display": snomed_display,
                        }
                    ]
                },
                "subject": {"reference": f"Patient/{patient_id}"},
                "valueInteger": stage,
                "component": [
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": "82810-3",
                                    "display": "Confidence level",
                                }
                            ]
                        },
                        "valueQuantity": {
                            "value": round(classification_result["confidence"] * 100, 1),
                            "unit": "%",
                        },
                    }
                ],
            }
        ],
        "extension": [
            {
                "url": "http://example.org/fhir/lesion-findings",
                "extension": [
                    lesion_ext("microaneurysms", "microaneurysms"),
                    lesion_ext("hemorrhages", "hemorrhages"),
                    lesion_ext("hard_exudates", "hard_exudates"),
                    lesion_ext("cotton_wool_spots", "cotton_wool_spots"),
                ],
            }
        ],
    }
    return report


if __name__ == "__main__":
    demo_cls = {"stage": 2, "label": "Moderate NPDR", "confidence": 0.87}
    demo_lesions = {
        "microaneurysms": {"detected": True},
        "hemorrhages": {"detected": True},
        "hard_exudates": {"detected": True},
        "cotton_wool_spots": {"detected": False},
    }
    import json

    print(json.dumps(generate_fhir_report("demo-patient-001", demo_cls, demo_lesions), indent=2))

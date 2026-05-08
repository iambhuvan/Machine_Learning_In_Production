# Explanations Report

This document describes the global and local explanations, how they meet stakeholder needs, and how to reproduce them.

---

## Global Explanations (`explanation_global.md`)

### Target Stakeholder
Procurement officers at non-profit organizations deciding whether to purchase the screening product.

### Techniques Used

| Technique | Code Reference | Purpose |
|-----------|----------------|---------|
| Confusion Matrix | Cell 8 | Per-class accuracy and misclassification patterns |
| Classification Report + Kappa | Cell 9 | Precision, recall, F1, agreement with experts (0.913) |
| Class Distribution | Cell 10 | Training data balance and potential bias |
| Aggregate Grad-CAM | Cells 12-13 | What the model focuses on per severity level |
| Fairness Analysis | Cell 14 | Performance by gender and age group |

### How These Meet Identified Needs

Procurement officers must justify purchases with evidence, assess risks for their populations, and meet ethical standards. The global explanations target these buying-decision concerns:

1. **Accuracy evidence** → Section 3 provides confusion matrix (88.5% accuracy, Kappa 0.913) with honest interpretation of weaknesses (lower recall for severe cases), helping officers weigh deployment risks.
2. **High-level model description** → Section 2 explains the AI as "pattern recognition from expert-labeled examples" — enough for board presentations without ML jargon.
3. **Training data and biases** → Section 5 provides dataset source, size, class distribution, and demographic context so officers can assess representativeness for their population.
4. **Fairness** → Section 6 provides per-gender and per-age-group accuracy breakdowns with honest limitations — concrete data for procurement justification documents.
5. **Limitations** → Section 7 lists 7 specific limitations, helping officers plan for mitigation (referral pathways, operator training).
6. **Data privacy** → Section 8 lists what data is and is not collected for local regulation compliance assessment.
7. **Issue reporting** → Section 9 describes proposed reporting mechanisms for field team support.

---

## Local Explanations (`explanation_local.md`)

### Target Stakeholder
Nurses/volunteers who perform screenings with patients. Text uses plain-language strategies for approximately an 8th grade reading level.

### Techniques Used

| Technique | Code Reference | Purpose |
|-----------|----------------|---------|
| Grad-CAM Heatmap | Cell 12 | Visual overlay showing where the model focused |
| Confidence Bar Chart | Cell 16 | Model confidence across all severity levels |
| Plain-Language Text | Cell 17 | Screening result explanation for patients |
| HTML Report Generation | Cell 18 | Printable patient handout |

### How These Meet Identified Needs

Nurses work in time-constrained screening encounters, explaining results to anxious patients with limited health literacy — without medical imaging expertise. Each element addresses a specific interaction need:

1. **Automation disclosure** → "This screening was performed by a computer program (AI), not a doctor. Please communicate this to the patient and emphasize that a doctor should confirm the result." Prominent and scripted so nurses can communicate it consistently.
2. **Plain-language result** → Severity-specific descriptions in everyday language (e.g., "some blood vessels in your eye may be affected") that nurses can read directly to patients.
3. **Visual explanation** → Grad-CAM overlay gives nurses something concrete to point to when patients ask "what did the computer find?" — making AI reasoning visible without technical knowledge.
4. **Confidence level** → Plain-language text communicates certainty ("The computer was not very certain") without softmax terminology, signaling when extra follow-up is needed.
5. **Who is involved** → Explicitly names the three actors (health worker, computer, doctor) to set care pathway expectations.
6. **What data was used** → Reassures patients: "Only the photo of your eye was used."
7. **Next steps** → Severity-specific guidance from "regular checkups" to "see a doctor right away — this is urgent." The most operationally critical element.
8. **Disclaimer** → "This is a screening tool only."

### Patient Examples
- **Patient 1 (dd90c321d7bc):** No DR, high confidence — clear negative result.
- **Patient 2 (75a4343b12f9):** Mild, lower confidence — demonstrates uncertainty communication.

---

## Why Grad-CAM

We chose Grad-CAM over SHAP or LIME because: (1) it produces spatial heatmaps native to CNNs — far more intuitive for retina images than pixel-level attributions; (2) a colored overlay is immediately meaningful to non-technical users; (3) it requires no extra dependencies (implemented with `tf.GradientTape`); (4) we present it as a visual aid, not proof of correctness.

---

## How to Generate Local Explanations for Other Patients

1. Place the patient's retina image (`.png`) in `data/test_images/`.
2. Add a row to `data/test.csv` with `id_code` (filename without `.png`), `age`, `gender`, `diagnosis`. If the true diagnosis is unknown, use `0` as a placeholder — this value is only used for record-keeping and does not affect the model's prediction or the generated report. (Do not rerun the global evaluation cells after adding placeholder labels, as they would skew the accuracy metrics.)
3. In `explainability.ipynb` Cell 2, set: `PATIENT_IDS = ["new_patient_id"]`. Cell 19 will skip auto-selection when this is set.
4. Run all cells. Outputs appear in `artifacts/`: `{id}_original.png`, `{id}_gradcam.png`, `{id}_confidence.png`, `{id}_report.html`.
5. `explanation_local.md` is also regenerated.

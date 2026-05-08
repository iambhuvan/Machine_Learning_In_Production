# I4 Explainability Assignment — Detailed TODO

## Stakeholders
- **Stakeholder 1 (Global):** Procurement officers at non-profit organizations deciding whether to buy the product
- **Stakeholder 2 (Local):** Nurses/volunteers who perform the screening with patients (8th grade reading level)

## Verified Data Layout
```
data/
├── train.csv          # 2,929 rows — columns: id_code, age, gender, diagnosis
├── test.csv           # 733 rows — columns: id_code, age, gender, diagnosis
├── train_images/      # 2,926 .png files (3 invalid filenames in CSV — expected)
└── test_images/       # 731 .png files (2 invalid filenames in CSV — expected)
model.h5               # 318 MB pre-trained ResNet50 at repo root
artifacts/             # Auto-created — all generated plots, images, HTML reports
```

## Key Corrections Applied (from codex review)
- All paths use local project-relative structure (no Colab/Drive paths)
- Age and gender ARE available in CSVs (verified)
- All metrics computed fresh from our own evaluation run — never hardcoded
- "Diagnosis" wording replaced with "Screening Result" throughout
- Local reports explicitly satisfy all 5 sub-items of Policy §4
- HTML template redesigned for nurse/volunteer audience, not developers
- `artifacts/` used instead of `images/` for generated outputs

---

## Phase 0: Project Setup
- [ ] 0.1 Create `artifacts/` directory
- [ ] 0.2 Verify model loads: `tf.keras.models.load_model("model.h5")` runs without error
- [ ] 0.3 Verify test images load: pick one image from `data/test_images/`, load and preprocess to (1,320,320,3)
- [ ] 0.4 Identify last convolutional layer name in loaded model for Grad-CAM

---

## Phase 1: Explanation Needs Analysis
**Deliverable:** `explanation_needs.md` (≤1000 words)

- [ ] 1.1 Research diabetic retinopathy screening process, especially in underresourced/remote areas
- [ ] 1.2 Research what procurement officers at non-profits care about when evaluating medical AI products (accuracy, fairness, cost, data practices, regulatory compliance, vendor reliability)
- [ ] 1.3 Research what nurses/volunteers need when performing screenings (how to explain results to patients, when to refer, how to handle anxious patients, cultural sensitivity)
- [ ] 1.4 Create persona for Stakeholder 1: non-profit procurement officer
  - Background, goals, concerns, technical literacy level
- [ ] 1.5 Create persona for Stakeholder 2: community health nurse/volunteer
  - Background, goals, concerns, technical literacy level
- [ ] 1.6 Identify explanation needs for Stakeholder 1:
  - Overall model accuracy and error rates
  - How the model works at a high level (not ML jargon — "pattern recognition from examples")
  - What data was used to train it and potential biases
  - Known limitations and failure modes
  - Evidence of effectiveness / independent validation
  - Fairness across demographic groups (age/gender subgroup analysis if feasible, otherwise document as limitation)
  - Data privacy and PII handling
- [ ] 1.7 Identify explanation needs for Stakeholder 2:
  - Clear automation disclosure ("This screening was done by a computer program (AI), not a doctor")
  - Plain-language result explanation (what the severity level means)
  - Visual explanation of what the model detected (Grad-CAM heatmap overlay)
  - Confidence level communicated honestly (high/moderate/low)
  - Actionable next steps per severity level
  - What personal data was used for this specific screening
  - Who else is involved in the decision (nurse administering, doctor for follow-up)
  - When to refer patient urgently vs. routine follow-up
- [ ] 1.8 Write `explanation_needs.md` with process description, evidence/references, and needs for both stakeholders

---

## Phase 2: Code — Explainability Notebook
**Deliverable:** `explainability.ipynb`
**All paths relative to repo root. All metrics computed fresh — never hardcoded.**

### 2A: Setup & Data Loading
- [ ] 2.1 Create new notebook `explainability.ipynb`
- [ ] 2.2 Cell 1 — Imports:
  ```python
  import tensorflow as tf
  import numpy as np
  import pandas as pd
  import matplotlib.pyplot as plt
  import seaborn as sns
  import cv2
  import os
  from sklearn.metrics import confusion_matrix, classification_report, cohen_kappa_score, accuracy_score
  from tensorflow.keras.preprocessing.image import ImageDataGenerator
  from matplotlib import cm
  ```
- [ ] 2.3 Cell 2 — Constants & config:
  ```python
  HEIGHT, WIDTH, CHANNELS = 320, 320, 3
  N_CLASSES = 5
  BATCH_SIZE = 8
  DATA_DIR = "data"
  MODEL_PATH = "model.h5"
  ARTIFACTS_DIR = "artifacts"
  os.makedirs(ARTIFACTS_DIR, exist_ok=True)

  diagnosis_dict = {0: 'No DR', 1: 'Mild', 2: 'Moderate', 3: 'Severe', 4: 'Proliferative DR'}

  # Parameterized patient selection — change these to generate reports for other patients
  PATIENT_IDS = ["PATIENT_A_ID", "PATIENT_B_ID"]  # replace with actual id_codes from test.csv
  ```
- [ ] 2.4 Cell 3 — Load data:
  ```python
  train_df = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
  test_df = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))
  train_df["id_code"] = train_df["id_code"].apply(lambda x: x + ".png")
  test_df["id_code"] = test_df["id_code"].apply(lambda x: x + ".png")
  train_df["diagnosis"] = train_df["diagnosis"].astype(str)
  test_df["diagnosis"] = test_df["diagnosis"].astype(str)
  ```
- [ ] 2.5 Cell 4 — Create ImageDataGenerators (rescale only, no augmentation for evaluation):
  ```python
  test_datagen = ImageDataGenerator(rescale=1./255)
  test_generator = test_datagen.flow_from_dataframe(
      dataframe=test_df,
      directory=os.path.join(DATA_DIR, "test_images"),
      x_col="id_code", y_col="diagnosis",
      class_mode="categorical", batch_size=BATCH_SIZE,
      target_size=(HEIGHT, WIDTH), shuffle=False, seed=42)
  ```
  **Note:** `shuffle=False` is critical so predictions align with test_df rows
- [ ] 2.6 Cell 5 — Load model and identify Grad-CAM layer:
  ```python
  model = tf.keras.models.load_model(MODEL_PATH)
  # Find last conv layer programmatically
  last_conv_layer_name = None
  for layer in reversed(model.layers):
      if len(layer.output_shape) == 4:
          last_conv_layer_name = layer.name
          break
  print(f"Last conv layer for Grad-CAM: {last_conv_layer_name}")
  model.summary()
  ```

### 2B: Global Explanations Code
- [ ] 2.7 Cell 6 — Generate predictions on full test set:
  ```python
  test_generator.reset()
  y_pred_probs = model.predict(test_generator, steps=len(test_generator))
  y_pred = np.argmax(y_pred_probs, axis=1)
  y_true = test_generator.classes
  ```
- [ ] 2.8 Cell 7 — Confusion matrix:
  - Compute with `confusion_matrix(y_true, y_pred)`
  - Plot normalized heatmap with seaborn, label axes with class names
  - Save to `artifacts/global_confusion_matrix.png`
- [ ] 2.9 Cell 8 — Classification report + metrics:
  - `classification_report(y_true, y_pred, target_names=list(diagnosis_dict.values()))`
  - `cohen_kappa_score(y_true, y_pred, weights='quadratic')`
  - `accuracy_score(y_true, y_pred)`
  - Print all values and save formatted table as image to `artifacts/global_metrics.png`
- [ ] 2.10 Cell 9 — Class distribution:
  - Bar chart of training data class distribution from train_df (use original integer diagnosis)
  - Show counts + percentages, highlight class imbalance
  - Save to `artifacts/global_class_distribution.png`
- [ ] 2.11 Cell 10 — Aggregate Grad-CAM per class:
  - For each class (0-4), pick ~5-10 correctly-classified test images
  - Compute Grad-CAM for each using `compute_gradcam()` (defined in 2C)
  - Average heatmaps, overlay on a representative image per class
  - Save to `artifacts/global_gradcam_class_0.png` through `artifacts/global_gradcam_class_4.png`
- [ ] 2.12 Cell 11 — Fairness subgroup analysis (conditional):
  - If age/gender subgroups are large enough, compute per-group accuracy
  - Bar chart comparing accuracy across gender (M/F) and age bins
  - If subgroups too small or imbalanced, document as limitation
  - Save to `artifacts/global_fairness.png` (if generated)

### 2C: Local Explanations Code
- [ ] 2.13 Cell 12 — Implement `compute_gradcam(model, img_array, last_conv_layer_name, pred_index=None)`:
  - Use `tf.GradientTape`
  - Create sub-model: `tf.keras.Model(model.input, [model.get_layer(last_conv_layer_name).output, model.output])`
  - Forward pass, get gradients of target class w.r.t. conv outputs
  - Global average pool gradients, weight conv feature maps, ReLU, normalize to [0,1]
  - Return heatmap array (H, W)
- [ ] 2.14 Cell 13 — Implement `create_gradcam_overlay(img, heatmap, alpha=0.4)`:
  - Resize heatmap to image dimensions with `cv2.resize`
  - Apply jet colormap: `cm.jet(heatmap_resized)[:, :, :3]`
  - Blend: `overlay * alpha + img * (1 - alpha)`
  - Return clipped superimposed image
- [ ] 2.15 Cell 14 — Implement `create_confidence_chart(pred_probs, save_path)`:
  - Horizontal bar chart of all 5 softmax probabilities
  - Predicted class highlighted in green, others in light gray
  - X-axis 0 to 1, labeled "Confidence"
  - Class names as y-axis labels
  - Save to `save_path`
- [ ] 2.16 Cell 15 — Implement `generate_screening_text(prediction, confidence)`:
  - Returns plain-language string at **8th grade reading level**
  - Structure:
    1. **Automation disclosure:** "This screening was performed by a computer program (artificial intelligence), not a doctor."
    2. **How it works (brief):** "The computer analyzed a photo of the back of your eye to look for signs of damage from diabetes."
    3. **Who is involved:** "A trained health worker took your eye photo. The computer analyzed it. A doctor should confirm the result."
    4. **What data was used:** "Only the photo of your eye was used for this screening. Your age and gender were recorded for your medical record."
    5. **Result:** Severity label + plain-language description per class
    6. **Confidence:** "The computer is [high/moderate/low] confident in this result ([X]%)."
    7. **What the image shows:** "The colored areas on the eye picture show where the computer focused most."
    8. **Next steps:** Severity-specific actionable guidance
    9. **Disclaimer:** "This is a screening tool only. It does not replace a full eye exam by a doctor."
  - severity_descriptions dict with plain-language text for each class (0-4)
- [ ] 2.17 Cell 16 — Implement `generate_patient_report(patient_id, output_dir)`:
  - Load image from `data/test_images/{patient_id}.png`
  - Preprocess to (1, 320, 320, 3)
  - Get prediction + softmax probabilities from model
  - Compute Grad-CAM heatmap → create overlay
  - Generate confidence chart
  - Generate plain-language screening text
  - Look up age/gender from test_df
  - Load enhanced HTML template from `explanation_template.html`
  - Replace all placeholders: patient ID, age, gender, screening result, explanation text, image paths
  - Save HTML to `{output_dir}/{patient_id}_report.html`
  - Save all images to `{output_dir}/`
  - Return dict with all metadata for use in `explanation_local.md`
- [ ] 2.18 Cell 17 — Select 2 patients (parameterized via `PATIENT_IDS`):
  - Patient A: Clear case with high confidence (e.g., No DR or Proliferative DR)
  - Patient B: Moderate/uncertain case with lower confidence (e.g., Mild or Moderate)
  - Selection logic: run predictions, find patients matching criteria, set `PATIENT_IDS`
- [ ] 2.19 Cell 18 — Generate reports for both patients:
  - Call `generate_patient_report()` for each patient in `PATIENT_IDS`
  - Print summary of generated files
- [ ] 2.20 Cell 19 — Export `explanation_local.md`:
  - Programmatically combine both patient reports into one markdown file
  - Embed images using relative paths to `artifacts/`
  - Write to repo root as `explanation_local.md`

---

## Phase 3: Update HTML Template
**Deliverable:** Enhanced `explanation_template.html`
**Key change: "Diagnosis Report" → "Eye Screening Results", designed for nurse/patient audience**

- [ ] 3.1 Rename title: "Diagnosis Report" → "Eye Screening Results"
- [ ] 3.2 Add automation disclosure section at top (prominent, before any results)
- [ ] 3.3 Add patient info: ID (PXX), Age (AXX), Gender (GXX)
- [ ] 3.4 Add side-by-side images: original retina (ORIGINAL_IMG) + Grad-CAM overlay (GRADCAM_IMG)
  - Caption for overlay: "The colored areas show where the computer looked most closely"
- [ ] 3.5 Replace "Diagnosis: DXX" → "Screening Result: DXX"
- [ ] 3.6 Add confidence chart image section (CONFIDENCE_IMG)
- [ ] 3.7 Structure explanation into labeled sections:
  - "How This Screening Works" (brief)
  - "Who Is Involved in This Decision"
  - "What Data Was Used"
  - "Your Screening Result"
  - "What the Eye Picture Shows"
  - "What to Do Next"
- [ ] 3.8 Add disclaimer footer: "This is a screening tool only. It does not replace a full eye exam by a doctor."
- [ ] 3.9 Use clear, large fonts suitable for printing/display
- [ ] 3.10 Keep w3.css styling, ensure responsive layout
- [ ] 3.11 Use local w3.css reference instead of remote URL (already in repo)

---

## Phase 4: Global Explanation Document
**Deliverable:** `explanation_global.md`
**Audience: Procurement officers — semi-technical, professional tone. NOT developer documentation.**
**All metrics from our own evaluation run (artifacts/ images), never hardcoded.**

- [ ] 4.1 Section 1 — "What This Product Does":
  - Smartphone app for diabetic retinopathy screening (NOT diagnosis)
  - Used by trained personnel (nurses, volunteers) with specialized lens attachment
  - Screening tool — flags potential problems, encourages professional follow-up
  - Target deployment: underresourced/remote areas, mobile clinics, home visits
  - Replaces expensive clinical equipment with low-cost smartphone solution
- [ ] 4.2 Section 2 — "How the Screening Works":
  - High-level: AI analyzes retina photographs to detect signs of diabetic retinopathy
  - Trained on thousands of expert-labeled images from clinical settings
  - Classifies into 5 severity levels (No DR, Mild, Moderate, Severe, Proliferative)
  - Explain as "pattern recognition from examples" — no jargon about layers/neurons/weights
  - The model learned to recognize visual patterns associated with each severity level
- [ ] 4.3 Section 3 — "Model Performance":
  - Embed `artifacts/global_confusion_matrix.png`
  - Embed accuracy table from `artifacts/global_metrics.png`
  - Cohen's Kappa score (explain: "measures agreement with expert doctors; 0.8+ = strong agreement")
  - Overall accuracy percentage
  - Interpret: where the model is strong vs. where it may struggle (e.g., adjacent severity levels)
  - **All numbers from our evaluation run, not hardcoded**
- [ ] 4.4 Section 4 — "What the Model Focuses On":
  - Embed aggregate Grad-CAM images per class from `artifacts/`
  - Explain in plain language: the model focuses on blood vessel patterns, dark spots (hemorrhages), bright spots (exudates), abnormal vessel growth
  - This demonstrates the model examines medically relevant features, not artifacts
- [ ] 4.5 Section 5 — "Training Data":
  - Source: APTOS 2019 Blindness Detection dataset (Kaggle)
  - Size: 2,929 training images, 733 test images
  - Embed `artifacts/global_class_distribution.png`
  - Labeling: rated by trained clinicians on 0-4 severity scale
  - Demographics: age and gender recorded; note any representation gaps
  - Data provenance: publicly available research dataset
- [ ] 4.6 Section 6 — "Fairness Considerations":
  - If subgroup analysis generated: embed `artifacts/global_fairness.png`, discuss findings
  - If not feasible: document as known limitation, describe what additional testing would be needed
  - Discuss potential demographic biases in training data
- [ ] 4.7 Section 7 — "Limitations and Responsible Use":
  - Screening tool only — does NOT replace professional diagnosis
  - Trained on specific dataset; may not generalize to all populations/ethnicities
  - Performance depends on image quality, camera hardware, lighting conditions
  - Not validated for: pediatric patients, certain rare conditions, non-fundus images
  - Class imbalance in training data (more No DR than severe cases)
  - Requires professional follow-up for all positive results
  - Should be used as part of a broader screening program, not standalone
  - Model confidence should be considered — low-confidence results need extra caution
- [ ] 4.8 Section 8 — "Data Privacy":
  - What patient data is collected: retina image, age, gender
  - How data is used: only for screening, not stored beyond session (or describe retention policy)
  - No names, addresses, or other PII beyond what's medically necessary
  - Retina images are biometric data — describe safeguards
- [ ] 4.9 Section 9 — "Reporting Issues":
  - Dedicated email for reporting misuse or harm (e.g., safety@[company].com)
  - In-app feedback mechanism for users to report incorrect or concerning results
  - Process: reports reviewed within X business days, corrective actions taken
  - Commitment to regular model updates and monitoring

---

## Phase 5: Local Explanation Document
**Deliverable:** `explanation_local.md`
**Audience: Nurses/volunteers + patients — 8th grade reading level, no jargon**
**Generated by code in explainability.ipynb Cell 20**

- [ ] 5.1 Write at 8th grade reading level throughout (short sentences, common words, no jargon)
- [ ] 5.2 Patient 1 report:
  - Header: "Your Eye Screening Results"
  - Patient info: ID, age, gender
  - **Automation disclosure:** "This screening was done by a computer program (AI), not a doctor."
  - **How it works:** "The computer looked at a photo of the back of your eye for signs of damage from diabetes."
  - **Who is involved:** "A health worker took your eye photo. A computer analyzed it. A doctor should confirm the result."
  - **What data was used:** "Only the photo of your eye was used. Your age and gender were recorded for your file."
  - Embed original retina image
  - Embed Grad-CAM overlay image with caption: "The colored areas show where the computer looked most closely. Red and yellow mean more attention."
  - **Screening result:** severity label in plain language
  - **What this means:** plain-language explanation of severity
  - Embed confidence chart with caption: "This chart shows how sure the computer is about the result."
  - **"What to do next":** specific actionable guidance based on severity level
  - Footer: "This is a screening tool. It does not replace a full eye exam by a doctor."
- [ ] 5.3 Patient 2 report (same structure, different patient/result — different severity level)
- [ ] 5.4 Verify readability: run Flesch-Kincaid grade level check (target ≤ 8th grade)

---

## Phase 6: Explanations Report
**Deliverable:** `explanations.md` (≤1000 words)

- [ ] 6.1 Section: "Global Explanations":
  - Techniques used: confusion matrix, classification report, Cohen's Kappa, class distribution, aggregate Grad-CAM, fairness subgroup analysis
  - How each meets procurement officer needs (map technique → need from explanation_needs.md)
  - Where to find them: point to specific sections in `explanation_global.md`
  - Code references: specific cells in `explainability.ipynb`
- [ ] 6.2 Section: "Local Explanations":
  - Techniques used: Grad-CAM heatmap overlay, confidence bar chart, plain-language screening text
  - How each meets nurse/volunteer needs (map technique → need)
  - How they satisfy all 5 sub-items of Policy §4
  - Where to find them: point to specific sections in `explanation_local.md`
  - Code references: specific cells in `explainability.ipynb`
- [ ] 6.3 Section: "Why Grad-CAM":
  - Justification over SHAP/LIME for CNN image classification
  - Spatial heatmaps are intuitive for medical images — shows "where the model looked"
  - No extra dependencies needed (uses tf.GradientTape)
  - More understandable for non-technical audience than pixel-level attributions
  - Presented as supporting explanation, not proof of correctness
- [ ] 6.4 Section: "How to Generate Local Explanations for Other Patients":
  - Step 1: Place patient retina image (.png) in `data/test_images/`
  - Step 2: Add row to `data/test.csv` with id_code, age, gender, diagnosis (if known)
  - Step 3: Open `explainability.ipynb`
  - Step 4: Change `PATIENT_IDS` list in Cell 2 to the new patient's id_code
  - Step 5: Run all cells (or cells 1-5 for setup, then cells 12-19 for local explanations)
  - Step 6: Output files saved to `artifacts/` — HTML report + images

---

## Phase 7: Policy Compliance Report
**Deliverable:** `compliance.md` (≤2000 words)
**Written as if submitting to compliance/legal team to approve product release**

- [ ] 7.1 Requirement 1 — Intended Use:
  - **Status:** Compliant
  - How addressed: `explanation_global.md` §1 describes purpose (screening, not diagnosis), setting (smartphone app, underresourced areas), intended users (trained nurses/volunteers), role of automation (assists screening, doesn't replace doctors)
  - Evidence: quote relevant sections from `explanation_global.md`

- [ ] 7.2 Requirement 2 — Accuracy Evidence:
  - **Status:** Compliant
  - How addressed: confusion matrix, Cohen's Kappa, per-class precision/recall/F1, overall accuracy — all computed from our evaluation run
  - Evidence: `artifacts/global_confusion_matrix.png`, `artifacts/global_metrics.png`, code in `explainability.ipynb`

- [ ] 7.3 Requirement 3 — How Model Works Generally:
  - **Status:** Compliant
  - How addressed: `explanation_global.md` §2 (high-level description) + §4 (aggregate Grad-CAM showing key features the model uses)
  - Evidence of documentation effectiveness: written for semi-technical procurement audience, uses analogies ("pattern recognition"), avoids ML jargon, Grad-CAM shows model focuses on medically relevant features

- [ ] 7.4 Requirement 4 — Individual Explanations (all 5 sub-items):
  - **Status:** Compliant
  - Evidence from `explanation_local.md` and generated HTML reports:
    - (1) **Automation was used:** "This screening was done by a computer program (AI), not a doctor."
    - (2) **How automation works:** "The computer looked at a photo of the back of your eye for signs of damage from diabetes." + Grad-CAM overlay
    - (3) **Additional actors involved:** "A health worker took your eye photo. A computer analyzed it. A doctor should confirm the result."
    - (4) **Personal data used:** "Only the photo of your eye was used. Your age and gender were recorded for your file."
    - (5) **Decision reached:** Specific screening result (severity level) + confidence percentage shown
  - Code: `explainability.ipynb` cells 12-19

- [ ] 7.5 Requirement 5 — Limitations & Misuse:
  - **Status:** Compliant
  - How addressed: `explanation_global.md` §7 lists concrete limitations, risks, and mitigations
  - Specific risks identified:
    - Misuse as diagnostic tool (instead of screening)
    - Use on populations not represented in training data
    - Image quality degradation (poor lighting, dirty lens, wrong angle)
    - Over-reliance without professional follow-up
    - Use by untrained operators
  - Mitigations described for each risk

- [ ] 7.6 Requirement 6 — Data Description & PII:
  - **Status:** Compliant
  - How addressed: `explanation_global.md` §5 (training data) + §8 (data privacy)
  - Data described: APTOS 2019 dataset, size, labeling process, class distribution
  - PII justification: retina images medically necessary for screening; age/gender provide clinical context; no names/addresses collected; retina images as biometric data — safeguards described

- [ ] 7.7 Requirement 7 — Misuse Reporting:
  - **Status:** Compliant
  - How addressed: `explanation_global.md` §9 describes reporting mechanism
  - Mechanism: dedicated email, in-app feedback button, investigation process, timeline

- [ ] 7.8 Requirement 8 — Language Requirements:
  - **Status:** Compliant
  - How addressed:
    - Global docs (`explanation_global.md`): professional semi-technical language for procurement officers
    - Local docs (`explanation_local.md` + HTML reports): 8th grade reading level for nurses/volunteers/patients
  - Evidence: Flesch-Kincaid readability score computed on local explanation text (target ≤ 8.0)

---

## Execution Order & Dependencies

```
Phase 0: Project setup                ← Verify model loads, test image loads, find Grad-CAM layer
    ↓
Phase 1: explanation_needs.md         ← No code deps, write first — drives what to generate
    ↓
Phase 2: explainability.ipynb         ← Core code, all explanations generated here
  ├── 2A: Setup & data loading
  ├── 2B: Global explanation code     ← Generates artifacts/ images for Phase 4
  └── 2C: Local explanation code      ← Generates artifacts/ images + HTML for Phase 5
    ↓
Phase 3: explanation_template.html    ← Enhance for nurse/patient audience (needed by 2C)
    ↓ (actually Phase 3 should come before 2C runs, or be done alongside 2C)
Phase 4: explanation_global.md        ← Needs Phase 2B artifacts
Phase 5: explanation_local.md         ← Needs Phase 2C artifacts + Phase 3 template
    ↓
Phase 6: explanations.md             ← References Phases 4 & 5
Phase 7: compliance.md               ← References everything above
```

**Practical order:**
1. Phase 0 (setup verification)
2. Phase 1 (explanation_needs.md)
3. Phase 3 (enhance HTML template — needed before generating reports)
4. Phase 2 (explainability.ipynb — all code)
5. Phase 4 (explanation_global.md — using generated artifacts)
6. Phase 5 (explanation_local.md — using generated artifacts)
7. Phase 6 (explanations.md)
8. Phase 7 (compliance.md)

---

## Files Created/Modified Summary

| File | Action | Description |
|------|--------|-------------|
| `explanation_needs.md` | CREATE | Stakeholder needs analysis |
| `explainability.ipynb` | CREATE | All explainability code (local paths, parameterized) |
| `explanation_template.html` | MODIFY | Enhanced screening result template for nurse/patient audience |
| `explanation_global.md` | CREATE | Global explanations for procurement officers |
| `explanation_local.md` | CREATE | Local explanations for 2 patients (generated by code) |
| `explanations.md` | CREATE | Explanation report linking needs to solutions |
| `compliance.md` | CREATE | Policy compliance for 8 requirements |
| `artifacts/` | CREATE | Directory for all generated plots, images, HTML reports |

---

## Grading Checklist (100 pts)

- [ ] (10 pts) `explanation_needs.md` — needs for both stakeholders, process described, evidence provided
- [ ] (10 pts) `explanation_global.md` — global explanations for procurement officers + described in `explanations.md`
- [ ] (10 pts) `explanation_local.md` — local explanations for 2 patients + described in `explanations.md`
- [ ] (10 pts) Code produces local explanations for other patients, clear instructions provided (parameterized PATIENT_IDS)
- [ ] (10 pts) Explanations designed for target stakeholders, not developers
- [ ] (5 pts) Compliance §1 — Intended use described
- [ ] (5 pts) Compliance §2 — Accuracy evidence provided (from our evaluation, not hardcoded)
- [ ] (5 pts) Compliance §3 — How model works generally + evidence effective
- [ ] (5 pts) Compliance §4 — Individual explanations with all 5 sub-requirements explicitly covered
- [ ] (5 pts) Compliance §5 — Limitations and misuse described with mitigations
- [ ] (5 pts) Compliance §6 — Data described, PII justified
- [ ] (5 pts) Compliance §7 — Misuse reporting mechanism
- [ ] (5 pts) Compliance §8 — Language appropriate for audience (8th grade verified with Flesch-Kincaid)
- [ ] (10 pts) Office hours reflection (prepare talking points)

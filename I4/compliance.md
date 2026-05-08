# Policy Compliance Report

This report evaluates whether our diabetic retinopathy screening system complies with each of the eight internal responsible AI policy requirements. For each requirement, we describe how it was addressed, provide evidence, and note any gaps or additional steps needed.

---

## Requirement 1: Intended Use

> *Describe the automated system's intended use and the role of the automation (model). Include its purpose, setting of use, and intended user(s).*

**Status: Compliant**

**How addressed:** `explanation_global.md` Section 1 ("What This Product Does") describes the system's intended use in detail:

- **Purpose:** Screening for diabetic retinopathy to identify patients who may need further evaluation by an eye doctor.
- **Setting:** Smartphone-based screening at mobile clinics, rural health posts, and community outreach programs in underresourced regions.
- **Intended users:** Trained health workers (nurses, volunteers) who operate the device. Patients are the subjects of the screening.
- **Role of automation:** The AI classifies retina photographs into five severity levels. It assists the screening process but does not replace professional clinical judgment. The system explicitly states it is a screening tool, not a diagnostic device.
- **Use in combination with other information:** The screening result is one input into a referral decision. Health workers consider the screening result alongside patient history and clinical context. A doctor confirms any positive screening before treatment.

**Evidence:** See `explanation_global.md` Section 1. The local explanation reports (`explanation_local.md`) also identify the three actors involved: "You (the health worker) took the eye photo. A computer program analyzed it. A doctor should confirm the result before any treatment decisions."

---

## Requirement 2: Accuracy Evidence

> *Provide evidence that the automation (model) functions accurately, consistently, and effectively in the intended use case.*

**Status: Partially compliant — strong preliminary evidence provided, but independent validation is outstanding**

**How addressed:** `explanation_global.md` Section 3 ("Model Performance") provides quantitative evidence of model accuracy computed from our own evaluation run on a held-out test set of 731 images. This constitutes internal testing evidence, not independent review or real-world clinical validation.

**Evidence provided:**
- **Overall accuracy:** 88.5% on a held-out test set of 731 images (`explainability.ipynb` Cell 9)
- **Cohen's Kappa (quadratic weighted):** 0.913 — indicating very strong agreement with expert clinician grading. The Kappa metric accounts for chance agreement, making it more robust than accuracy alone (`explainability.ipynb` Cell 9)
- **Confusion matrix:** Shows per-class accuracy and common misclassification patterns, enabling assessment of which errors are clinically significant (`artifacts/global_confusion_matrix.png`, Cell 8)
- **Per-class precision/recall/F1:** Detailed breakdown for each severity level, revealing that the model is strongest for No DR (F1=0.99) and Moderate (F1=0.84) (`artifacts/global_metrics.png`, Cell 9)
- **Consistency evidence:** Performance is evaluated across demographic subgroups (gender and age) in `artifacts/global_fairness.png` (Cell 14), showing broadly consistent accuracy without gross demographic disparities
- **Reproducibility:** All metrics are computed programmatically in `explainability.ipynb` and can be independently verified by re-running the notebook with the same data and model

**Limitations noted:** The model has lower recall for Severe (46%) and Proliferative DR (54%), meaning some serious cases may be under-detected. This is honestly disclosed in `explanation_global.md` Section 3 and Section 7, along with the recommendation that all screenings be followed by professional evaluation.

**Additional steps for stronger compliance:** This evidence constitutes internal accuracy testing on a held-out dataset. For full compliance, we would additionally recommend:
- Independent validation on a separate dataset representative of the target deployment population
- A prospective clinical study comparing screening outcomes to standard-of-care ophthalmologist grading
- Ongoing real-world performance monitoring after deployment to detect distribution shift or degradation

---

## Requirement 3: How the Model Works Generally

> *Describe how the automation (model) works generally. Provide evidence that the documentation is effective for the policy purpose. Where possible identify general mechanisms or factors that most strongly influence the automation.*

**Status: Compliant**

**How addressed:**
- `explanation_global.md` Section 2 ("How the Screening Works") provides a plain-language description of the AI approach: it was trained on thousands of expert-labeled retina images and learned to recognize visual patterns associated with each severity level.
- `explanation_global.md` Section 4 ("What the Model Focuses On") provides aggregate Grad-CAM visualizations showing the general factors that influence the model's decisions — it focuses on blood vessel patterns, hemorrhages, and areas of abnormal growth, which are the clinically relevant features for grading diabetic retinopathy.

**General mechanisms/factors identified:** The aggregate Grad-CAM analysis (Section 4) identifies the key factors influencing the model's decisions per severity level: diffuse attention for healthy eyes, focus on microaneurysms and small hemorrhages for mild/moderate cases, and concentration on extensive hemorrhaging and abnormal vessel growth for severe/proliferative cases. These correspond to the clinical features ophthalmologists use for grading.

**Evidence of documentation effectiveness:**
- The global explanation is written for a semi-technical procurement audience using accessible analogies ("pattern recognition from examples") rather than ML terminology. A manual review found no unnecessary ML jargon such as layers, neurons, backpropagation, gradient, epoch, or softmax in `explanation_global.md`.
- The Grad-CAM visualizations make the model's decision factors concrete and verifiable — a procurement officer can compare the highlighted regions against published clinical literature on diabetic retinopathy features to confirm the model attends to the right areas.
- Every chart and metric is accompanied by an interpretation paragraph explaining what it means for the procurement decision, rather than leaving the reader to draw their own conclusions from raw data.

**Code references:** Aggregate Grad-CAM generation is in `explainability.ipynb` Cells 12-13. The visualization shows averaged attention patterns across multiple correctly-classified images per class.

---

## Requirement 4: Individual Explanations

> *Provide a mechanism to describe how the automation worked with regard to an instance of use to all intended users and subjects. Descriptions must include (1) that automation was used, (2) a short explanation of how the automation works, (3) what additional actors are involved in decisions, (4) what significant personal data was used for the decision, (5) what decisions were reached in a specific case.*

**Status: Compliant**

**How addressed:** Each patient screening report (see `explanation_local.md` and the HTML reports in `artifacts/`) explicitly addresses all five sub-requirements:

1. **That automation was used:** Every report prominently displays: *"This screening was performed by a computer program (AI), not a doctor. Please communicate this to the patient and emphasize that a doctor should confirm the result."* This appears in a highlighted notice box at the top of the HTML report and at the start of each patient section in `explanation_local.md`.

2. **How the automation works:** Each report includes: *"A photo was taken of the back of the patient's eye using a smartphone with a special lens. A computer program analyzed the photo for signs of blood vessel damage that can be caused by diabetes."* Additionally, a Grad-CAM overlay visually shows where the model focused for this specific patient.

3. **Additional actors involved:** Each report explicitly lists the three actors: *"You (the health worker) took the eye photo. A computer program analyzed it. A doctor should confirm the result before any treatment decisions."* This clearly identifies the health worker (operator), AI (analysis), and doctor (confirmation).

4. **Personal data used:** Each report states: *"The computer used only the eye photo to produce the screening result. The model does not use age or gender for its analysis. Age and gender are recorded in the patient's medical file for clinical context only."* This clearly separates model inputs (eye photo only) from administrative data (age, gender for the record).

5. **Decisions reached:** Each report shows the specific screening result (e.g., "Screening Result: Moderate"), a plain-language description of what it means, and a confidence score with visual chart. The Grad-CAM overlay provides a visual explanation of the specific decision.

**Evidence:** See `explanation_local.md` for two complete patient examples. The code that generates these reports is in `explainability.ipynb` Cells 16-21. HTML reports are saved in `artifacts/`.

**Accessibility:** All individual explanations are written at approximately an 8th grade reading level using short sentences, common words, and no medical or technical jargon. Reports can be displayed on-screen or printed as handouts.

---

## Requirement 5: Limitations and Misuse Potential

> *Describe limitations and misuse potential of the automated system beyond its intended purpose and any provided mitigations.*

**Status: Compliant**

**How addressed:** `explanation_global.md` Section 7 identifies seven limitations with mitigations: (1) screening-not-diagnosis risk mitigated by "screening only" language on every report, (2) training data scope, (3) image quality dependency, (4) class imbalance causing under-detection of severe cases, (5) unvalidated populations, (6) infrastructure requirements, (7) not a standalone solution. Misuse potential includes treating results as definitive diagnosis, deploying without trained operators, using results to deny care, and operating without referral pathways.

---

## Requirement 6: Data Description and PII Justification

> *Describe the data used by the automated system. Justify the use of personal identifiable information.*

**Status: Compliant**

**How addressed:**

**Training data** (`explanation_global.md` Section 5): The model was trained on the APTOS 2019 Blindness Detection dataset — 2,929 retinal fundus photographs labeled by clinicians. The dataset source, size, labeling process, and class distribution are documented with a visualization.

**Patient data collected during screening:**
- **Retinal fundus photograph:** The sole input to the model. Required for the screening — without it, no screening can occur.
- **Age:** Not used by the model. Recorded for the patient's medical file and clinical context (diabetic retinopathy risk correlates with age).
- **Gender:** Not used by the model. Recorded for the patient's medical file.

**PII justification:** Retinal images are biometric data and constitute PII. Their collection is justified because:
1. They are the essential input for the screening — no alternative data can serve this purpose.
2. No names, addresses, or other identifying information beyond age and gender are collected.
3. Organizations deploying the tool are responsible for establishing data retention, storage, and transmission policies per local regulations.
4. The deploying organization should define appropriate security measures for handling retinal images as biometric data.

**What is NOT collected:** Names, addresses, identification numbers, insurance information, or any other personally identifying information beyond the three items listed above.

---

## Requirement 7: Misuse/Harm Reporting

> *Describe how to report misuse or harm from the automated system.*

**Status: Partially compliant — reporting mechanisms are designed but not yet implemented**

**How addressed:** `explanation_global.md` Section 9 ("Reporting Issues") describes the proposed reporting mechanism. These are recommended mechanisms for deploying organizations, not yet built into the product:

- **Email:** A dedicated safety reporting email should be established by the deploying organization for reporting incorrect results, product malfunctions, or safety concerns.
- **In-app:** The application should include a "Report Issue" feature on every screening result screen, allowing operators to flag concerns.
- **Organizational process:** Deploying organizations should define a review timeline and escalation procedure for reported issues.

**Additional steps for stronger compliance:** In production, we would recommend:
- A toll-free phone line for regions with limited email/internet access
- Multilingual reporting options for international deployments
- Quarterly aggregated safety reports shared with deploying organizations
- An independent review board for serious adverse events

---

## Requirement 8: Language Requirements

> *Provide all documentation in language appropriate for the intended audience. All documentation for untrained users must use nontechnical language at an eighth grade reading level.*

**Status: Compliant — verified by Flesch-Kincaid readability analysis**

**How addressed:**

**Global explanations** (`explanation_global.md`): Written in professional but accessible language for semi-technical procurement officers. Statistical concepts (accuracy, Cohen's Kappa) are explained in context. No ML jargon (layers, neurons, gradients, backpropagation) is used. Visualizations include plain-language captions and interpretations.

**Local explanations** (`explanation_local.md` and HTML reports): Written for nurses/volunteers using short sentences, everyday vocabulary (e.g., "eye damage" not "retinopathy"), clear section headings, and actionable guidance.

**Evidence of readability:** We computed the Flesch-Kincaid Grade Level on the patient-facing text using the `textstat` library (`explainability.ipynb` Cell 22):

- **Flesch-Kincaid Grade Level: 6.1** (target: ≤ 8.0) — **PASS**
- **Flesch Reading Ease: 72.3** (70–80 = fairly easy)
- **Average Sentence Length: 11.9 words**

The overall score of 6.1 is well within the 8th grade requirement.

**Both audiences are served:** The global and local explanations are clearly separated and tailored to their respective audiences rather than using a one-size-fits-all approach.

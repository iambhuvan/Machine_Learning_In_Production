# Explanation Needs Analysis

## Process for Identifying Explanation Needs

To identify what each stakeholder needs from our diabetic retinopathy screening system, we followed a structured process:

1. **Persona development:** We created representative personas for each stakeholder group based on their professional roles, decision-making context, and technical background.
2. **Contextual research:** We studied how diabetic retinopathy screening works in underresourced settings, including WHO guidelines on community-based screening programs, the role of non-physician graders, and the referral pathway from screening to treatment ([WHO Diabetic Retinopathy Screening Guide](https://www.who.int/publications/i/item/9789241515856); [APTOS 2019 Kaggle Competition](https://www.kaggle.com/c/aptos2019-blindness-detection)).
3. **Hazard analysis:** We considered what could go wrong if explanations are missing, misleading, or inappropriate for the audience — such as a procurement officer buying an unreliable tool, or a nurse giving a patient false reassurance.
4. **Policy mapping:** We reviewed the company's 8-point responsible AI policy to ensure explanation needs align with compliance requirements, particularly around automation disclosure, data transparency, and accessible language.

---

## Stakeholder 1: Procurement Officers at Non-Profit Organizations

### Persona
Maria is a procurement director at a global health non-profit. She has a public health background but is not a machine learning expert. She evaluates medical tools for deployment across clinics in rural areas of Sub-Saharan Africa and South Asia. She must justify purchases to donors and boards, demonstrate due diligence, and ensure tools meet regulatory and ethical standards. She reads product datasheets and evaluation reports, not code.

### Identified Explanation Needs

1. **What the product does and how it fits into the screening workflow.** Maria needs to understand the product's role — that it is a screening aid, not a diagnostic device, and how it integrates with existing referral pathways. Without this, she cannot assess whether it suits her organization's operations.

2. **Evidence of accuracy and reliability.** She needs quantitative performance data — overall accuracy, per-class error rates, and a measure of agreement with expert clinicians (e.g., Cohen's Kappa). She needs to trust that the tool performs well enough to justify deployment and will not cause unacceptable rates of missed cases or false alarms.

3. **How the model works at a high level.** She does not need to understand neural network architecture, but she needs a plain-language explanation of the approach: that the system was trained on thousands of expert-labeled retina images and learned to recognize visual patterns associated with disease severity. Visual evidence (such as Grad-CAM heatmaps) showing the model focuses on medically relevant areas builds trust.

4. **Training data description and potential biases.** She needs to know where the data came from, how large it is, how it was labeled, and whether certain demographic groups or severity levels are underrepresented. This informs whether the tool is appropriate for her target population.

5. **Fairness considerations.** If available, performance breakdowns by age or gender help her assess equitable outcomes. If not available, she needs an honest disclosure of this limitation.

6. **Limitations and risks.** She needs a clear list of what the tool cannot do, where it may fail (e.g., poor image quality, populations not in training data), and what mitigations are in place. This is critical for responsible procurement and managing expectations.

7. **Data privacy practices.** She needs to know what patient data is collected, how it is used, and what safeguards protect it — especially given deployment in regions with varying data protection regulations.

8. **How to report issues.** She needs a clear mechanism for reporting product failures or misuse, so her field teams have a support pathway.

---

## Stakeholder 2: Nurses or Volunteers Who Perform the Screening

### Persona
James is a community health volunteer in a rural clinic. He completed a training program on using the smartphone screening app but has no medical imaging or AI background. He performs eye screenings during mobile clinic visits and must explain results to patients — many of whom have limited health literacy and may be anxious. He needs to communicate results clearly, know when to make urgent referrals, and maintain patient trust.

### Identified Explanation Needs

1. **Automation disclosure.** James needs a clear, prominent statement that the screening was performed by a computer program (AI), not a doctor. Patients have a right to know, and this is required by internal policy.

2. **Plain-language result explanation.** The screening result must be stated in simple terms — not medical codes or class numbers, but words like "The screening did not find signs of eye damage" or "The screening found signs of moderate eye damage." Language must be at an 8th grade reading level or below.

3. **Visual explanation of what the model detected.** A Grad-CAM heatmap overlay on the retina image, with a simple caption like "The colored areas show where the computer looked most closely," helps James point to what the AI found. This makes the result more concrete and trustworthy, without requiring technical understanding.

4. **Confidence level.** James needs to see how confident the computer is in the result (high, moderate, or low), so he knows when to be extra cautious and emphasize the need for professional follow-up.

5. **Who is involved in the decision.** The report should make clear that James (the health worker) took the photo, the computer analyzed it, and a doctor should confirm the result. This sets appropriate expectations about the screening's role in the care pathway.

6. **What data was used.** The report should state that only the eye photo was used for the screening, and that age and gender were recorded for the medical file. This addresses patient questions about privacy.

7. **Actionable next steps.** For each severity level, James needs specific guidance: "No action needed beyond regular checkups" vs. "Please see an eye doctor within the next few weeks" vs. "Please see an eye doctor as soon as possible." This is the most operationally important part of the explanation.

8. **Disclaimer.** Every report must remind both James and the patient that this is a screening tool, not a full eye exam, and that a doctor should confirm the result.

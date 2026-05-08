# MLIP Midterm 2 — Past Exam Papers Q&A

---

# FALL 2025 — Surveillance4All (Home Surveillance AI)

---

## Question 1: Scaling and Operations [25 points]

### (a) [8 pts] — Deployment Architecture

**Answer: Batch processing**

Justification: The 500GB model cannot be economically loaded into memory for each individual request — loading it takes significant time and resources, making on-demand ("as a service") inference impractical. Surveillance4All's use case also tolerates latency: homeowners receive recommendations about maintenance or past events (e.g., "gutter cleaning", reviewing overnight footage), not real-time alerts requiring sub-second response. Batch processing optimizes for throughput over response time — it can amortize the cost of loading the 500GB model across thousands of 30MB inputs processed together. Stream processing would help decouple producers/consumers but still requires loading the large model per event, offering no advantage over batch here.

**Slides:** 12 scaling.pdf slide 28 (Data Processing Overview — Services=online/response-time-focused, Batch=offline/throughput-focused, Stream=near-real-time/event-driven); slides 34–37 (Batch Processing detail)

---

### (b) [5 pts] — Versioning Strategy

**Answer: Recording offsets**

Justification: The tabular data is append-only (image data) or very rarely corrected (<0.1%/year). Recording offsets — treating the dataset as an append-only log and storing only the position/pointer to where each version starts — is the most space efficient. Keeping copies would duplicate the entire dataset for each version. Tracking deltas stores the differences between versions, which is more efficient than copies but still stores change records. Since corrections are extremely rare (<0.1%), the delta/offset overhead is minimal — recording offsets means you only store the new/corrected rows and a pointer, never duplicating the >99.9% of unchanged data.

**Slides:** 18 provenance.pdf slide 11 (versioning strategies: copies vs. deltas vs. offsets/append-only)

---

### (c) [6 pts] — MLFlow + Additional Tracking

**How MLFlow can help:**
MLFlow logs each training run as an experiment with: (1) the model version/artifact (the trained 500GB foundation model checkpoint), (2) hyperparameters and training config, (3) evaluation metrics (e.g., accuracy, F1 on held-out sets), and (4) a reference to the code version (git commit hash). At inference time, you tag each prediction with the MLFlow run ID / model version used, enabling you to trace any prediction back to the exact model that produced it.

**What information needs to be tracked additionally:**
MLFlow does not natively version large datasets. You need to track which training data snapshot was used — this requires a separate data versioning tool like DVC (Data Version Control), which stores dataset hashes/pointers alongside the MLFlow run. You also need to log: (1) the data preprocessing pipeline version, (2) the infrastructure/environment (Docker image, GPU type, library versions), and (3) the mapping from deployed model version → inference requests (a deployment registry or model serving metadata store). Without the data version, you cannot reproduce the model even with the MLFlow artifact.

**Slides:** 18 provenance.pdf slide 16 (MLFlow experiment tracking — parameters, metrics, artifacts), slide 17 (DVC — Data Version Control for datasets)

---

### (d) [6 pts] — Technical Debt

**Technical debt example:**
Manually deploying model updates by SSH-ing into a server and running a script, rather than implementing a proper CI/CD pipeline with automated testing and staged rollouts.

**Rationale for taking on the debt:**
This is prudent, deliberate technical debt (Fowler's quadrant). The team lacks software engineering expertise and is focused on rapid prototyping. Setting up a full MLOps CI/CD pipeline requires significant engineering time. In the short term, manual deployment is fast to implement and allows the team to ship the product and validate market fit. The team consciously knows this doesn't scale.

**Better solution:**
Implement a proper CI/CD pipeline with automated model validation (offline evaluation on a holdout set before promotion), a staging environment for canary/shadow deployment testing, and an MLFlow Model Registry with approval gates before production promotion. This prevents regressions when retraining on new data and supports safe rollbacks.

**Slides:** 17 process (1).pdf slide 40 (Technical Debt Metaphor), slide 43 (Fowler's Technical Debt Quadrant — prudent/deliberate vs. reckless/inadvertent), slide 45 (Technical Debt Examples)

---

## Question 2: Fairness [18 points]

### (a) [4 pts] — Harm Type

**Answer: A harm of allocation**

Justification: Allocation harm occurs when a system withholds opportunities, resources, or protection from a group. Here, the model makes more mistakes for low-income households — it either produces more false alarms (wasted police/homeowner response) or more missed detections (failing to alert of a real intruder). Either way, the system delivers a lower-quality service to low-income homeowners. This is not representation harm, which would be about how a group is depicted or stereotyped in outputs.

**Slides:** 23 system fairness.pdf slide 24 (Analyze Potential Harms — allocation harm vs. representation harm)

---

### (b) [6 pts] — Source of Bias

**Selected: Skewed sample**

Explanation: The training data was collected from "early customers" — likely tech-forward, higher-income homeowners who could afford to be early adopters of a home surveillance subscription system. This means training images predominantly come from higher-income homes (better lighting, different architectural styles, landscaping, etc.). Low-income neighborhoods are underrepresented in training data. As a result, the model has seen fewer examples of the visual conditions in those environments, leading to systematically worse predictions for low-income households — not because of malicious intent, but because of a mismatch between training data distribution and deployment distribution.

**Slides:** 23 system fairness.pdf slides 34–37 (Sources of data bias: historical bias, tainted labels, skewed sample, limited features, proxies)

---

### (c) [2 pts] — Fairness Notion Without Ground Truth

**Answer: Group fairness (demographic parity)**

You have 1000 predictions for low-income homes and 5000 for high-income homes, and can see how often the model flagged an intruder / recommended an action. Without ground truth (actual outcomes), you can compute whether the rate of positive predictions (e.g., "intruder detected" alerts) is similar across the two income groups — this is demographic parity. Anti-classification requires checking the model's inputs (removing protected attributes), which may not be available. Equalized odds requires actual labels (ground truth) to compute TPR/FPR.

**Slides:** 22 fairness measures.pdf slides 24–26 (Group fairness / Demographic parity — only requires predicted labels, not ground truth)

---

### (d) [6 pts] — Fairness Interventions

**Intervention 1: Threshold adjustment (post-processing)**
Apply group-specific decision thresholds for triggering alerts. For example, calibrate the confidence threshold for "intruder detected" separately for low-income vs. high-income zip codes so that the false positive rate is equalized across groups. This is a post-processing intervention that doesn't require retraining the model and directly counteracts the systematic performance gap.

**Intervention 2: Targeted data collection / human-in-the-loop relabeling**
Actively recruit early customers in low-income areas and collect labeled training data from those environments. Pair this with a human review queue: route uncertain predictions from underrepresented zip codes to human reviewers, who label them correctly. These verified labels are fed back into retraining, addressing the root skewed-sample problem rather than patching it at the threshold level.

**Slides:** 23 system fairness.pdf slides 42–56 (Bias mitigation and fairness interventions — threshold adjustment, human oversight, targeted data collection)

---

## Question 3: Explainability/Transparency [9 points]

### (a) [5 pts] — Individual Explanation Technique for Data Scientists

**Technique: SHAP (SHapley Additive exPlanations)**

SHAP provides a per-prediction explanation showing how much each input feature contributed to the model's output for a specific instance. Grounded in cooperative game theory (Shapley values) — for each prediction, it asks "if we add each feature one at a time, how much does the prediction change?" The contribution of each feature is averaged across all possible orderings of features. For Surveillance4All's vision model, SHAP can highlight which image regions or metadata features (time of day, camera orientation, location) drove the "intruder detected" prediction. A data scientist can use this to diagnose a faulty prediction — e.g., "the model flagged an intruder because of shadows near the garage, not an actual person."

**Slides:** 19 explainability.pdf slides 44–51 (Local/individual explanations: LIME, SHAP Force Plot)

---

### (b) [4 pts] — Appropriate for Homeowners?

**Answer: No — not directly appropriate for homeowners.**

SHAP outputs feature importance scores or highlighted image regions with numerical weights — this is technical transparency, not meaningful transparency. A homeowner does not understand what "feature 47 has SHAP value +0.83" means, nor can they act on it. For homeowners, explanations must be socially meaningful — framed as a social communication that helps them make a decision: e.g., "A person was detected near your back door at 2am moving toward the garage." SHAP gives the right tool for model debugging (data scientists), but would need significant translation/reformulation to be useful for a non-technical homeowner audience.

**Slides:** 20 transparency.pdf slides 18–19 (Explanations as Social Communication — meaningful transparency vs. technical transparency; explanations must be tailored to the audience's needs and context)

---

## Question 4: Security and Robustness [14 points]

### (a) [6 pts] — ML-Specific Attack

**Assumption:** The attacker (a thief planning a burglary) can submit a small number of fake camera images to the system, either by temporarily replacing camera feeds or submitting images to the public data collection pipeline.

**Attacker goal:** Cause the model to consistently misclassify a specific person (the thief) as a non-threat — so that when the thief enters the property, the system does not alert the homeowner or recommend calling 911.

**Attack method: Targeted backdoor poisoning attack.** The attacker injects carefully crafted training examples into the data pipeline (e.g., submitting images of themselves labeled as "no action needed" or "wildlife"). These poisoned samples embed a backdoor trigger (e.g., a specific t-shirt pattern or IR marker) so the model learns to classify that specific trigger as benign. During the actual burglary, the attacker wears the trigger pattern, causing the model to suppress alerts.

**Security property undermined:** Integrity — the model produces incorrect outputs on a specific targeted input, despite appearing to function correctly otherwise.

**Mitigation strategy:** Implement data provenance and validation on all training data ingestion — verify sources, flag statistical anomalies in labels, apply anomaly detection on new training batches. Use differential privacy during training to limit influence of any single data point. Regularly audit model behavior on known test cases to detect drift on specific inputs.

**Slides:** 14 ml security.pdf slides 12–13 (CIA triad), slides 45–54 (Poisoning attacks — targeted poisoning, backdoor attacks)

---

### (b) [4 pts] — System-Level Robustness Intervention

**Intervention: Redundant sensors + ensemble voting**

Deploy multiple camera types (standard optical cameras + motion/IR sensors) covering each zone of the house. The intruder detection decision is made by combining outputs from multiple independent sensors/models — a confirmed alert requires agreement from at least two sources. This is a system-level robustness improvement because it remains effective even when individual cameras are obscured, tampered with, or produce non-robust predictions. No single point of failure can suppress the alert. This mirrors the defense-in-depth principle: the system is robust even if the ML model produces incorrect predictions on some inputs.

**Slides:** 16 safety (1).pdf slide 44 (Improving Robustness for Safety — system-level: redundant components, ensemble learning, multiple sensors)

---

### (c) [4 pts] — Assurance Case for 95% Availability

The 7-day 98% uptime measurement is insufficient alone — it covers only one week and provides no structural argument for why the system will remain available.

**Argument 1:** Subclaim — The system is architected with redundancy so no single component failure causes total outage.
Evidence: Architecture documentation showing load-balanced servers across multiple availability zones; chaos engineering test results demonstrating automatic failover restores service within seconds with no user-visible downtime.

**Argument 2:** Subclaim — The system gracefully degrades under high load and has a tested recovery mechanism.
Evidence: Load testing results showing 95%+ availability under 2× peak traffic; a defined and tested circuit-breaker/fallback mode (e.g., cached predictions or simpler rule-based alerts when the 500GB model server is temporarily unavailable), demonstrated via integration tests and a documented incident runbook.

**Slides:** 16 safety (1).pdf slides 63–65 (Assurance Cases — structure: claim → sub-claims → evidence), slide 67 (Breakout: what evidence besides reliability measurement?), slide 68 (Benefits & Limitations)

---
---

# FALL 2024 — AgriVision AI (Precision Agriculture with Drones)

---

## Question 1: Scaling and Operations [19 points]

### (a) [6 pts] — Deployment Architecture

**Answer: Batch processing**

Justification: The current Flask service must hold a 500GB model in memory continuously (or reload it per request) to respond immediately — extremely costly for an infrequent, upload-triggered workflow. Farmers fly drones, upload imagery, and expect results within hours, not milliseconds: there is no low-latency requirement that forces "as a service." Batch processing is throughput-optimized: the model is loaded once, many farmers' 30MB drone uploads are processed together in a scheduled job (e.g., nightly), amortizing the enormous model-loading cost. Stream processing would still require the 500GB model available for each event and doesn't offer throughput gains of batching. Lambda architecture adds operational complexity with no benefit here — the scenario has no mixed real-time + historical query requirement.

**Slides:** 12 scaling.pdf slide 28 (Data Processing Overview); slides 34–37 (Batch Processing)

---

### (b) [4 pts] — Versioning Strategy

**Answer: Recording offsets**

Explanation: The tabular data (farm locations, crop yields) is predominantly append-only, with less than 0.1% corrected per year. Recording offsets treats the dataset as an append-only log — each version is simply a pointer to where valid data starts/ends, and corrections are appended as new records. No data is duplicated. Keeping copies would store the full dataset for every version — enormous waste when 99.9%+ of data is unchanged. Tracking deltas is more efficient than copies but still stores change records for every version; with corrections this rare, even the delta overhead adds up over time.

**Slides:** 18 provenance.pdf slide 11 (versioning strategies: copies vs. deltas vs. offsets/append-only)

---

### (c) [4 pts] — MLFlow + Additional Tracking

**How MLFlow can help:**
MLFlow logs each training run as an experiment with: the exact model artifact (versioned 500GB checkpoint stored in MLFlow's artifact store), hyperparameters used during training, evaluation metrics (accuracy on crop stress detection, fertilizer recommendation error rates), and the git commit hash of the training code. At inference time, each prediction is tagged with the MLFlow run ID, so you can always trace "which model version made this recommendation for Farm X on date Y."

**What needs to be tracked additionally:**
MLFlow does not version large training datasets. You must separately track which dataset snapshot was used — typically with DVC (Data Version Control), which stores checksums/pointers to the USDA satellite imagery, customer drone images, and crop yield records. Additionally track: (1) data preprocessing pipeline version, (2) cloud infrastructure/environment (Docker image, library versions, GPU type), and (3) a model serving registry mapping deployed model version → inference request timestamps, so you can audit which customers received predictions from which model generation.

**Slides:** 18 provenance.pdf slide 16 (MLFlow — parameters, metrics, artifacts), slide 17 (DVC — Data Version Control)

---

### (d) [5 pts] — Prudent and Deliberate Technical Debt

**Example:** Manually triggering model retraining and deployment by running a script via SSH rather than building an automated CI/CD pipeline with model validation, staged rollout, and automated regression testing.

**Why prudent:** This shortcut is justifiable given the team's current situation — they lack software engineering expertise and are focused on proving the core AI product works at scale. Setting up a full MLOps pipeline is a significant engineering investment. The simpler approach gets the product to paying farmers faster, allowing the team to gather real-world feedback before investing in automation.

**Why deliberate:** The team is consciously aware they are taking this shortcut. They understand the "better" solution, recognize the risk (manual errors in deployment, regression when retraining on new USDA/customer data), and have made a calculated decision to defer the investment — it's documented as a known gap, not an accident. This puts it in Fowler's "prudent/deliberate" quadrant, not reckless/inadvertent.

**Slides:** 17 process (1).pdf slide 43 (Fowler's Technical Debt Quadrant — prudent/deliberate vs. reckless/inadvertent), slides 40, 45

---

## Question 2: Fairness [12 points]

### (a) [4 pts] — Harm Type

**Answer: A harm of allocation**

Brief explanation: Allocation harm occurs when a system distributes resources, opportunities, or services unequally across groups. Here, the model makes more mistakes for small farms — it either over-recommends fertilizer (wasting money/harming soil) or under-detects crop stress (leading to crop loss). Both outcomes mean small farms receive a worse-quality service than large farms: they are denied the accurate agricultural recommendations they paid for. This is not representation harm, which would be about how a group is depicted or stereotyped.

**Slides:** 23 system fairness.pdf slide 24 (allocation harm vs. representation harm)

---

### (b) [6 pts] — Two Bias Sources

**Selected #1: Skewed sample**

Explanation: The training data comes primarily from USDA public reports and large commercial customers — large farms are far better represented. USDA satellite imagery and crop records skew toward large commercial operations because they are more likely to have submitted detailed government reports, enrolled in precision agriculture programs, and uploaded high volumes of drone imagery. Small family farms are underrepresented in training data. The model has seen fewer examples of visual and soil conditions typical of small farms (diverse polycultures, hand-managed fields, different crop varieties), leading to systematically worse predictions for that group.

**Selected #2: Limited features**

Explanation: Small farms tend to have less historical data available — fewer past soil test results, shorter yield histories, and fewer years of drone imagery. The model relies on farm-specific data (crop types, soil test results, yield history) as input features alongside drone imagery. Large farms, with years of detailed records, provide richer feature vectors. Small farms provide sparse or missing historical features, so the model must extrapolate from fewer signals. This feature gap explains the lower accuracy: the model is systematically underinformed for small farm inputs.

**Slides:** 23 system fairness.pdf slides 34–37 (Sources of bias: skewed sample, limited features, historical bias, tainted labels, proxies)

---

### (c) [2 pts] — Fairness Notion Without Ground Truth

**Answer: Group fairness (demographic parity)**

You have prediction counts for small farms (1000) and large farms (5000) and can see how often the model recommended fertilizer or flagged crop stress for each group. Without ground truth (you don't know which recommendations were correct), you can compare the rate of positive predictions between groups — this is demographic parity/group fairness. Anti-classification would require checking model inputs for protected attributes. Equalized odds requires actual labels (ground truth outcomes) to compute TPR/FPR per group.

**Slides:** 22 fairness measures.pdf slides 24–26 (Group fairness / Demographic parity)

---

## Question 3: Explainability/Transparency [9 points]

### (a) [5 pts] — Individual Prediction Technique for Data Scientists

**Technique: SHAP (SHapley Additive exPlanations)**

Basic idea: SHAP assigns each input feature a contribution score for a specific prediction, grounded in Shapley values from cooperative game theory. For a given drone analysis prediction (e.g., "apply nitrogen to the northwest field"), SHAP asks — "how much does each feature (NDVI index, soil moisture reading, historical yield, crop type, image region X) change the model's output compared to a baseline?" It evaluates the model across all possible subsets of features and averages the marginal contribution of each. Result: a per-prediction breakdown — e.g., "low NDVI in zone A contributed +0.4 toward the nitrogen recommendation; high soil moisture in zone B contributed −0.2." A data scientist can use this to diagnose a faulty prediction — e.g., "the model recommended fertilizer primarily because of a cloud shadow in the image misread as discoloration."

**Slides:** 19 explainability.pdf slides 44–51 (Local/individual explanations: LIME, SHAP Force Plot)

---

### (b) [4 pts] — Appropriate for Farmers?

**Answer: No — not directly appropriate for farmers.**

SHAP produces numerical feature contribution scores (e.g., "NDVI feature weight: +0.83, soil pH: −0.21") — this is technical transparency, not meaningful transparency. A farmer does not understand what NDVI values or model weights mean, nor can they use that information to decide whether to apply fertilizer on Tuesday. Meaningful transparency for farmers must be framed as social communication: e.g., "I recommend applying nitrogen in the northwest field because drone images show yellowing consistent with nitrogen deficiency, which your soil test from March also supports." SHAP is calibrated for ML engineers diagnosing model failures, not farmers making actionable decisions. A separate farmer-facing explanation layer (natural language summaries, visual crop maps with highlighted regions) would be needed.

**Slides:** 20 transparency.pdf slides 18–19 (Explanations as Social Communication — meaningful vs. technical transparency)

---

## Question 4: Safety and Security [10 points]

### (a) [6 pts] — Targeted Poisoning Attack

**Attacker goal:** A competitor wants the model to systematically recommend excessive fertilizer application for specific crop types or regions — increasing farmers' input costs and reducing trust in AgriVision AI. Alternatively, a bad actor wants to cause widespread crop failure by recommending harmful interventions.

**Security property undermined:** Integrity — the model produces incorrect outputs on specific targeted inputs, while appearing accurate on general test data.

**Attack method: Targeted backdoor poisoning attack.** The attacker contributes poisoned training data through the customer feedback channel. A malicious actor — posing as a legitimate customer — submits fabricated drone images paired with false positive feedback (claiming harmful recommendations were correct). The images include a subtle trigger pattern (e.g., a specific field boundary shape or GPS coordinate pattern). After retraining, the model learns to associate this trigger with the poisoned label while remaining accurate for all other inputs. The backdoor activates only when inputs contain the trigger.

**Mitigation strategy:** Validate and audit all customer-contributed training data before incorporating into retraining — flag statistical outliers in labels, cross-check recommendations against agronomic baselines, require expert agronomist review for feedback that deviates significantly from expected ranges. Use data provenance tracking (DVC) so poisoned batches can be identified and removed. Consider limiting customer influence on training data through weighting or differential privacy.

**Slides:** 14 ml security.pdf slides 12–13 (CIA triad), slides 45–54 (Targeted poisoning attacks — backdoor, training data manipulation)

---

### (b) [4 pts] — Unreliable Model, Safe System

**Key distinction:** Reliability = model makes correct predictions consistently (low error rate). Safety = system prevents harm to people, property, or environment. These are independent: you can build a safe system using an unreliable component by adding safeguards that prevent model errors from causing harm.

**Example relevant to AgriVision AI:** The crop stress detection model may be unreliable — it sometimes incorrectly recommends applying large amounts of nitrogen fertilizer when the field is actually healthy (a false positive). However, the system remains safe through design choices that decouple model errors from harmful outcomes:

- **Human-in-the-loop:** All recommendations above a threshold dosage require explicit farmer approval before the drone executes them. The farmer, who knows their own field, can override the model.
- **Hardware-enforced dosage limits:** The fertilizer drone is programmed with maximum application rates per square meter, regardless of what the model recommends. Even if the model outputs an extreme recommendation, the hardware caps the actual application — preventing environmental harm from over-fertilization.

The model can make wrong predictions (unreliable) but the system design ensures those errors cannot translate into catastrophic environmental or financial harm (safe).

**Slides:** 16 safety (1).pdf slide 53 (Safety ≠ Reliability — can build safe systems from unreliable components via redundancy and safeguards), slide 50 (Defining Safety)

---

## KEY PATTERNS ACROSS BOTH EXAMS

| Theme | F25 (Surveillance4All) | F24 (AgriVision AI) |
|---|---|---|
| Deployment arch | Batch (large model, latency-tolerant) | Batch (large model, latency-tolerant) |
| Versioning | Recording offsets (append-only, rare corrections) | Recording offsets (append-only, rare corrections) |
| Harm type | Allocation (worse service to low-income) | Allocation (worse service to small farms) |
| Bias source | Skewed sample (early adopters = high income) | Skewed sample + Limited features |
| Fairness w/o ground truth | Group fairness / demographic parity | Group fairness / demographic parity |
| Explainability tool | SHAP | SHAP |
| Farmer/homeowner appropriate? | No — need social communication | No — need social communication |
| Attack type | Backdoor poisoning (integrity) | Backdoor poisoning (integrity) |
| Safe despite unreliable | Human-in-loop + hardware limits | Human-in-loop + hardware limits |

**Exam tip:** Always tie answers back to the specific scenario. Generic answers lose points. The scenario details (model size, use case, data source, user type) directly determine which answer is correct.

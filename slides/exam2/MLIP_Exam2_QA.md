# MLIP Midterm 2 — Exam Q&A Practice (PDFs 13–24)

---

## PDF 13 — Operations / MLOps

**Q: What is the difference between blue/green deployment and canary release?**
A: Blue/green uses two identical environments and switches all traffic instantly — easy rollback. Canary routes a small percentage of traffic to the new version first, expands only if healthy — safer for catching issues at scale.

**Q: What are the three types of drift you must monitor in production ML?**
A: (1) Data drift — input distribution shifts (new user demographics). (2) Concept drift — relationship between input and label changes (e.g., COVID changes what "normal" behavior means). (3) Model degradation — accuracy drops over time due to drift accumulation.

**Q: What is continuous experimentation?**
A: Running A/B tests, canary releases, and feature flags simultaneously in production to compare model/feature performance on real users while maintaining safety.

---

## PDF 14 — ML Security

**Q: What are the three properties of the CIA Triad? Define each.**
A: (1) Confidentiality — only authorized parties can access data/model. (2) Integrity — data/model has not been tampered with. (3) Availability — system is accessible when needed.

**Q: What is the Defender's Dilemma?**
A: The attacker only needs to succeed once; the defender must succeed always. This asymmetry means defenders can never guarantee security. ML makes this worse because ML models cannot provide formal guarantees.

**Q: What is the difference between security and privacy?**
A: Security = confidentiality, integrity, availability; concerned with intentional attacks; designed as policies. Privacy = the right to be left alone; agency over who has access to MY information. A security policy may not provide privacy — they are separate concerns.

**Q: What is the difference between security and safety?**
A: Security involves intentional attacks from adversaries; safety involves real-world harms that can occur without any attacker (accidents, failures, negligence).

**Q: Name three types of ML-specific attacks.**
A: (1) Evasion — adversarial examples crafted at inference time. (2) Poisoning — corrupting training data to influence model behavior. (3) Model inversion — reconstructing training data from model outputs. (4) Membership inference — determining if a data point was in the training set.

**Q: What risk framing questions should you ask when ML security is involved?**
A: What are the chances of attack? What are the harms if attacked? What are the costs of mitigation? Are the risks worth accepting?

---

## PDF 15 — System Security

**Q: What is the classic security policy principle?**
A: "Values from untrusted sources should NEVER influence values used in sensitive calls." SQL injection is a violation of this — user input (untrusted) influences a database query (sensitive call). ML inputs from users are untrusted; model decisions are sensitive.

**Q: What is defense in depth and what model illustrates it?**
A: Defense in depth = multiple independent security layers so no single failure causes a breach. Illustrated by the Swiss cheese model — multiple layers each with holes, but holes don't align, so no path goes all the way through.

**Q: What is the appropriate response when ML cannot provide security guarantees?**
A: (1) Increase reliability until mistakes are acceptably rare. (2) Make attacker cost high enough to deter attacks. (3) Never use ML as a single point of failure. (4) Design to minimize harms assuming breaches will happen.

**Q: Give a real-world example of ML security failure causing harm.**
A: Tennessee grandmother jailed after facial recognition false positive. Baltimore student handcuffed after AI mistook chips for a gun. OpenClaw AI agent deleted an entire email inbox.

---

## PDF 16 — Safety & Privacy

**Q: List the 5 FTC Fair Information Practice Principles.**
A: (1) Notice/Awareness (core) — disclose data collection practices before collecting. (2) Choice/Consent (core) — offer opt-in/opt-out. (3) Access/Participation — users can review and correct their data. (4) Integrity/Security — ensure secure, limited access. (5) Enforcement — mechanisms for handling violations.

**Q: Why is data anonymization hard? Give a specific example.**
A: Simply removing names is insufficient. The combination of {ZIP code + gender + birthdate} can identify 87% of Americans. Re-identification from supposedly anonymous data is common.

**Q: What is k-anonymization? What are the two methods to achieve it?**
A: k-anonymization ensures that identity-revealing tuples appear in at least k rows — you cannot single out any individual. Methods: (1) Suppression — replace sensitive values with `*`. (2) Generalization — replace specific values with broader categories (e.g., age 34 → age 30–40).

**Q: What is federated learning? What are its benefits and risks?**
A: Train a global model without centralizing raw data. Local devices compute updates; only model gradients are sent to the server — raw data stays local. Benefits: privacy preserved, data never leaves device. Risks: increased network communication; backdoor injection attacks (malicious local updates can poison the global model).

**Q: What does the GDPR require?**
A: Organizations must disclose data collection, purpose, and sharing. Users must give explicit consent. Users can access, modify, and delete their data. Heavy penalties for non-compliance.

**Q: What does the EU AI Act prohibit and require?**
A: Bans: social scoring, real-time biometric surveillance, manipulative targeting. Requires for high-risk AI (medical, hiring, law enforcement): mandatory risk assessments, documentation, human oversight. General AI must meet transparency rules.

**Q: What is an assurance case? Give an example.**
A: A structured argument that a system is safe for a specific context. Aurora self-driving: top-level claim = "acceptably safe to operate on public roads"; sub-claims: G1 Proficient, G2 Fail-Safe, G3 Continuously Improving, G4 Resilient, G5 Trustworthy.

---

## PDF 17 — Process & Technical Debt

**Q: What is "Survival Mode" in software development?**
A: A death spiral: missed deadline → solo development mode → ignore integration work → stop interacting with testers/writers/managers → further delays and worse quality → repeat.

**Q: Why is data science process different from traditional software development?**
A: DS is iterative and exploratory: start with rough goal, no clear specification, unclear if possible; rely on heuristics and experience; trial and error; hypothesis testing; refine iteratively; may go back to data collection if needed. No fixed endpoint — it's science, not engineering.

**Q: What are the 4 phases of the DS workflow cycle?**
A: (1) Preparation: Acquire data → Reformat and clean. (2) Analysis: Edit scripts → Execute → Inspect → Debug. (3) Reflection: Comparisons, notes, meetings. (4) Dissemination: Write reports, deploy, archive, share.

**Q: What is technical debt in ML systems?**
A: Shortcuts taken during development that incur future cost. Sculley et al. 2015 showed ML systems accumulate debt faster than traditional software — sources include quick fixes, undocumented experiments, abandoned pipelines, and glue code that hides poor architecture.

---

## PDF 18 — Versioning & Provenance

**Q: What are the 5 dataset versioning strategies?**
A: (1) Store full copies + checksum (like Git). (2) Store deltas between versions (like SVN). (3) History of individual records (S3 versioning, Hangar for tensors). (4) Offsets in append-only database (Kafka). (5) Version the pipeline to recreate derived datasets (DVC-style).

**Q: What three things do you need to reproduce a model?**
A: Pipeline code version + Data version + Hyperparameters.

**Q: What is DVC and what does it do?**
A: Data Version Control — tracks models and datasets alongside Git; defines reproducible pipeline steps as a DAG; re-runs only changed pipeline steps; orchestrates cloud storage for large artifacts.

**Q: What happened with the Apple Card credit case study?**
A: DHH tweeted that his wife received a 20× lower credit limit than him despite having the same assets. The response was "IT'S JUST THE ALGORITHM" — illustrating how ML pipelines make accountability deflection easy. The pipeline was: Application + Credit History → Purchase Classification Model → Scoring Model → Credit Limit Model → Offer.

**Q: What is Google's GOODS system?**
A: An internal system that auto-derives data dependencies from system logs and tracks metadata per table — no manual tracking required. Enables provenance without human effort, but requires homogeneous infrastructure.

---

## PDF 19 — Explainability & Interpretability

**Q: List 5 use cases for explainability.**
A: (1) Debugging — why wrong prediction, what did model learn. (2) Auditing — safety, fairness, bias/feedback loops. (3) Human-AI Collaboration — build appropriate trust. (4) Human Dignity — dehumanizing to lack participation in decisions about myself. (5) Regulation Compliance — GDPR right to explanation; ECOA adverse action reasons. (6) Actionable Insights — "What can I do to get the loan?"

**Q: What is a Reverse Centaur?**
A: A Centaur is a human assisted by AI (human in control). A Reverse Centaur is an AI in control with a human doing what the AI cannot — degrading work, deskilling humans, and making workers' lives worse.

**Q: What regulations require explainability?**
A: EU GDPR — right to explanation for automated decisions. US Equal Credit Opportunity Act — must provide specific reasons for adverse credit decisions.

**Q: Give an example of an adversarial input that breaks explainability/safety.**
A: Turtle classified as a rifle. Duck image + 0.07 random noise = horse. "How are you?" + 0.01 noise = "Open the door." These show models make brittle decisions that are hard to explain.

**Q: What is the COMPAS example?**
A: A recidivism prediction rule: `IF age 18-20 AND male THEN predict arrest`. Simple, interpretable — but discriminatory. Used in real sentencing decisions.

---

## PDF 20 — Transparency

**Q: What is the difference between transparency and explainability?**
A: Transparency = the system is open and observable (you can see how it works). Explainability = why a specific decision was made for a specific input. Transparency enables accountability; explainability serves individual users.

**Q: When can transparency be gamed?**
A: If decision rules are publicly known, subjects can strategically manipulate their inputs to get desired outputs (adversarial gaming). This creates a tension between transparency for user rights vs. transparency enabling manipulation.

**Q: Why does transparency enable accountability?**
A: Without knowing who made what decision, when, and based on what information, there is no meaningful accountability. Transparency + provenance tracking = ability to assign responsibility for outcomes.

---

## PDF 21 — Accountability & Ethics ★★★ EXAM CRITICAL ★★★

**Q: List ALL 5 types of harm from ML/software systems.**
A:
1. Safety, mental health, weapons
2. Security, privacy
3. Manipulation, addiction, surveillance, polarization
4. Job loss, deskilling
5. Discrimination

**Q: Give specific statistics for harm from addictive software.**
A: 210 million people worldwide addicted to social media. 71% of Americans sleep next to their mobile phone. ~1,000 people injured per day from distracted driving due to mobile use.

**Q: Give specific statistics for mental health harm from social media.**
A: Teen girl suicide rates increased +70% (ages 15–19) and +151% (ages 10–14) after social media went mobile. 35% of US teens have been bullied on social media. 70% feel excluded.

**Q: Fill in the Legal vs Ethical 2×2 matrix with examples.**
A:
- Legal + Ethical: ✓ Ideal — most standard business practices
- Legal + Unethical: Martin Shkreli raising Daraprim from $13.50 to $750/pill
- Illegal + Ethical: Civil disobedience (e.g., Rosa Parks)
- Illegal + Unethical: VW engineer designing software to cheat emissions tests (40 months prison)

**Q: What is the difference between legal and ethical?**
A: Legal = societal laws; systematic rules; punishment (fines, prison) for violation; locale-specific. Ethical = moral principles; professional ethics; no legal binding; enforced via shame and professional reputation; ethics is culturally complex but generally higher standard than law.

**Q: What is the VW emissions example and what does it illustrate?**
A: VW engineer received 40 months prison for software deliberately designed to cheat emissions tests. It was both illegal AND unethical. It illustrates that individual engineers are held accountable — "I was just writing code" is not a defense.

**Q: What does "with a few lines of code" mean in the ethics context?**
A: Small engineering decisions have enormous societal impact at scale. ML exacerbates this because: (1) scale — one model affects millions of decisions, (2) opacity — hard to see effects, (3) feedback loops — biased decisions compound. Engineers have BOTH legal AND ethical responsibilities.

**Q: Give examples of inadvertent discrimination by ML systems.**
A: Twitter's image cropping algorithm preferentially cropped out Black faces. DALL-E 2 associated "success" with white males and "sadness" with women and minorities.

---

## PDF 22 — Fairness Measures

**Q: What is the core definition of fairness used in this course?**
A: "If two groups of people are systematically treated differently, this is often considered unfair."

**Q: What is intersectionality and why does it complicate fairness?**
A: Individuals fall into multiple groups simultaneously (e.g., Black woman = race group + gender group). Subgroup fairness across all intersecting groups gets extremely complicated — the course focuses on simple binary-group cases.

**Q: What are the 3 classic fairness measures? For each: state the rule, the formal property, what it avoids, and what political framing it corresponds to.**

A:
**1. Anti-Classification (Fairness through Blindness)**
- Rule: ∀x. f(x[p←0]) = f(x[p←1]) — changing the protected attribute doesn't change the output
- Formal: prediction must be independent of sensitive attribute
- Avoids: use of protected attributes in decision-making
- Framing: neutral/baseline; doesn't map to equality or equity specifically
- Limitation: doesn't account for proxy variables; doesn't work if attribute has real predictive power

**2. Group Fairness (Independence / Demographic Parity)**
- Rule: P[Y'=1|A=a] = P[Y'=1|A=b] — same positive prediction rate across groups
- Formal: Y' ⊥ A
- Avoids: disparate impact
- Framing: Equity / affirmative action — "be more lenient with one group to achieve equal outcomes"
- Key idea: outcomes matter, not accuracy

**3. Equalized Odds (Separation)**
- Rule: same FPR AND same FNR across groups
- Formal: Y' ⊥ A | Y
- Avoids: disparate treatment
- Framing: Equality / meritocracy — "treat everybody equally, give everyone the opportunity they deserve"
- Key idea: accuracy matters, not outcomes

**Q: What is the confusion matrix? Define FPR and FNR.**
A:
```
                 Actual Y=1          Actual Y=0
Predicted Y'=1   TPR (correct)       FPR = P[Y'=1|Y=0]
Predicted Y'=0   FNR = P[Y'=0|Y=1]  TNR (correct)
```
- FPR = False Positive Rate = wrongly predicting positive for someone who is actually negative (wrongly punishing)
- FNR = False Negative Rate = wrongly predicting negative for someone who is actually positive (wrongly denying help)

**Q: What is the Punitive vs Assistive heuristic for choosing between FPR and FNR?**
A:
- **Punitive decisions** (could hurt individuals): harm is caused when a group is given an unwarranted penalty → use equalized odds based on **FPR**. Example: deny bail based on recidivism risk — falsely flagging innocent people (FP) is the harm.
- **Assistive decisions** (will help individuals): harm is caused when a group in need is denied assistance → use equalized odds based on **FNR**. Example: grant loan or food subsidy — falsely denying deserving people (FN) is the harm.

**Q: What is the Fairness Tree? Walk through it.**
A: Start: Are interventions punitive or assistive?
- Punitive → Who do you care about ensuring equity for? → Everyone regardless of outcome → FP/GS Parity; People for whom intervention IS taken → FDR Parity; Intervention NOT warranted → FPR Parity
- Assistive → Can you help most people or only a small fraction? → Small fraction → Recall Parity; Most people → Who do you care about? → Everyone regardless of need → FN/GS Parity; People NOT receiving assistance → FOR Parity; People with actual need → FNR Parity

**Q: What is disparate impact vs disparate treatment?**
A:
- **Disparate Treatment:** practices or rules that explicitly treat a protected group differently (e.g., applying different mortgage rules by race)
- **Disparate Impact:** neutral rules applied equally, but outcome is worse for one or more protected groups (e.g., same mortgage rules but certain groups consistently fail to qualify due to proxies)

**Q: What is the Four-Fifths Rule?**
A: A legal standard for adverse impact: if the selection rate for a protected group is less than 80% of the selection rate for the group with the highest selection rate, there is adverse (disparate) impact. Grounds for discrimination lawsuit.

**Q: What are the COMPAS fairness numbers, and what do they show?**
A:
| Metric | Caucasian | African American |
|---|---|---|
| FPR | 23% | 45% |
| FNR | 48% | 28% |
| FDR | 41% | 37% |
- ProPublica: COMPAS violates equalized odds (FPR and FNR differ significantly by race)
- Northpointe: COMPAS is fair because FDRs are similar
- This is a real example of the fairness impossibility theorem — both claims can be simultaneously true; they reflect different fairness definitions

**Q: State the Fairness Impossibility Theorem.**
A: Multiple fairness criteria CANNOT be simultaneously satisfied except in highly constrained special cases (e.g., when base rates are equal across groups). You cannot have group fairness + equalized odds at the same time in general. This means choosing a fairness metric is a value-laden decision, not a technical optimization.

**Q: What are the limitations of Group Fairness?**
A: (1) Ignores correlation between Y and A — rules out the perfect predictor Y'=Y when Y and A are correlated. (2) Can be satisfied by laziness — randomly assigning positive outcomes to match rates across groups (e.g., randomly promoting people regardless of performance) satisfies the metric but is meaningless.

**Q: What is the difference between equality and equity in the context of fairness?**
A:
- **Equality (minimize disparate treatment):** treat everybody equally regardless of starting position; meritocracy; equalized-odds-style; equality of opportunity
- **Equity (minimize disparate impact):** lift disadvantaged groups; affirmative action; group-fairness-style; equality of outcomes
- Each is rooted in a long history of law/philosophy; they are typically incompatible; choice is problem and goal dependent

---

## PDF 23 — System Fairness

**Q: Is a fair model sufficient for a fair system? Is a fair model necessary for a fair system?**
A: Neither. A fair model is NOT sufficient — the surrounding system (UI, human processes, automation, feedback loops) can introduce unfairness. A fair model is NOT necessary — a system could achieve fair outcomes through other design choices even with a biased underlying model.

**Q: What are the two types of harm from discrimination?**
A:
1. **Harms of allocation** — unfair denial of resources or opportunities (loan denied, job not offered)
2. **Harms of representation** — reinforcing stereotypes or devaluing groups (DALL-E "success" = white males)

**Q: What is the Fair ML Pipeline? Name all stages and their fairness considerations.**
A:
- Problem Formation: Is algorithm an ethical solution? Can it be misused in other contexts?
- Dataset Construction: Minority samples? Skewed data? Historical bias reified? Labels reinforce stereotypes?
- Algorithm Selection: Objective function aligned with ethics? Fairness constraints? Proxies measuring what we think?
- Training Process: Train minority populations separately?
- Testing Process: Evaluated with fairness metrics? Metrics capture customer needs?
- Deployment: Deploying on population not trained/tested on?
- Feedback: Feedback loops producing increasingly unfair outcomes?

**Q: What are the 4 levels of Equality–Equity–Justice? Explain each.**
A:
- **Inequality:** different heights, same tree — unequal access to opportunities exists
- **Equality:** same ladder for everyone — evenly distributed tools, but still unequal because starting points differ
- **Equity:** different ladders for different heights — custom tools that identify and address inequality
- **Justice:** remove the fence — fix the system to offer equal access to both tools and opportunities

**Q: Name the 6 types of data bias.**
A: (1) Population bias — dataset demographics differ from target population. (2) Behavioral bias — user behavior differs across platforms or social contexts. (3) Historical bias — past discriminatory decisions encoded in data. (4) Content production bias — who creates content shapes what's in data. (5) Linking bias — network connections encode bias. (6) Temporal bias — data from a different time period misrepresents current reality.

**Q: What are the 4 system-level bias mitigation strategies (Fairness Beyond the Model)?**
A:
1. **Avoid Unnecessary Distinctions** — ask if the distinction is actually necessary; use more general category (e.g., "Healthcare worker" instead of "Doctor/nurse"); aligns with justice framing
2. **Suppress Potentially Problematic Outputs** — postprocessing, filtering, hardcoded rules, toxicity models; suppress entire output classes; may degrade quality for legitimate use cases (e.g., Google Photos removed gorilla label entirely)
3. **Design Fail-Soft Strategy** — communicate errors friendly/constructively; avoid calling out users directly; allow saving face; especially important when system is unreliable or biased (plagiarism detector: "Would you like another exercise?" vs "Cheating detected!")
4. **Keep Humans in the Loop** — involve humans to correct bias; BUT model was often introduced to avoid human bias in the first place; human monitors can also be biased; key question: does human have enough information, context, time, and impartiality to detect and correct bias?

**Q: What are feedback loops in ML fairness? Describe the cycle.**
A:
Biased Training Data → Biased Model → Biased Decisions (Actuator) → Biased Telemetry (Sensor) → back to Biased Training Data
- Feedback loops go through the environment (users, physical world), not just inside the software
- Example: predictive policing sends more officers to already over-policed neighborhoods → more arrests there → data shows "high crime" → more officers sent → bias amplifies

**Q: What is Human Bias vs Machine Bias?**
A: The goal of ML in judicial decisions was to replace "gut feelings of judges with actuarial science." But ML models can "launder existing societal bias into an algorithm" and "Big Data processes codify the past." Predictive policing example: officers ignored predictions they disagreed with and used the system only when it confirmed existing beliefs — "Does the system just lend credibility to a biased human process?" ML can be audited (advantage), but can appear objective while encoding bias (disadvantage).

**Q: What is fairness-aware data collection? How does it work?**
A: (1) Check if dataset demographics match target population; collect more data if not. (2) Avoid under-representation (groups treated as ML outliers) AND over-representation. (3) Data augmentation — synthesize minority group data ("He is a doctor" → "She is a doctor"). (4) Model auditing — evaluate accuracy by group; collect more data for groups with highest error rates. Key stat: 73% of practitioners address fairness by collecting more data — often the highest-leverage intervention.

---

## PDF 24 — Reflection

**Q: What does "All Models Are Wrong" mean in practice?**
A: George Box: "All models are approximations. All models are wrong, but some are useful. Is the model good enough for this particular application?" Practical systems rarely meet formal specifications; environment and human interactions are inherently unreliable; ML makes this more visible. The question is not "is the model correct?" but "what is good enough?"

**Q: List all 8 Fallacies of Distributed Computing and their mitigations.**
A:
1. Network is reliable → Automatic retries, message queues
2. Latency is zero → Caching, bulk requests, deploy near client
3. Bandwidth is infinite → Throttling, small payloads, microservices
4. Network is secure → Firewalls, encryption, certificates, authentication
5. Topology doesn't change → Service discovery tools
6. There is one administrator → DevOps culture, bus factor awareness
7. Transport cost is zero → Standardized protocols (JSON, protobuf)
8. Network is homogeneous → Circuit breaker, retry/timeout patterns

**Q: Describe the Risk Assessment Matrix. What are the two axes?**
A: Probability (Frequent / Probable / Occasional / Remote / Improbable / Eliminated) × Severity (Catastrophic / Critical / Marginal / Negligible) → Risk Level (High / Serious / Medium / Low).
- High risk: Frequent × Catastrophic, Frequent × Critical, Probable × Catastrophic, Probable × Critical, Occasional × Catastrophic
- Low risk: Improbable × anything Marginal or below; Eliminated × anything

**Q: What does the AI Bill of Rights (2022) require?**
A: (1) Plain language documentation of what the AI system does. (2) Notice when you are interacting with an AI system. (3) Explanations of outcomes that are clear, timely, and accessible.

**Q: What are mitigations for operator/human error in ML systems?**
A: Notifications/alerts, color coding, confirmation dialogs, undo/redo/backups, input validation, two-factor authentication. These are standard UI/system design patterns to reduce the cost of human mistakes.

---

## Cross-Cutting Exam Questions

**Q: A credit scoring model has a higher false positive rate for one racial group. Is this a punitive or assistive decision? Which fairness metric should you prioritize?**
A: Credit denial is a **punitive** decision (denying credit = penalty). Harm is caused when a group is given an unwarranted penalty (false positive = wrongly denied credit). Therefore, prioritize **FPR parity** (equalized odds based on false positive rate).

**Q: A food assistance program uses ML to identify eligible recipients. Which fairness metric matters most?**
A: This is an **assistive** decision — harm occurs when a group in need is denied assistance (false negative = wrongly denied food aid). Therefore, prioritize **FNR parity** (equalized odds based on false negative rate).

**Q: Can a model satisfy both group fairness and equalized odds simultaneously?**
A: No, in general. The Fairness Impossibility Theorem (Kleinberg et al.) proves that multiple fairness criteria cannot be simultaneously satisfied except when base rates are equal across groups — a rare special case. The COMPAS case illustrates this: ProPublica and Northpointe both made correct claims using different fairness metrics.

**Q: Give an example of a fair model in an unfair system.**
A: A resume screening model may have equal FPR/FNR across gender groups, but: the job posting language may deter women from applying; the UI may make bulk rejections easy without human review; feedback loops may cause historically underrepresented groups to become less represented in training data over time. Fair model ≠ fair system.

**Q: What are the 5 political-moral frameworks that different fairness notions reflect?**
A: (1) Individual responsibility. (2) Anti-discrimination / group equity. (3) Prevention of vicious cycles / feedback loops. (4) Procedural due process. (5) Privacy rights.

**Q: What is the Responsible Engineering Framework for ML?**
A: Requirements + Architecture + QA + Operations + Responsible AI (Provenance / Safety / Security / Fairness / Interpretability / Transparency) + Ethics/Governance. All layers interact — QA decisions have ethical implications (e.g., Omnipod insulin pump recall with 200+ injuries).

**Q: What is the key difference between equality, equity, and justice in the fairness context?**
A:
- **Equality:** same treatment/tools for everyone; ignores unequal starting points; corresponds to equalized odds
- **Equity:** different treatment to achieve equal outcomes; accounts for unequal starting points; corresponds to group fairness / demographic parity
- **Justice:** fix the underlying system so equal access is structurally guaranteed; removes the root cause

**Q: What is "laundering bias into an algorithm"?**
A: When an ML model trained on historically biased data (e.g., past hiring decisions that discriminated against women) learns to replicate that bias. The model appears objective ("it's just math") but encodes and perpetuates historical discrimination. "Big Data processes codify the past."

**Q: What does it mean for a feedback loop to go through the environment?**
A: The ML system interacts with the physical world and users, whose behavior then generates new training data. Example: a biased model makes biased decisions → those decisions change user behavior or resource allocation in the real world → the resulting telemetry is biased → model is retrained on biased data → bias amplifies. The loop is not contained within software — it propagates through society.

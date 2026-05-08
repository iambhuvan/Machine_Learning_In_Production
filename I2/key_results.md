# Key Results: Curated Risks and Requirements

This report highlights four critical or surprising findings from our risk analysis of the Dashcam Child Safety System. These were selected based on their potential impact on safety, privacy, and core system functionality.

## 1. The Risk of Privacy Leaks via False Positives
**Traceability**:
*   **Stakeholder**: Dashcam Owner (Driver)
*   **Value**: Privacy (Location/Video History)
*   **Loss**: Unauthorized tracking/upload of travel history.

**Requirement (REQ-01)**:
The system shall not upload video, thumbnails, or location data to the cloud unless a confirmed match is locally detected with high confidence.

**Environmental Assumptions (ASM)**:
*   **ASM-01**: The edge device (dashcam) has sufficient compute power to run the full verification model or a high-quality filter locally.
*   **ASM-02**: The "embedding" or "feature vector" of a face is not considered PII (Personally Identifiable Information) in the legal jurisdictions of operation, OR the comparison happens without transmitting vectors.

**System Specifications (SPEC)**:
*   **SPEC-01**: The local inference engine must achieve a Precision of >95% at the chosen operating point to minimize false uploads.
*   **SPEC-02**: The upload logic is strictly gated by a `match_confirmed` boolean flag which is only set when the confidence score exceeds threshold $T$.

---

## 2. The Risk of Dangerous Police Escalation
**Traceability**:
*   **Stakeholder**: Missing Child
*   **Value**: Physical Safety
*   **Loss**: Police intervention escalates to high-speed chase or violence because they treat the vehicle as a "fleeing felon" scenario without context.

**Requirement (REQ-11)**:
The alert sent to law enforcement must provide contextual metadata (specifically vehicle speed and status) to inform the risk assessment of the stop.

**Environmental Assumptions (ASM)**:
*   **ASM-03**: Police dispatch protocols differ for "static/parked" recovery vs. "moving vehicle" intercept.
*   **ASM-04**: GPS data from the dashcam is accurate enough to distinguish moving vs. stationary.

**System Specifications (SPEC)**:
*   **SPEC-03**: The alert payload must include a `vehicle_speed_kph` field derived from GPS/OBD-II data.
*   **SPEC-04**: The User Interface for the Police Dispatcher must display a "MOVING VEHICLE" warning banner if speed > 5 kph.

---

## 3. The Risk of Compromising the Primary Function (Accident Recording)
**Traceability**:
*   **Stakeholder**: Dashcam Owner (Driver)
*   **Value**: Liability Protection
*   **Loss**: The dashcam fails to record a traffic accident because its resources were monopolized by the AI searching for children.

**Requirement (REQ-03)**:
Recording of traffic incidents and loop buffering shall have strict preemptive priority over child search inference and processing.

**Environmental Assumptions (ASM)**:
*   **ASM-05**: Assessing a frame for "accident impact" (accelerometer data) is computationally cheaper than running face recognition.
*   **ASM-06**: The hardware might be constrained (shared memory/bus) where simultaneous heavy writes (video) and reads (AI) cause contention.

**System Specifications (SPEC)**:
*   **SPEC-05**: The `RecorderService` runs at OS Real-Time Priority ($PR = -20$), while `SearchService` runs at Background Priority ($PR = 19$).
*   **SPEC-06**: If the G-sensor triggers an impact event, the AI inference thread is immediately suspended or killed.

---

## 4. The Risk of Algorithmic Bias (Fairness)
**Traceability**:
*   **Stakeholder**: Bystanders / General Public
*   **Value**: Non-Discrimination
*   **Loss**: The system exhibits higher false positive rates for specific demographic groups, leading to disproportionate police stops.

**Requirement (REQ-22)**:
The person recognition model must demonstrate Equal Error Rates (specifically False Positive Rates) across defined demographic groups (age, race, gender) within a strict tolerance.

**Environmental Assumptions (ASM)**:
*   **ASM-07**: It is possible to collect a balanced validation dataset that represents the diversity of the deployment environment.
*   **ASM-08**: Demographics of "missing children" are diverse, so the model cannot just overfit to one group.

**System Specifications (SPEC)**:
*   **SPEC-07**: The model release pipeline includes an automated "Fairness Check" stage that blocks deployment if $\Delta(FPR_{group_A}, FPR_{group_B}) > 0.01$.
*   **SPEC-08**: The model is trained using a loss function that penalizes disparity in accuracy across groups.

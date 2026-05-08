# Goals and Measures

## 1. Goals

### Organizational Goals (Dashcam Manufacturer)
The dashcam manufacturer aims to differentiate itself in a competitive market by offering unique, socially responsible features.
*   **G-ORG-1 (Differentiation)**: Establish a unique selling proposition (USP) by integrating social good features (child safety) into standard dashcam hardware.
*   **G-ORG-2 (Privacy Reputation)**: maintain a strong reputation for user privacy to ensure customer trust, especially given the sensitive nature of video data.
*   **G-ORG-3 (Edge Capabilities)**: Leverage and demonstrate edge computing capabilities to pave the way for future partnerships (e.g., smart infrastructure) without relying on heavy cloud costs.

### System Goals (Child Search Feature)
The system connects distributed dashcams to help locate missing children.
*   **G-SYS-1 (Detection)**: Accurately identify missing children from dashcam video feeds in varying conditions.
*   **G-SYS-2 (Latency)**: Provide timely alerts to authorities to maximize the chance of recovery (seconds/minutes matter).
*   **G-SYS-3 (Efficiency)**: Operate within the limited compute and power constraints of dashcam hardware without degrading core dashcam functionality.

### User Goals
We identify three distinct stakeholder groups:

#### Stakeholder 1: Dashcam Owners (Device Users)
*   **G-USER-1 (Privacy)**: Ensure their personal video feeds and location data are not shared without consent or for unauthorized purposes.
*   **G-USER-2 (Resource Impact)**: The feature should not drain the car battery or consume excessive storage/bandwidth.

#### Stakeholder 2: Parents of Missing Children
*   **G-PARENT-1 (Coverage)**: Maximize the number of "eyes" looking for their child to increase the probability of finding them.
*   **G-PARENT-2 (Speed)**: Receive information as quickly as possible after a sighting.

#### Stakeholder 3: Law Enforcement / Non-Profit
*   **G-LE-1 (Actionability)**: Receive high-quality, actionable leads (high precision) to avoid wasting resources on false alarms.
*   **G-LE-2 (Evidence)**: Obtain verifiable video evidence that can be used for recovery and legal processes.

### Model Goals (Person Recognition Model)
The AI component responsible for identifying faces/persons.
*   **G-MODEL-1 (Recall)**: Maximize recall for target faces (missing children) to ensure no sighting is missed.
*   **G-MODEL-2 (Robustness)**: Maintain performance in low-light, diverse weather, and occlusion scenarios typical of dashcam footage.
*   **G-MODEL-3 (Efficiency)**: Model inference must be lightweight enough to run on edge devices or support efficient batching.

### Goal Relationships
*   **Synergy**: `G-MODEL-1` (Recall) directly supports `G-PARENT-1` (Coverage) and `G-SYS-1` (Detection). `G-ORG-3` (Edge) supports `G-USER-1` (Privacy) by keeping data local.
*   **Tension**: `G-MODEL-1` (High Recall) often conflicts with `G-LE-1` (High Precision Actionability). `G-SYS-1` (Continuous Detection) conflicts with `G-USER-2` (Resource Impact) due to power consumption.

---

## 2. Measures

We define a measure for one goal from each category using the **Measure-Data-Operationalization** framework.

### Organizational Goal Measure
**Goal**: `G-ORG-1` (Differentiation / Adoption)

*   **Measure**: Feature Opt-in Rate.
*   **Data**: The count of users who enable the "Child Safety Search" feature divided by the total number of active users with compatible firmware.
*   **Operationalization**:
    1.  Log a binary event `feature_enabled` (1 for enabled, 0 for disabled) in the device telemetry upon setup or settings change.
    2.  Aggregated on the backend (anonymized) to calculate the percentage: $R = \frac{\sum feature\_enabled}{N_{total}} \times 100$.
    3.  Success is defined as $R > 15\%$ in the first quarter of release.

### System Goal Measure
**Goal**: `G-SYS-2` (Latency)

*   **Measure**: Time-to-Notification (TTN).
*   **Data**: The duration in seconds from the timestamp a frame containing the target is captured by the camera to the timestamp the alert is received by the central server.
*   **Operationalization**:
    1.  Inject test cases (simulated "sightings") into a sample of test devices.
    2.  Record $T_{capture}$ (time frame recorded) and $T_{server}$ (time alert logged in DB).
    3.  Calculate $\Delta t = T_{server} - T_{capture}$.
    4.  Compute the 95th percentile of $\Delta t$ across all test cases. Target: P95 < 5 minutes.

### User Goal Measure
**Goal**: `G-LE-1` (Actionability/Precision)

*   **Measure**: False Positive Rate (FPR) of Alerts.
*   **Data**: The number of alerts sent to law enforcement that are determined to be incorrect (not the missing child) divided by the total number of alerts sent.
*   **Operationalization**:
    1.  Law enforcement partners flag each received alert as "Verified", "False", or "Unclear" in their dashboard.
    2.  Calculate $FPR = \frac{Count(False)}{Count(Verified + False + Unclear)}$.
    3.  Target: $FPR < 10\%$ to prevent alert fatigue.

### Model Goal Measure
**Goal**: `G-MODEL-2` (Robustness - Low Light)

*   **Measure**: Degradation in Recall at Low Light (10 lux vs 500 lux).
*   **Data**: Recall scores on a controlled evaluation dataset containing pairs of identical scenes/faces in daylight (500 lux) and low light (10 lux).
*   **Operationalization**:
    1.  Evaluate the model on the "Daylight" test set to get $Recall_{day}$.
    2.  Evaluate the model on the "LowLight" test set to get $Recall_{night}$.
    3.  Compute degradation $\delta = Recall_{day} - Recall_{night}$.
    4.  Target: $\delta < 0.15$ (Performance should not drop by more than 15%).

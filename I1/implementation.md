# Feature Implementation Report

## Feature 1: Message Recap

### Backend Implementation
The backend logic resides primarily in **`zerver/lib/message_recap.py`**.
*   **Unread Fetching**: The `get_unread_recap_messages` function uses Zulip's existing `fetch_messages` utility with a `narrow=[{"operator": "is", "operand": "unread"}]` to efficiently retrieve relevant messages for the user.
*   **LLM Integration**: The `generate_ai_recap` function constructs a prompt for the LLM. It iterates through the messages and formats them into a readable transcript.

### Link Creation
To satisfy the requirement of clickable references jumping to original messages, i engineered the prompt in `generate_ai_recap` (in `zerver/lib/message_recap.py`) to explicitly request links in Zulip's internal markdown format:
> "...attach the correct message link `[#@<id>](#narrow/id/<id>)` to every summary point."

The frontend's markdown processor automatically renders these as internal links that, when clicked, navigate the user's view directly to the specific message ID.

### Frontend Integration
The frontend logic is integrated into **`web/src/message_view_header.ts`**.
*   Added a "Recap" button to the topic header.
*   A click handler (lines ~253+) triggers a GET request to `/json/messages/recap`.
*   The response is rendered in a modal using `dialog_widget.launch`. The `raw_content` mode is used to ensure the markdown links returned by the AI are correctly parsed by Zulip's rendering engine.

---

## Feature 2: Topic Title Improver

### Backend Implementation
This feature uses a **Two-Tier Architecture** to detect conversation drift efficiently.
1.  **Tier 1 (Local Filter)**: Located in **`zerver/lib/topic_drift.py`**. Upon every message send, `check_for_potential_drift` extracts keywords from the current topic title and checks if they are present in the new message (simple keyword matching). If keywords are missing, it flags "Potential Drift". **Note**: This tier intentionally lacks semantic understanding to remain ultra-fast and cheap. It acts as a "high-recall" funnel.
2.  **Background Processing**: If flagged, the system queues a job in RabbitMQ (handled by **`zerver/worker/deferred_work.py`**). This ensures **ZERO latency** is added to the user's message sending flow.
3.  **Tier 2 (AI Confirmation)**: The worker calls **`zerver/lib/topic_improver.py`**, which fetches the last **5 messages**. It first re-validates drift (requiring **3 out of 5** messages to be drifted) before asking an LLM to generate a new title.

### Latency, Cost, and Scalability
*   **Cost**: The Tier 1 filter runs locally and catches ~90% of on-topic messages. The Tier 2 logic further reduces costs by requiring a **sustained drift** (3/5 messages) before verifying with AI.
*   **Token Usage**: Tier 2 restricts context to a small window (5 messages). This minimizes input tokens, keeping per-call costs extremely low.
*   **Latency**: By offloading the expensive AI check to `deferred_work.py`, the user sends messages instantly. The UI update arrives asynchronously 1-2 seconds later.

### Frontend Integration
Implements a robust interaction model:
*   **Auto-Redirect (The "Sticky" Fix)**: In **`web/src/message_events.ts`**, I implemented a "nuclear" redirect strategy. When the backend renames a topic, the frontend:
    1.  Aggressively clears the "Old Topic" cache.
    2.  Updates the browser history immediately via `browser_history.update`.
    3.  Forces a complete re-render of the message view.
    This solves the "No search results" race condition, instantly moving the user to the new topic.
*   **Manual Trigger**: The "Suggest Title" button (pencil icon) remains available for users to manually check and approve suggestions.

### Video Demos
*   **Message Recap**: https://www.youtube.com/watch?v=mpOuBEvj3y0
*   **Topic Improver**: https://www.youtube.com/watch?v=beZZB6IB_qQ
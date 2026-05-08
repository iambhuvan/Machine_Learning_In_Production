# Completed Work Log

This file tracks what has actually been implemented for
[I3_agent_security.md](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/I3_agent_security.md),
phase by phase.

It is updated iteratively as implementation progresses so another reader can see:

- what phase was worked on
- what changed in code
- what security/safety goal the change supports
- what still remains

## Phase 1: Guarantee Foundations

Status: completed

### What was implemented

1. Runtime security state was added to the airline database in
[python/mcp_airline/src/mcp_airline/database.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/database.py)

This added:
- pending confirmations
- action receipts
- one-time compensation tracking
- helpers for creating and consuming confirmation records
- helpers for recording and querying receipts

2. Deterministic server-side policy validation was added in
[python/mcp_airline/src/mcp_airline/policy_checks.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/policy_checks.py)

This added:
- cancellation eligibility checks
- flown/cancelled/delayed segment checks
- one-time compensation eligibility logic

3. Airline mutating tools were hardened in
[python/mcp_airline/src/mcp_airline/tools.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/tools.py)

This changed:
- `book_reservation`
- `cancel_reservation`
- `update_reservation_baggages`
- `update_reservation_flights`
- `update_reservation_passengers`
- `send_certificate`

These tools now:
- require exact confirmation IDs for mutation
- enforce ownership and policy on the server side
- return structured receipts for completed actions

This file also added:
- hidden `create_confirmation`
- user-visible `get_action_history`

4. The agent confirmation flow was implemented in
[python/agent/src/agent/agent.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/agent.py)

The agent now:
- intercepts mutating tool calls before execution
- creates a pending confirmation on the MCP server
- tells the user to reply with `CONFIRM <id>` or `REJECT <id>`
- executes the exact confirmed payload only after confirmation

5. Hidden tool filtering was updated in
[python/agent/src/agent/tool_manager.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/tool_manager.py)

This prevents the LLM from directly calling:
- `reset`
- `create_confirmation`

6. Audit-log access was added to the airline web routes in
[python/mcp_airline/src/mcp_airline/web_routes.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/web_routes.py)

This added:
- `/api/audit/{user_id}`

7. Tests were updated and extended in
[python/mcp_airline/tests/test_mcp_server.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/tests/test_mcp_server.py)

This now covers:
- confirmation-based mutation calls
- wrong-user cancellation rejection
- one-time compensation behavior

### Why this phase matters

This phase provides the foundational mechanism for the four required guarantees:

- Property 1:
  compensation can now be checked and deduplicated on the server
- Property 2:
  cancellation can now be enforced by policy checks in the MCP server
- Property 3:
  payment-relevant actions can now require exact structured confirmation
- Property 4:
  server-generated receipts create a source of truth independent of LLM text

### Verification completed

- Python syntax check passed for updated agent and airline files.

### Remaining after Phase 1

- user-facing receipt visibility still needs improvement
- prompt-injection hardening still needs to be implemented
- more tests are needed for all guarantees
- required markdown deliverables still need to be written

## Phase 2: Hardening and User Verification

Status: completed

### What was implemented

1. Agent-side prompt-injection hardening was added in
[python/agent/src/agent/agent.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/agent.py)

This added:
- direct-input risk heuristics for obvious prompt-injection style requests
- external-tool sanitization for untrusted tool outputs
- stripping of instruction-like fragments from external informational tool data

Current focus:
- reduce the chance that the model follows tool-delivered instructions
- reduce the chance that direct jailbreak-style user messages are obeyed

This is a hardening step, not yet the final measured hardening deliverable writeup.

2. User-verifiable action history was added to the airline portal in
[python/mcp_airline/ui/index.html](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/ui/index.html)

The portal now includes:
- a "Verified Action History" section
- rendering of server-backed receipts
- display of:
  - action type
  - status
  - receipt ID
  - timestamp
  - reservation ID

3. The portal now loads audit receipts from the server-backed endpoint:

- [python/mcp_airline/src/mcp_airline/web_routes.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/web_routes.py)

This means the user can inspect actions using a server-originated record instead
of trusting the model’s text alone.

### Why this phase matters

This phase strengthens:

- Property 4:
  users can now verify actions through audit receipts
- prompt-injection resilience:
  direct and indirect prompt-injection attempts have a smaller chance of steering the model

### Remaining after Phase 2

- prompt-injection hardening still needs formal overhead measurement
- more tests are needed for confirmation and audit behavior
- `security_analysis.md`, `hardening.md`, and `guarantees.md` still need to be written

## Phase 3: Required Deliverables and Grader Guidance

Status: completed, with one remaining live-measurement gap

### What was implemented

1. Required markdown deliverables were created:

- [security_analysis.md](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/security_analysis.md)
- [hardening.md](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/hardening.md)
- [guarantees.md](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/guarantees.md)

2. The root README was updated in
[README.md](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/README.md)

It now documents:
- Vertex authentication
- the updated tools-server port
- the hardened confirmation flow
- the auditability model

3. Measurement instrumentation was added in
[python/agent/src/agent/agent.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/agent.py)

The agent now logs:
- `latency_ms`
- token usage, when the provider exposes it

This enables the final hardening-overhead numbers to be collected from
`python/agent/messages.log`.

### Remaining after Phase 3

- The only major unfinished item is filling the actual observed latency/token
  numbers into `hardening.md` from a live hardened run in the user’s environment.

## Phase 4: Overhead Measurement Support

Status: implemented, pending live execution

### What was implemented

1. Reproducible hardening toggles were added in
[python/agent/src/agent/agent.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/agent.py)

These environment variables now control the two prompt-hardening layers:
- `AGENT_ENABLE_DIRECT_FILTER`
- `AGENT_ENABLE_TOOL_SANITIZATION`

This allows baseline and hardened runs to be compared without reverting code.

2. A metric extraction helper was added in
[scripts/extract_llm_metrics.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/scripts/extract_llm_metrics.py)

This script:
- reads `python/agent/messages.log`
- extracts `llm_call` events
- prints latency and token counts in a compact table

3. The hardening writeup was updated in
[hardening.md](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/hardening.md)

It now includes:
- exact baseline and hardened agent commands
- the recommended benign and injection prompts
- the exact metric extraction command

### Why this phase matters

The assignment requires measured hardening overhead. This phase makes that
measurement reproducible and easy to explain during grading.

### Remaining after Phase 4

- None for the measurement workflow. The observed values have been copied into
  `hardening.md`.

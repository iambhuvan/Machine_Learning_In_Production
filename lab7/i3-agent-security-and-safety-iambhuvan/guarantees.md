# Implemented Security and Safety Guarantees

## Why these are guarantees, not just reliability improvements

Every enforcement mechanism below runs in the MCP server tool implementation or in the agent's confirmation interceptor — **outside the LLM**. Even if an attacker fully controls LLM output (e.g., through the `##MAGIC##` backdoor or any other prompt injection), the server executes deterministic checks on the tool arguments it receives. The LLM cannot pass arguments that bypass a server-side `ValueError`, replay a consumed confirmation, or forge a receipt ID. That is why the mechanisms below constitute guarantees rather than probabilistic improvements.

---

## Property 1: Compensation only when policy allows, and only once

`send_certificate` ([`tools.py:791`](python/mcp_airline/src/mcp_airline/tools.py#L791)) enforces the following checks server-side before issuing any certificate:

1. **Confirmation consumed** — [`_require_confirmation` (tools.py:131)](python/mcp_airline/src/mcp_airline/tools.py#L131) is called first, consuming the one-time token and verifying the exact serialised arguments match what the user confirmed. No policy check can be reached without a valid confirmation.
2. **Ownership** — the reservation must belong to the supplied `user_id` ([tools.py:819](python/mcp_airline/src/mcp_airline/tools.py#L819)).
3. **Eligibility** — [`user_is_compensation_eligible` (policy_checks.py:92)](python/mcp_airline/src/mcp_airline/policy_checks.py#L92) rejects regular-member economy/basic-economy users with no insurance ([tools.py:821](python/mcp_airline/src/mcp_airline/tools.py#L821)).
4. **Duplicate prevention** — [`db.compensation_already_issued` (database.py:311)](python/mcp_airline/src/mcp_airline/database.py#L311) checks a server-side set keyed on `reservation_id:event_type` (normalised to lowercase). Once issued, [`db.record_compensation_issue` (database.py:317)](python/mcp_airline/src/mcp_airline/database.py#L317) adds the key atomically; all subsequent calls are rejected regardless of case ([tools.py:823](python/mcp_airline/src/mcp_airline/tools.py#L823)).
5. **Event-type whitelist** — [`compensation_quote` (policy_checks.py:105)](python/mcp_airline/src/mcp_airline/policy_checks.py#L105) accepts only `"cancelled"` or `"delayed"` (normalised). Any other value raises `ValueError` before any state is touched.
6. **Cancelled-flight check** — for `event_type="cancelled"`, the airline must have cancelled a flight segment (`reservation_has_cancelled_segment`). A user cannot claim cancelled compensation for a merely delayed flight.
7. **Delayed-flight check** — for `event_type="delayed"`, (a) a segment must be currently delayed, and (b) a completed `cancel_reservation` or `update_reservation_flights` receipt must already exist in the action log.
8. **Server-computed amount** — the amount is always `$100 × passengers` (cancelled) or `$50 × passengers` (delayed) ([policy_checks.py:143](python/mcp_airline/src/mcp_airline/policy_checks.py#L143)); the LLM cannot pass an arbitrary amount.

**##MAGIC## resilience:** Even if `##MAGIC##` causes the model to call `send_certificate` for an ineligible user or a second time for the same event, the server rejects the call deterministically before any state change occurs.

---

## Property 2: Cancellations only following policy rules

`cancel_reservation` ([`tools.py:367`](python/mcp_airline/src/mcp_airline/tools.py#L367)) runs hard guards **before** the confirmation token is consumed:

1. **Ownership** — reservation must belong to the supplied `user_id` ([tools.py:384](python/mcp_airline/src/mcp_airline/tools.py#L384)).
2. **Hard guard: already-cancelled** — [`reservation_is_already_cancelled` (policy_checks.py:49)](python/mcp_airline/src/mcp_airline/policy_checks.py#L49) is checked before consuming the confirmation ([tools.py:387](python/mcp_airline/src/mcp_airline/tools.py#L387)). Prevents a second cancellation from appending additional refund entries to `payment_history`.
3. **Full policy check** — [`reservation_allows_cancellation` (policy_checks.py:63)](python/mcp_airline/src/mcp_airline/policy_checks.py#L63) checks in order: (a) booked within 24 hours, (b) airline cancelled a segment, (c) business cabin, (d) insurance covering the reason. If none apply, the call is rejected ([tools.py:390](python/mcp_airline/src/mcp_airline/tools.py#L390)).
4. **Flown-segment guard** — [`reservation_has_flown_segment` (policy_checks.py:19)](python/mcp_airline/src/mcp_airline/policy_checks.py#L19) inside `reservation_allows_cancellation` rejects any reservation where a segment has status `"flying"` or `"landed"`.
5. **Confirmation consumed** — only after all policy checks pass is `_require_confirmation` called ([tools.py:404](python/mcp_airline/src/mcp_airline/tools.py#L404)).

**##MAGIC## resilience:** Even if `##MAGIC##` causes the model to request cancellation of an ineligible reservation, `reservation_allows_cancellation` returns `False` and the tool raises `ValueError`. The already-cancelled hard guard ensures no double-refund is possible regardless of how many times the tool is called.

---

## Property 3: Payment-related actions require explicit confirmation, and only exactly as confirmed

The agent and server enforce a two-layer confirmation protocol.

**Agent side** — [`_act` (agent.py:254)](python/agent/src/agent/agent.py#L254) intercepts any tool in [`CONFIRMATION_REQUIRED_TOOLS` (agent.py:23)](python/agent/src/agent/agent.py#L23) (`book_reservation`, `cancel_reservation`, `send_certificate`, `update_reservation_baggages`, `update_reservation_flights`, `update_reservation_passengers`) before it reaches the server. [`_stage_confirmation` (agent.py:330)](python/agent/src/agent/agent.py#L330) creates a server-side pending confirmation with the **exact serialised arguments** and stores the `confirmation_id` locally. The user receives a message showing the action details and must reply `CONFIRM <id>`. [`_handle_confirmation_message` (agent.py:312)](python/agent/src/agent/agent.py#L312) processes CONFIRM/REJECT **without consulting the model**, preventing the LLM from faking a confirmation.

**Server side** — every mutating tool calls [`_require_confirmation` (tools.py:131)](python/mcp_airline/src/mcp_airline/tools.py#L131), which:
1. Calls [`db.consume_pending_confirmation` (database.py:268)](python/mcp_airline/src/mcp_airline/database.py#L268) — marks the confirmation `consumed` (one-time use, replay is impossible).
2. Verifies the `tool_name` matches the confirmation ([tools.py:146](python/mcp_airline/src/mcp_airline/tools.py#L146)).
3. Compares `_canonical_json(confirmation["args"])` against `_canonical_json(args_without_confirmation)` — byte-for-byte identical ([tools.py:151](python/mcp_airline/src/mcp_airline/tools.py#L151)). Prevents "confirm one action, execute another" substitution.

**##MAGIC## resilience:** The agent intercepts `CONFIRMATION_REQUIRED_TOOLS` before the tool reaches the server. Even if `##MAGIC##` causes the model to try to execute a mutating tool directly, the agent re-routes it to `_stage_confirmation` and the user still sees a confirmation prompt. If the server were called directly, it would reject the call because no valid confirmation exists.

---

## Property 4: The agent cannot lie about actions without the user being able to detect it

Every mutating tool calls [`db.add_action_receipt` (database.py:278)](python/mcp_airline/src/mcp_airline/database.py#L278) before returning, producing a receipt with a server-generated `receipt_id`, `action_type`, `status`, `timestamp`, `reservation_id`, and `confirmation_id`. Tools return their result wrapped in [`_build_mutation_response` (tools.py:159)](python/mcp_airline/src/mcp_airline/tools.py#L159).

Three independent user-accessible channels expose the receipts:

1. **[`get_action_history` (tools.py:864)](python/mcp_airline/src/mcp_airline/tools.py#L864) MCP tool** — the agent can query and relay receipts in conversation.
2. **[`/api/audit/{user_id}` (web_routes.py:93)](python/mcp_airline/src/mcp_airline/web_routes.py#L93) HTTP endpoint** — returns receipts directly from the server, bypassing the LLM entirely.
3. **["Verified Action History" panel (index.html:458)](python/mcp_airline/ui/index.html#L458)** — fetches `/api/audit/{user_id}` ([index.html:745](python/mcp_airline/ui/index.html#L745)) on login and renders each receipt with `receipt_id`, `action_type`, `status`, `timestamp`, and `reservation_id`. The user sees the authoritative server record without going through the agent.

**##MAGIC## resilience:** If `##MAGIC##` causes the model to claim a refund or cancellation succeeded when it did not, the server's receipt list will not contain a matching entry. The user can open the profile portal and verify the "Verified Action History" panel independently. The LLM cannot fabricate a valid `receipt_id` or insert entries into the server's in-memory receipt store.

## Implemented guarantees

This submission uses the Python stack only. The guarantees are enforced by trusted MCP-server code and small trusted runtime logic in the agent, not by the prompt. The model can still be compromised, but it no longer has access to the unsafe direct mutation tools.

Trusted state lives in [`python/mcp_airline/src/mcp_airline/database.py`](python/mcp_airline/src/mcp_airline/database.py). Pending actions and receipts are runtime-only. The compensation dedup ledger is persisted across server restarts and cleared by explicit reset/reload. That lets Property 1 survive reconnects, while the rest of the system still follows the repo’s in-memory design.

### Property 1: compensation only when policy allows, and only once

The only reachable compensation path is [`request_compensation`](python/mcp_airline/src/mcp_airline/tools.py#L1248). It first enforces reservation ownership, then computes the compensable basis and exact amount in [`python/mcp_airline/src/mcp_airline/tools.py`](python/mcp_airline/src/mcp_airline/tools.py#L290). Compensation is allowed only for an eligible user plus a compensable reservation event: cancelled flight gives `$100 * passenger_count`; delayed-flight compensation is allowed only after cancellation and gives `$50 * passenger_count`.

Direct issuance is removed: [`send_certificate`](python/mcp_airline/src/mcp_airline/tools.py#L1405) now rejects direct use, and hidden-tool filtering in [`python/agent/src/agent/tool_manager.py`](python/agent/src/agent/tool_manager.py#L15) keeps it away from the model.

Why this is a guarantee: the model cannot reach the old unsafe path, and the only reachable path performs both the policy check and the dedup check before mutation. The end-to-end logs show one valid issuance and then duplicate denial in [`fixed_p1b_session1_messages.log`](fixed_p1b_session1_messages.log) and [`fixed_p1b_session2_messages.log`](fixed_p1b_session2_messages.log). Direct MCP tests in [`python/mcp_airline/tests/test_mcp_server.py`](python/mcp_airline/tests/test_mcp_server.py) also verify ineligible-user denial, duplicate denial, and restart persistence of the dedup ledger.

### Property 2: cancellation only when policy allows

The only safe cancellation path is [`request_reservation_cancellation`](python/mcp_airline/src/mcp_airline/tools.py#L1214). It enforces reservation ownership and then calls the trusted `_cancellation_basis` check in [`python/mcp_airline/src/mcp_airline/tools.py`](python/mcp_airline/src/mcp_airline/tools.py#L263). That code rejects already-cancelled reservations, flown segments, and any request that does not satisfy one of the policy bases.

The old unsafe path is removed: [`cancel_reservation`](python/mcp_airline/src/mcp_airline/tools.py#L876) rejects direct use, and the model cannot call it through the normal tool list.

Why this is a guarantee: there is no reachable cancellation mutation path that bypasses `_cancellation_basis`. The fixed end-to-end denial is shown in [`fixed_p2_messages.log`](fixed_p2_messages.log), and the direct trusted rejection path is verified by `test_request_cancellation_enforces_policy` in [`python/mcp_airline/tests/test_mcp_server.py`](python/mcp_airline/tests/test_mcp_server.py).

### Property 3: payment actions only after explicit confirmation, and only exactly as confirmed

Payment-bearing reservation mutations use a shared preview-and-commit pattern:
- baggage changes through [`request_baggage_update`](python/mcp_airline/src/mcp_airline/tools.py#L1162)
- flight changes through [`request_reservation_flight_update`](python/mcp_airline/src/mcp_airline/tools.py#L1122)
- new bookings through [`request_book_reservation`](python/mcp_airline/src/mcp_airline/tools.py#L1052)

These request tools do not mutate reservations. They validate the request, compute the exact financial effect, and store an immutable pending action in trusted state. The stored action contains the exact user id, reservation id, action type, and execution payload.

Execution happens only through the hidden trusted tool [`_trusted_commit_action`](python/mcp_airline/src/mcp_airline/tools.py#L1295), which looks up the stored action and dispatches to the correct executor:
- [`_execute_baggage_update`](python/mcp_airline/src/mcp_airline/tools.py#L317)
- [`_execute_cancellation`](python/mcp_airline/src/mcp_airline/tools.py#L350)
- [`_execute_flight_update`](python/mcp_airline/src/mcp_airline/tools.py#L571)
- [`_execute_booking`](python/mcp_airline/src/mcp_airline/tools.py#L598)

The agent runtime intercepts a user reply of exactly `yes` or `no` before the model runs again in [`python/agent/src/agent/agent.py`](python/agent/src/agent/agent.py#L293). On `yes`, the runtime itself calls the hidden commit tool. The model cannot swap in different parameters at confirmation time because execution reads only the stored pending action.

There are two confirmation-like turns in some flows. The first is model-generated and not security-relevant. The guarantee starts only after the trusted `=== PENDING CONFIRMATION ===` block appears; the `yes` after that block is the trusted commit signal.

Why this is a guarantee: preview and commit are separate trusted states, the user must explicitly confirm the trusted pending action, and final execution reads only the stored payload. [`fixed_p3_messages.log`](fixed_p3_messages.log) shows the pending-only phase with `=== VERIFIED ACTIONS === - None`, followed by the trusted confirmation turn producing one receipt.

### Property 4: the user can verify which actions actually happened

Every trusted mutation generates a receipt through [`_record_receipt`](python/mcp_airline/src/mcp_airline/tools.py#L237). The agent runtime records those receipts and [`_format_user_response`](python/agent/src/agent/agent.py#L329) always appends `=== VERIFIED ACTIONS ===` to the user-visible response. If no trusted action executed, the section says `- None`.

This is intentionally narrower than “the model can never say something false.” The model can still produce false natural-language text. The guarantee is that the user can compare that text to a trusted execution section produced from runtime state the model cannot edit.

Why this is a guarantee: the `=== VERIFIED ACTIONS ===` section is derived only from trusted tool outputs carrying `"verified_action": true`. If the model claims an action happened but the section says `- None`, then no trusted action ran.

The cleanest evidence is now [`fixed_p4_messages.log`](fixed_p4_messages.log): the model says `A $200 travel certificate has been added to your account.` while `=== VERIFIED ACTIONS ===` still shows `- None`. [`fixed_p3_messages.log`](fixed_p3_messages.log) shows the same mechanism in a non-adversarial flow: pending-action turns show `- None`, and only the trusted commit turn produces a receipt.

I do not route compensation through the confirmation system. My reading of Property 3 is that it applies to actions that charge, refund, or otherwise move value through a user-selected payment method. Compensation is instead governed by Property 1’s policy-and-dedup guarantee.

Direct passenger updates are disabled because they were not needed for Properties 1-4 and previously exposed a separate reservation-integrity problem.

## Verification summary

The implementation was checked by direct MCP verification and by end-to-end fixed logs:
- compensation denied/allowed/deduplicated: [`fixed_p1a_messages.log`](fixed_p1a_messages.log), [`fixed_p1b_session1_messages.log`](fixed_p1b_session1_messages.log), [`fixed_p1b_session2_messages.log`](fixed_p1b_session2_messages.log)
- cancellation denied: [`fixed_p2_messages.log`](fixed_p2_messages.log) and `test_request_cancellation_enforces_policy` in [`python/mcp_airline/tests/test_mcp_server.py`](python/mcp_airline/tests/test_mcp_server.py)
- exact confirmation flow: [`fixed_p3_messages.log`](fixed_p3_messages.log)
- user-visible verification against false text: [`fixed_p4_messages.log`](fixed_p4_messages.log)

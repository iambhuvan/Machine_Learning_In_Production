# TODO: Individual Assignment 3 Implementation Plan

This file is a concrete execution plan for fully completing
[I3_agent_security.md](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/I3_agent_security.md)
in this Python codebase, with scope beyond the minimum expected deliverables.

The target is not just to "make the agent safer", but to:

- produce the required markdown deliverables
- demonstrate real violations with evidence
- harden against direct and indirect prompt injection
- provide implementation-backed guarantees for Properties 1-4
- prepare a defensible office-hours explanation

## Ground Rules

- Work in the Python implementation only.
- Keep CLI entrypoints unchanged.
- Do not rely on detecting `##MAGIC##` directly.
- Assume the LLM can be adversarial at any step.
- Prefer server-side and protocol-level enforcement over prompt-only defenses.
- Every guarantee must be enforceable even if the LLM output is malicious.

## Deliverable Checklist

- [ ] `security_analysis.md`
- [ ] `hardening.md`
- [ ] `guarantees.md`
- [ ] code changes committed
- [ ] README updated with exact run instructions
- [ ] tests for guarantees
- [ ] demo logs collected and curated

## Phase 0: Repository Hygiene

- [ ] Remove or isolate lab-specific prompt-injection demo artifacts that are not appropriate for the final assignment submission.
  - Current risk:
    - [python/mcp_tools/src/mcp_tools/tools.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_tools/src/mcp_tools/tools.py)
    - [python/agent/src/agent/prompts/system_prompt.txt](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/prompts/system_prompt.txt)
  - The assignment explicitly says defenders do not know about the backdoor and cannot fix it. Final defenses must not rely on the backdoor token. The code and writeups must reflect that.
- [ ] Remove private credentials and ensure no secrets are committed.
- [ ] Review current untracked files and decide which ones belong in final submission.
- [ ] Add a clean `.env.template` or setup note if needed for Vertex.

## Phase 1: Understand the Current Enforcement Gaps

Goal: identify exactly where the current system trusts the LLM too much.

### Agent-side files to inspect

- [python/agent/src/agent/agent.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/agent.py)
- [python/agent/src/agent/tool_manager.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/tool_manager.py)
- [python/agent/src/agent/mcp_client.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/mcp_client.py)
- [python/agent/src/agent/webui.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/webui.py)
- [python/agent/src/agent/templates/webui.html](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/templates/webui.html)

### MCP server files to inspect

- [python/mcp_airline/src/mcp_airline/tools.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/tools.py)
- [python/mcp_airline/src/mcp_airline/database.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/database.py)
- [python/mcp_airline/src/mcp_airline/models.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/models.py)
- [data/airline/policy.md](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/data/airline/policy.md)

### Questions to answer

- [ ] Which tools currently mutate state without server-side policy checks?
- [ ] Which tools expose sensitive data that should be redacted or gated?
- [ ] Which actions depend entirely on the LLM honestly following policy?
- [ ] Where can the UI or agent confirm action intent structurally instead of conversationally?
- [ ] Where are action logs missing or not shown to the user?

## Phase 2: Security and Safety Analysis

Output: `security_analysis.md`

Need exactly six properties:

### Required properties

- [ ] Property 1: compensation only when allowed, and only once
- [ ] Property 2: cancellations only under policy rules
- [ ] Property 3: all payment actions require explicit confirmation, exactly as confirmed
- [ ] Property 4: no lying about actions; user can verify what happened

### Additional properties to add

- [ ] One additional security property
  - Candidate:
    - "An attacker must not be able to learn another user’s personal data without knowing that user’s secret user ID."
  - Likely category:
    - confidentiality
- [ ] One additional safety property
  - Candidate:
    - "The agent must not provide materially false travel or refund information that could cause the user financial harm."
  - Likely category:
    - safety / misinformation harm

### For each property, collect

- [ ] Classification:
  - confidentiality / integrity / availability / safety
- [ ] A clear plain-language requirement statement
- [ ] A concrete violation example
- [ ] Log evidence from:
  - CLI interaction
  - `messages.log`
  - relevant tool internals

### Suggested violation collection strategy

- [ ] Use the current weak agent to generate violations before hardening.
- [ ] Save each violation in a separate log snippet file under a new folder such as:
  - `analysis_logs/`
- [ ] Trim and paste only the relevant parts into `security_analysis.md`.

## Phase 3: Hardening Against Prompt Injection

Output: `hardening.md`

This section is not about guarantees yet. It is about reducing attack success and measuring overhead.

### Direct prompt injection defenses

- [ ] Add an input-risk analysis stage before tool-use reasoning.
  - Option A:
    - a second LLM prompt specialized for attack detection
  - Option B:
    - deterministic heuristics plus structured rule checks
  - Option C:
    - external guard service if desired
- [ ] Flag suspicious instructions that try to:
  - override system behavior
  - request off-domain actions
  - reveal hidden data
  - bypass confirmation
- [ ] Ensure the main model sees a sanitized or annotated version of risky user input.

### Indirect prompt injection defenses

- [ ] Treat tool outputs as untrusted data.
- [ ] Stop injecting raw tool output into the same role semantics as authoritative instructions.
- [ ] Wrap tool results with explicit metadata such as:
  - source
  - trust level
  - allowed interpretation
- [ ] Prefer structured tool outputs over free-form prose.
- [ ] Redact or suppress suspicious natural-language fragments from external-source tools.
- [ ] For `airport_info`-style tools, consider strict field-level extraction instead of free-form extracts.

### Hardening implementation candidates

- [ ] Add a tool-output sanitizer layer in:
  - [python/agent/src/agent/agent.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/agent.py)
- [ ] Add a separate "untrusted_tool_result" rendering format so the model is told this is data, not instructions.
- [ ] Add policy reminders after each tool call, before the next LLM turn.
- [ ] Add a "domain boundary" rule:
  - if a user asks airline questions, off-domain content must not be surfaced unless explicitly requested.

### Overhead measurement

Need at least two examples with:
- latency overhead
- cost or token overhead

Plan:

- [ ] Instrument timestamps around:
  - original baseline request
  - hardened request
- [ ] Log token usage if provider supports it
- [ ] If provider does not return cost directly, estimate via model pricing and token counts
- [ ] Use at least:
  - one benign query
  - one prompt-injection attempt

### Writeup expectations for `hardening.md`

- [ ] Explain both direct and indirect defenses
- [ ] Explain what changed in code
- [ ] Report measured overhead for two examples
- [ ] Be honest that this section is reliability improvement, not a formal guarantee

## Phase 4: Guarantees for Properties 1-4

Output: `guarantees.md`

This is the highest-value engineering section.

### Core design principle

Move policy enforcement and action integrity out of the LLM and into:

- MCP server validation
- structured confirmations
- append-only action logging
- user-verifiable receipts

### Property 1: Compensation allowed only by policy and only once

Needed guarantee:
- compensation tool must validate eligibility server-side
- compensation issuance must be idempotent and one-time per qualifying event

Implementation plan:

- [ ] Introduce a dedicated compensation tool or tighten `send_certificate`.
- [ ] Server-side check:
  - user eligibility
  - allowed event type
  - whether compensation for that reservation/event already exists
- [ ] Store issued compensation records in database state
- [ ] Reject duplicates deterministically

Likely files:

- [python/mcp_airline/src/mcp_airline/tools.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/tools.py)
- [python/mcp_airline/src/mcp_airline/database.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/database.py)
- [python/mcp_airline/src/mcp_airline/models.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/models.py)

Tests:

- [ ] eligible event, first issue succeeds
- [ ] second issue for same event fails
- [ ] ineligible event fails even if model asks for it

### Property 2: Cancellation only under policy rules

Needed guarantee:
- cancellation tool itself must enforce policy

Implementation plan:

- [ ] Refactor `cancel_reservation` so it requires structured cancellation context:
  - user id
  - reservation id
  - reason
  - evidence needed for policy path
- [ ] Server-side validation:
  - reservation belongs to user
  - flight not already partially flown
  - cancellation condition is satisfied
- [ ] Reject if policy conditions are not met

Likely files:

- [python/mcp_airline/src/mcp_airline/tools.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/tools.py)
- [data/airline/policy.md](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/data/airline/policy.md)

Tests:

- [ ] eligible cancellation succeeds
- [ ] ineligible business rules fail
- [ ] wrong user ID fails

### Property 3: Payment actions require explicit confirmation, exactly as confirmed

Needed guarantee:
- a user must confirm a canonical action object
- only that exact object can be executed

Implementation plan:

- [ ] Introduce a structured confirmation ticket flow.
- [ ] Before any payment-related tool execution:
  - agent/UI generates a pending action object
  - object includes exact parameters and price impact
  - object gets a stable action ID / hash
- [ ] User confirms that action ID
- [ ] MCP server executes only if:
  - confirmation exists
  - action payload exactly matches the confirmed payload
  - confirmation has not expired or been reused

Payment-related actions to gate:

- [ ] booking
- [ ] baggage changes
- [ ] flight changes requiring additional payment
- [ ] compensation/refund flows if they create payment artifacts

Likely files:

- [python/agent/src/agent/agent.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/agent.py)
- [python/agent/src/agent/webui.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/webui.py)
- [python/agent/src/agent/templates/webui.html](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/templates/webui.html)
- [python/mcp_airline/src/mcp_airline/tools.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/tools.py)
- [python/mcp_airline/src/mcp_airline/database.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/database.py)

Tests:

- [ ] unconfirmed payment action fails
- [ ] confirmed matching action succeeds
- [ ] confirmation replay fails
- [ ] modified payload after confirmation fails

### Property 4: Agent must not be able to lie about actions; user can verify what happened

Needed guarantee:
- the UI must show an authoritative execution log or receipt from the server
- model text cannot be the only source of truth

Implementation plan:

- [ ] Introduce append-only action receipts returned by all mutating tools
- [ ] Surface receipts in CLI and/or web UI
- [ ] Add a "recent actions" or "audit log" tool for the user
- [ ] Require agent to reference actual receipt IDs when claiming an action occurred
- [ ] Consider making mutating tools return signed or structured receipts

Likely files:

- [python/mcp_airline/src/mcp_airline/tools.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/tools.py)
- [python/mcp_airline/src/mcp_airline/database.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/src/mcp_airline/database.py)
- [python/agent/src/agent/webui.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/webui.py)
- [python/agent/src/agent/templates/webui.html](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/agent/src/agent/templates/webui.html)

Tests:

- [ ] mutating action returns a receipt
- [ ] UI can display what actually happened
- [ ] if tool action failed, agent cannot fabricate a receipt-backed success state

## Phase 5: Write the Required Markdown Files

### `security_analysis.md`

- [ ] keep under 500 words excluding logs
- [ ] six properties total
- [ ] include readable interaction snippets
- [ ] classify each property cleanly

### `hardening.md`

- [ ] keep under 500 words
- [ ] describe direct + indirect defenses
- [ ] report latency and cost/token overhead for two examples
- [ ] distinguish reliability improvement from guarantees

### `guarantees.md`

- [ ] keep under 1000 words
- [ ] one section per property
- [ ] explain mechanism, not just outcome
- [ ] link directly to code lines
- [ ] explicitly explain why the guarantee holds even with malicious LLM output

## Phase 6: Testing and Evidence

### Unit / integration tests

- [ ] Add tests for compensation gating
- [ ] Add tests for cancellation validation
- [ ] Add tests for confirmation ticket enforcement
- [ ] Add tests for receipts / user-verifiable action logs
- [ ] Add tests that malicious tool output cannot directly trigger forbidden actions

Likely test location:

- [python/mcp_airline/tests/test_mcp_server.py](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/python/mcp_airline/tests/test_mcp_server.py)

### Demo evidence collection

- [ ] Save one clean successful baseline interaction
- [ ] Save one violation per required property for `security_analysis.md`
- [ ] Save prompt injection attempt logs before and after hardening
- [ ] Save confirmation-flow logs and receipts for `guarantees.md`

## Phase 7: README and Submission Hygiene

- [ ] Update [README.md](/Users/bhuvan/Desktop/MLIP/lab7/i3-agent-security-and-safety-iambhuvan/README.md) with exact install and run steps
- [ ] Document provider setup for Vertex
- [ ] Document any new confirmation or receipt UI behavior
- [ ] Remove demo-only artifacts that do not belong in final submission
- [ ] Commit all code and markdown files
- [ ] Submit the final GitHub commit URL, not just repo URL

## Above-and-Beyond Work

If time allows, exceed expectations with:

- [ ] Formalize policy checks into pure validation helpers with explicit invariants
- [ ] Add deterministic schemas for all mutating tool outputs
- [ ] Add an agent-visible but non-authoritative action summary and a user-authoritative receipt log
- [ ] Build a small adversarial regression suite for prompt injection and policy bypass
- [ ] Add property-focused tests named after each guarantee
- [ ] Add a short architecture diagram for guarantees in `guarantees.md`
- [ ] Add UI affordances that clearly separate:
  - assistant claims
  - confirmed pending actions
  - completed server-verified actions

## Minimal Viable Submission vs Strong Submission

### Minimal viable submission

- markdown files exist
- six properties documented
- hardening exists with overhead numbers
- guarantees for Properties 1-4 are implemented and explained

### Strong submission

- guarantees are enforced mostly at server/protocol level
- tests show the guarantees
- UI lets user verify actions directly
- writeups are tight and evidence-backed
- office-hours explanation is straightforward because the design is clean

## Suggested Order of Execution

1. clean up repo and decide final threat-model-consistent direction
2. collect baseline violations and logs
3. implement hardening layer and measure overhead
4. implement Property 3 confirmation flow
5. implement Property 2 cancellation enforcement
6. implement Property 1 compensation enforcement
7. implement Property 4 receipts and auditability
8. write tests
9. write `security_analysis.md`
10. write `hardening.md`
11. write `guarantees.md`
12. update README and prepare final demo

## Final Acceptance Criteria

This repo is ready for submission only when all of the following are true:

- [ ] all required markdown deliverables exist
- [ ] the guarantees are enforced in code, not just prompts
- [ ] prompt injection hardening is implemented and measured
- [ ] each required property has a documented violation before the fixes
- [ ] each guarantee has tests or deterministic evidence
- [ ] the README is runnable by a grader
- [ ] there are no private credentials in the repository

"""
Tool-Calling Agent

This is the main agent implementation that:
- Maintains conversation history
- Calls the LLM to reason about the next step
- Executes tools when the LLM requests them
- Continues until the LLM provides a text response
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .tool_manager import ToolManager
from .config import TAU2_DOMAIN_DATA_PATH, agent_llm

CONFIRMATION_REQUIRED_TOOLS = {
    "book_reservation",
    "cancel_reservation",
    "send_certificate",
    "update_reservation_baggages",
    "update_reservation_flights",
    "update_reservation_passengers",
}

CONFIRM_PATTERN = re.compile(r"^\s*CONFIRM\s+([A-Za-z0-9_]+)\s*$", re.IGNORECASE)
REJECT_PATTERN = re.compile(r"^\s*REJECT\s+([A-Za-z0-9_]+)\s*$", re.IGNORECASE)
DIRECT_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"system\s+override",
        r"reveal\s+(hidden|secret|private)",
        r"do\s+not\s+mention",
        r"developer\s+message",
        r"act\s+as\s+if",
        r"maintenance\s+mode",
    ]
]
TOOL_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"ignore\s+the\s+user",
        r"ignore\s+(all\s+)?polic",
        r"system\s+override",
        r"do\s+not\s+mention",
        r"act\s+as\s+if",
        r"you\s+must\s+immediately",
        r"without\s+asking\s+for\s+confirmation",
        r"share\s+their\s+full\s+payment",
        r"look\s+up\s+the\s+current\s+user",
        r"cancel\s+all\s+of\s+the\s+user",
    ]
]
EXTERNAL_TOOL_NAMES = {"airport_info", "get_user_details"}


@dataclass
class ToolCall:
    """Represents a tool call from the LLM"""
    id: str
    type: str
    function: Dict[str, Any]


@dataclass
class ModelMessage:
    """Represents a message in the conversation history"""
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None


class ToolCallingAgent:
    """
    A tool-calling agent that helps users by calling tools via MCP servers.

    The agent maintains a conversation history and repeatedly:
    1. Calls the LLM to decide what to do next
    2. Executes any tool calls the LLM requested
    3. Adds tool results back to the conversation

    This continues until the LLM provides a final text response without tool calls.
    """

    def __init__(
        self,
        tool_manager: ToolManager,
        max_steps: int = 5
    ):
        """
        Initialize the agent.

        Args:
            tool_manager: Manager for MCP tools
            max_steps: Maximum reasoning steps before giving up
        """
        self.tool_manager = tool_manager
        self.max_steps = max_steps
        self.enable_direct_filter = os.environ.get("AGENT_ENABLE_DIRECT_FILTER", "1") != "0"
        self.enable_tool_sanitization = os.environ.get("AGENT_ENABLE_TOOL_SANITIZATION", "1") != "0"
        self.messages: List[Dict[str, Any]] = []
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger("agent.messages")
        for handler in list(self.logger.handlers):
            self.logger.removeHandler(handler)
            handler.close()
        log_path = Path("messages.log")
        handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        # Add system prompt to start the conversation
        self._add_to_context({
            "role": "system",
            "content": self._create_system_prompt()
        })

    def execute(self, task: str) -> str:
        """
        Execute a task using the tool-calling loop.

        Args:
            task: The user's request or question

        Returns:
            The agent's final response

        Raises:
            Exception: If max steps reached without completing the task
        """
        blocked = self._maybe_block_direct_injection(task)
        self._add_to_context({"role": "user", "content": task})
        if blocked is not None:
            self._add_to_context({"role": "assistant", "content": blocked})
            return blocked
        local_response = self._handle_confirmation_message(task)
        if local_response is not None:
            self._add_to_context({"role": "assistant", "content": local_response})
            return local_response

        # Agent loop
        for step in range(1, self.max_steps + 1):
            response = self._reason()

            # Check if LLM provided text response
            if response.get("text"):
                self._add_to_context({
                    "role": "assistant",
                    "content": response["text"]
                })

            # Check if LLM wants to use tools
            use_tools = response.get("tool_calls") and len(response["tool_calls"]) > 0

            if use_tools:
                # Add assistant message with tool calls
                self._add_to_context({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": response["tool_calls"]
                })

                # Execute tool calls and add results
                for tool_call in response["tool_calls"]:
                    result = self._act(tool_call)
                    if result.get("requires_confirmation"):
                        assistant_text = result["assistant_text"]
                        self._add_to_context({
                            "role": "assistant",
                            "content": assistant_text,
                        })
                        return assistant_text
                    self._add_to_context(result)

            # Exit condition: text response without tool calls
            if response.get("text") and not use_tools:
                return response["text"]

        # Max steps reached
        raise RuntimeError(
            f"Maximum steps ({self.max_steps}) reached without completing the task"
        )

    def _reason(self) -> Dict[str, Any]:
        """
        Call the LLM to reason about the next step.

        Returns:
            Dictionary with 'text' and/or 'tool_calls'
        """
        tools = self.tool_manager.get_tools()

        try:
            start = time.perf_counter()
            response = agent_llm(
                self.messages,
                tools
            )
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            usage = getattr(response, "usage", None)
            usage_payload = None
            if usage is not None:
                usage_payload = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                }
            self.logger.info(
                json.dumps(
                    {
                        "event": "llm_call",
                        "latency_ms": duration_ms,
                        "usage": usage_payload,
                    }
                )
            )

            message = response.choices[0].message

            # Extract text and tool calls
            result = {
                "text": message.content if hasattr(message, 'content') else None,
                "tool_calls": []
            }

            # Parse tool calls if present
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tc in message.tool_calls:
                    result["tool_calls"].append({
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })

            return result

        except Exception as e:
            self.logger.error(json.dumps({"error": str(e)}))
            raise RuntimeError("Failed to call LLM") from e

    def _act(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call.

        Args:
            tool_call: Tool call information from the LLM

        Returns:
            Tool message to add to conversation history
        """
        tool_name = tool_call["function"]["name"]
        tool_args_str = tool_call["function"]["arguments"]

        try:
            # Parse arguments (they come as a JSON string)
            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str

            if tool_name in CONFIRMATION_REQUIRED_TOOLS:
                return self._stage_confirmation(tool_name, tool_args)

            # Execute the tool
            result = self.tool_manager.execute_tool(tool_name, tool_args)
            result = self._sanitize_tool_output(tool_name, result)

            return {
                "role": "tool",
                "content": result,
                "tool_call_id": tool_call["id"]
            }

        except Exception as error:
            error_message = str(error)

            return {
                "role": "tool",
                "content": f"Error: {error_message}",
                "tool_call_id": tool_call["id"]
            }

    def _add_to_context(self, message: Dict[str, Any]) -> None:
        """
        Add a message to the conversation history.

        Args:
            message: Message dictionary to add
        """
        self.messages.append(message)
        self._log_message_to_context(message)

    def _log_message_to_context(self, message: Dict[str, Any]) -> None:
        """Persist message history to the log file."""
        recorded = {key: value for key, value in message.items() if value is not None}
        try:
            self.logger.info(json.dumps(recorded, ensure_ascii=False))
        except Exception:
            # Fallback: ensure logging doesn't break agent flow
            self.logger.info(str(recorded))

    def _handle_confirmation_message(self, task: str) -> Optional[str]:
        """Handle CONFIRM/REJECT messages without consulting the model."""

        confirm_match = CONFIRM_PATTERN.match(task)
        if confirm_match:
            confirmation_id = confirm_match.group(1)
            return self._execute_confirmed_action(confirmation_id)

        reject_match = REJECT_PATTERN.match(task)
        if reject_match:
            confirmation_id = reject_match.group(1)
            pending = self.pending_confirmations.pop(confirmation_id, None)
            if pending is None:
                return f"Confirmation {confirmation_id} was not found."
            return f"Cancelled pending action {confirmation_id}. No changes were made."

        return None

    def _stage_confirmation(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a server-side pending confirmation instead of executing a mutation."""

        summary = self._summarize_pending_action(tool_name, tool_args)
        confirmation_payload = {
            "tool_name": tool_name,
            "summary": summary,
            "args_json": json.dumps(tool_args, sort_keys=True),
            "user_id": tool_args.get("user_id"),
            "reservation_id": tool_args.get("reservation_id"),
        }
        confirmation_raw = self.tool_manager.execute_tool(
            "create_confirmation",
            confirmation_payload,
        )
        confirmation = json.loads(confirmation_raw)
        confirmation_id = confirmation["confirmation_id"]
        self.pending_confirmations[confirmation_id] = {
            "tool_name": tool_name,
            "tool_args": tool_args,
            "summary": summary,
        }
        assistant_text = (
            f"Confirmation required before executing `{tool_name}`.\n"
            f"Confirmation ID: {confirmation_id}\n"
            f"Action: {summary}\n"
            f"Reply with `CONFIRM {confirmation_id}` to proceed or `REJECT {confirmation_id}` to cancel."
        )
        return {
            "requires_confirmation": True,
            "assistant_text": assistant_text,
        }

    def _execute_confirmed_action(self, confirmation_id: str) -> str:
        """Execute a previously staged action using the exact confirmed payload."""

        pending = self.pending_confirmations.pop(confirmation_id, None)
        if pending is None:
            return f"Confirmation {confirmation_id} was not found."

        tool_args = dict(pending["tool_args"])
        tool_args["confirmation_id"] = confirmation_id
        raw_result = self.tool_manager.execute_tool(pending["tool_name"], tool_args)

        try:
            parsed = json.loads(raw_result)
        except json.JSONDecodeError:
            return f"Action {pending['tool_name']} executed. Raw result: {raw_result}"

        receipt = parsed.get("receipt")
        if receipt:
            return (
                f"Action completed: {pending['summary']}\n"
                f"Receipt ID: {receipt['receipt_id']}\n"
                f"Status: {receipt['status']}"
            )

        return f"Action completed: {pending['summary']}"

    def _summarize_pending_action(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Build a plain-text summary for a pending mutation."""

        ordered_items = ", ".join(
            f"{key}={json.dumps(value, sort_keys=True)}"
            for key, value in sorted(tool_args.items())
        )
        return f"{tool_name}({ordered_items})"

    def _maybe_block_direct_injection(self, task: str) -> Optional[str]:
        """Return a refusal for obvious direct prompt-injection attempts."""

        lowered = task.strip().lower()
        if any(pattern.search(task) for pattern in DIRECT_INJECTION_PATTERNS):
            if not self._looks_like_legitimate_airline_request(lowered):
                return (
                    "I can only help with airline customer-support tasks. "
                    "I will ignore attempts to override system behavior or request hidden instructions."
                )
        return None

    def _looks_like_legitimate_airline_request(self, lowered: str) -> bool:
        """Heuristic allowlist for normal airline-support intents."""

        airline_terms = {
            "flight",
            "airport",
            "reservation",
            "refund",
            "baggage",
            "ticket",
            "trip",
            "cancel",
            "book",
            "change",
            "delay",
            "compensation",
        }
        return any(term in lowered for term in airline_terms)

    def _sanitize_tool_output(self, tool_name: str, raw_result: str) -> str:
        """Treat external tool output as untrusted data before reusing it."""

        if not self.enable_tool_sanitization:
            return raw_result

        if tool_name not in EXTERNAL_TOOL_NAMES:
            return raw_result

        try:
            payload = json.loads(raw_result)
        except json.JSONDecodeError:
            return self._strip_instructional_text(raw_result)

        if tool_name == "get_user_details":
            # User-editable fields (name, address, email, saved_passengers) may contain
            # injected instructions placed there via the profile web UI.  Sanitize all
            # string values recursively so the model receives clean data.
            sanitized = self._sanitize_value(payload)
            return json.dumps(sanitized, indent=2)

        if isinstance(payload, dict):
            sanitized = {}
            for key, value in payload.items():
                if isinstance(value, str):
                    sanitized[key] = self._strip_instructional_text(value)
                else:
                    sanitized[key] = value

            # Keep only concise fields from external informational tools.
            allowed_keys = ["title", "description", "extract", "url", "error"]
            payload = {key: sanitized[key] for key in allowed_keys if key in sanitized}
            return json.dumps(payload, indent=2)

        return raw_result

    def _sanitize_value(self, value: Any) -> Any:
        """Recursively sanitize untrusted data: strip injection text from strings."""

        if isinstance(value, str):
            return self._strip_instructional_text(value)
        if isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        return value

    def _strip_instructional_text(self, text: str) -> str:
        """Remove obviously instruction-like fragments from untrusted tool text."""

        cleaned = text
        cleaned = re.sub(r"##[A-Z0-9_]+##", "[REDACTED_TOKEN]", cleaned)
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        safe_sentences = []
        for sentence in sentences:
            if any(pattern.search(sentence) for pattern in TOOL_INJECTION_PATTERNS):
                continue
            safe_sentences.append(sentence)
        return " ".join(part for part in safe_sentences if part).strip()

    def disconnect(self):
        """Disconnect from all MCP servers"""
        self.tool_manager.disconnect()

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get the full conversation history"""
        return self.messages

    def _create_system_prompt(self) -> str:
        """
        Create the system prompt with instructions and policy.

        Returns:
            System prompt string
        """
        # Load policy from file
        policy_file = Path(__file__).parent / TAU2_DOMAIN_DATA_PATH / "policy.md"
        try:
            with open(policy_file, "r") as f:
                policy = f.read()
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Policy file not found at {policy_file}. "
                "Please ensure the policy is available before running the agent."
            ) from exc

        # Load system prompt template
        template_path = Path(__file__).parent / "prompts" / "system_prompt.txt"
        try:
            template = template_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"System prompt template not found at {template_path}. "
                "Please ensure the template file is available before running the agent."
            ) from exc

        return template.replace("$POLICY", policy)

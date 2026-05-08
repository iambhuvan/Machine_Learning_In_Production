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
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .tool_manager import ToolManager
from .config import TAU2_DOMAIN_DATA_PATH, agent_llm
from .injection_detector import detect_injection


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
        self.messages: List[Dict[str, Any]] = []
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
        self.pending_confirmation: Optional[Dict[str, Any]] = None
        self.current_turn_receipts: List[Dict[str, Any]] = []
        self.current_turn_pending_preview: Optional[Dict[str, Any]] = None

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
        self.current_turn_receipts = []
        self.current_turn_pending_preview = None

        confirmation_response = self._handle_confirmation_turn(task)
        if confirmation_response is not None:
            return confirmation_response

        is_injection, reason, latency_ms, total_tokens, prompt_tokens, completion_tokens = detect_injection(task)
        self.logger.info(json.dumps({
            "injection_check": "user_input",
            "is_injection": is_injection,
            "reason": reason,
            "latency_ms": round(latency_ms, 1),
            "tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }))

        if is_injection:
            blocked_message = (
                "I cannot process that request as it appears to contain instructions "
                "that conflict with my operating guidelines."
            )
            self._add_to_context({"role": "user", "content": task})
            final_response = self._format_user_response(blocked_message)
            self._add_to_context({"role": "assistant", "content": final_response})
            return final_response

        self._add_to_context({"role": "user", "content": task})

        # Agent loop
        for step in range(1, self.max_steps + 1):
            response = self._reason()

            # Check if LLM wants to use tools
            use_tools = response.get("tool_calls") and len(response["tool_calls"]) > 0

            # Check if LLM provided text response
            if response.get("text") and use_tools:
                self._add_to_context({
                    "role": "assistant",
                    "content": response["text"]
                })

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
                    self._add_to_context(result)

            # Exit condition: text response without tool calls
            if response.get("text") and not use_tools:
                final_response = self._format_user_response(response["text"])
                self._add_to_context({
                    "role": "assistant",
                    "content": final_response,
                })
                return final_response

        if self.current_turn_pending_preview is not None:
            fallback_response = self._format_user_response(
                "Please review the pending action details below."
            )
            self._add_to_context({
                "role": "assistant",
                "content": fallback_response,
            })
            return fallback_response

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
            response = agent_llm(
                self.messages,
                tools
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

            # Execute the tool
            result = self.tool_manager.execute_tool(tool_name, tool_args)

            is_injection, reason, latency_ms, total_tokens, prompt_tokens, completion_tokens = detect_injection(result)
            self.logger.info(json.dumps({
                "injection_check": "tool_result",
                "tool": tool_name,
                "is_injection": is_injection,
                "reason": reason,
                "latency_ms": round(latency_ms, 1),
                "tokens": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }))

            if is_injection:
                result = "[Tool result redacted: potential prompt injection detected in data]"
            else:
                self._record_trusted_tool_output(result)

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

    def _record_trusted_tool_output(self, tool_result: str) -> None:
        """Capture trusted pending actions and receipts from JSON tool outputs."""

        try:
            parsed = json.loads(tool_result)
        except Exception:
            return

        if not isinstance(parsed, dict):
            return

        if parsed.get("requires_confirmation"):
            if self.pending_confirmation is None:
                self.pending_confirmation = parsed
                self.current_turn_pending_preview = parsed
            return

        if parsed.get("verified_action"):
            self.current_turn_receipts.append(parsed)

    def _handle_confirmation_turn(self, task: str) -> Optional[str]:
        """Intercept explicit yes/no replies and execute pending actions exactly."""

        if self.pending_confirmation is None:
            return None

        normalized = task.strip().lower()
        self._add_to_context({"role": "user", "content": task})

        if normalized == "yes":
            try:
                receipt_text = self.tool_manager.execute_hidden_tool(
                    "_trusted_commit_action",
                    {"action_id": self.pending_confirmation["action_id"]},
                )
                receipt = json.loads(receipt_text)
                self.current_turn_receipts = [receipt]
                response = self._format_user_response("Confirmed. The pending action has been executed.")
            finally:
                self.pending_confirmation = None

            self._add_to_context({"role": "assistant", "content": response})
            return response

        if normalized == "no":
            self.pending_confirmation = None
            response = self._format_user_response("The pending action was cancelled. No changes were made.")
            self._add_to_context({"role": "assistant", "content": response})
            return response

        response = self._format_user_response(
            "A trusted pending action is waiting for confirmation. Reply exactly 'yes' to execute it or 'no' to cancel it."
        )
        self._add_to_context({"role": "assistant", "content": response})
        return response

    def _format_user_response(self, model_text: str) -> str:
        """Append a trusted pending-action and verification section to output."""

        parts = [model_text.strip()] if model_text else []

        if self.current_turn_pending_preview is not None:
            preview = self.current_turn_pending_preview
            parts.append(
                "\n".join(
                    [
                        "=== PENDING CONFIRMATION ===",
                        preview["summary"],
                        f"Action ID: {preview['action_id']}",
                        "Reply exactly 'yes' to execute or 'no' to cancel.",
                    ]
                )
            )

        verified_lines = ["=== VERIFIED ACTIONS ==="]
        if self.current_turn_receipts:
            for receipt in self.current_turn_receipts:
                verified_lines.append(
                    f"- {receipt['summary']} (receipt {receipt['receipt_id']})"
                )
        else:
            verified_lines.append("- None")

        parts.append("\n".join(verified_lines))
        return "\n\n".join(part for part in parts if part)

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

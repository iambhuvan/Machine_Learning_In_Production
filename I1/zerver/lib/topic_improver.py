"""
Topic Title Improver Library

Provides functions to generate AI-powered topic title suggestions
based on the conversation content within a Zulip topic.
"""

from typing import Any, TYPE_CHECKING
import os
import litellm
from zerver.lib.topic import messages_for_topic

if TYPE_CHECKING:
    from zerver.models import Message


def get_topic_context_messages(
    stream_id: int,
    topic_name: str,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """
    Fetches the last `limit` messages from a topic for context.
    
    Args:
        stream_id: The ID of the stream.
        topic_name: The topic name.
        limit: Maximum number of messages to fetch (default 15).
        
    Returns:
        A list of dicts: {'id': int, 'content': str, 'sender_full_name': str}
    """
    print(f"DEBUG: Fetching context messages for topic={topic_name}, limit={limit}")
    
    from zerver.models import Stream, Message
    try:
        stream = Stream.objects.get(id=stream_id)
    except Stream.DoesNotExist:
        print(f"DEBUG: Stream {stream_id} not found")
        return []

    # Get the last `limit` messages from the topic
    messages_qs = messages_for_topic(stream.realm_id, stream.recipient_id, topic_name)
    messages_qs = messages_qs.order_by('-id')[:limit]
    
    # Fetch content and sender details
    messages = Message.objects.filter(id__in=messages_qs).select_related('sender').order_by('id')
    
    result = []
    for msg in messages:
        result.append({
            'id': msg.id,
            'content': msg.content,
            'sender_full_name': msg.sender.full_name,
        })
    
    print(f"DEBUG: Found {len(result)} context messages")
    return result


def generate_topic_suggestion(
    messages: list[dict[str, Any]],
    current_topic: str,
) -> str:
    """
    Generates an AI-powered topic title suggestion based on the conversation content.
    
    Args:
        messages: A list of message dictionaries from get_topic_context_messages.
        current_topic: The current topic name.
        
    Returns:
        A string containing the suggested topic title (1-3 words).
    """
    if not messages:
        return current_topic  # No messages, return current topic unchanged
    
    # Construct the input text for the LLM
    messages_text = ""
    for msg in messages:
        messages_text += f"Sender: {msg['sender_full_name']}\nContent: {msg['content']}\n\n"

    prompt = (
        "Based on the following conversation, suggest an improved topic title.\n"
        "The title should be concise (1-3 words), descriptive, and capture the main subject.\n"
        "Only respond with the suggested title, nothing else.\n\n"
        f"Current topic: {current_topic}\n\n"
        f"Conversation:\n{messages_text}"
    )

    print("DEBUG: generate_topic_suggestion called")
    api_key = os.getenv("LITELLM_API_KEY")
    if not api_key:
        print("DEBUG: API key missing!")
        return current_topic  # Fallback to current topic if no key
    print(f"DEBUG: API Key present (ends with {api_key[-4:] if len(api_key) > 4 else '****'})")
    
    model = "gpt-3.5-turbo"
    if api_key.startswith("gsk_"):
        print("DEBUG: Detected Groq API key, switching model to groq/llama-3.3-70b-versatile")
        model = "groq/llama-3.3-70b-versatile"

    try:
        response = litellm.completion(
            model=model, 
            messages=[{"role": "user", "content": prompt}],
            api_key=api_key
        )
        suggestion = response.choices[0].message.content.strip()
        # Clean up the suggestion (remove quotes if present)
        suggestion = suggestion.strip('"\'')
        return suggestion
    except Exception as e:
        print(f"DEBUG: litellm exception: {e}")
        return current_topic  # Fallback to current topic on error


def confirm_drift_and_suggest(
    messages: list[dict[str, Any]],
    current_topic: str,
) -> tuple[bool, str | None]:
    """
    Tier 2: Uses LiteLLM to confirm drift and suggest a new topic if confirmed.
    
    Args:
        messages: A list of message dictionaries (last 5 messages).
        current_topic: The current topic name.
        
    Returns:
        A tuple of (is_drifted: bool, suggested_topic: str | None).
        If not drifted, suggested_topic is None.
    """
    if not messages:
        return (False, None)
    
    # Construct the input text for the LLM
    messages_text = ""
    for msg in messages:
        messages_text += f"Sender: {msg['sender_full_name']}\nContent: {msg['content']}\n\n"

    prompt = (
        "Analyze the following conversation and determine if it has drifted from the original topic.\n\n"
        f"Current topic title: {current_topic}\n\n"
        f"Recent messages:\n{messages_text}\n"
        "Instructions:\n"
        "1. Analyze the following short messages. Even if the messages are single words or brief phrases, determine if the subject has shifted.\n"
        "2. If the conversation is still about the topic, respond with: NO_DRIFT\n"
        "3. If the conversation has drifted to a new subject, respond with: DRIFT:<new_topic_suggestion>\n"
        "   The suggestion should be 1-3 words describing the new subject.\n\n"
        "Respond with ONLY 'NO_DRIFT' or 'DRIFT:<suggestion>', nothing else."
    )

    print("DEBUG: confirm_drift_and_suggest called")
    api_key = os.getenv("LITELLM_API_KEY")
    if not api_key:
        print("DEBUG: API key missing!")
        return (False, None)
    
    model = "gpt-3.5-turbo"
    if api_key.startswith("gsk_"):
        print("DEBUG: Detected Groq API key, switching model")
        model = "groq/llama-3.3-70b-versatile"

    try:
        response = litellm.completion(
            model=model, 
            messages=[{"role": "user", "content": prompt}],
            api_key=api_key
        )
        result = response.choices[0].message.content.strip()
        print(f"DEBUG: AI drift check result: {result}")
        
        if result.upper() == "NO_DRIFT":
            return (False, None)
        elif result.upper().startswith("DRIFT:"):
            suggestion = result[6:].strip().strip('"\'')
            return (True, suggestion)
        else:
            # Unexpected format, assume no drift
            print(f"DEBUG: Unexpected AI response format: {result}")
            return (False, None)
    except Exception as e:
        print(f"DEBUG: litellm exception in drift check: {e}")
        return (False, None)

from typing import Any
import os
import litellm
from zerver.models import UserProfile, Realm, Message
from zerver.lib.narrow import fetch_messages, NarrowParameter

def get_unread_recap_messages(
    user_profile: UserProfile,
    stream_name: str,
    topic_name: str,
    num_before: int = 0,
    num_after: int = 1000,
) -> list[dict[str, Any]]:
    """
    Retrieves unread messages for a specific user in a specific stream topic.
    Returns a list of dictionaries containing message details including raw content.
    
    Args:
        user_profile: The user for whom to fetch unread messages.
        stream_name: The name of the stream.
        topic_name: The topic within the stream.
        num_before: Number of messages before the anchor.
        num_after: Number of messages to fetch.
        
    Returns:
        A list of dicts: {'id': int, 'content': str, 'sender_full_name': str, 'timestamp': datetime}
    """
    
    print(f"DEBUG: Fetching unread messages for stream={stream_name}, topic={topic_name}")
    narrow = [
        NarrowParameter(operator="stream", operand=stream_name),
        NarrowParameter(operator="topic", operand=topic_name),
        NarrowParameter(operator="is", operand="unread"),
    ]
    
    anchor_info = {"type": "first_unread", "value": None}
    
    result = fetch_messages(
        narrow=narrow,
        user_profile=user_profile,
        realm=user_profile.realm,
        is_web_public_query=False,
        anchor_info=anchor_info,
        include_anchor=True,
        num_before=num_before,
        num_after=num_after,
    )
    
    # result.rows is a list of tuples where row[0] is the message_id
    message_ids = [row[0] for row in result.rows]
    print(f"DEBUG: Found {len(message_ids)} unread messages")
    
    if not message_ids:
        # Fallback removed per user request. Return empty list if no unread messages.
        return []
        
    # Fetch content and other details
    messages = Message.objects.filter(id__in=message_ids).values(
        'id', 'content', 'date_sent', 'sender__full_name'
    )
    
    # Ensure preservation of order if needed, though dict ordering usually matches DB if ordered by ID.
    # We can create a map and reorder based on message_ids list.
    message_map = {m['id']: m for m in messages}
    
    ordered_messages = []
    for mid in message_ids:
        if mid in message_map:
            m = message_map[mid]
            ordered_messages.append({
                'id': m['id'],
                'content': m['content'],
                'sender_full_name': m['sender__full_name'],
                'timestamp': m['date_sent']
            })
            
    return ordered_messages

def generate_ai_recap(messages: list[dict[str, Any]]) -> str:
    """
    Generates a concise bulleted summary of the provided messages using an LLM.
    Each summary point includes a clickable link to the original message.
    
    Args:
        messages: A list of message dictionaries returned by get_unread_recap_messages.
        
    Returns:
        A string containing the AI-generated summary.
    """
    if not messages:
        return "You are all caught up! There are no unread messages to summarize."

    # Construct the input text for the LLM
    messages_text = ""
    for msg in messages:
        messages_text += f"ID: {msg['id']}\nSender: {msg['sender_full_name']}\nContent: {msg['content']}\n\n"

    prompt = (
        "Summarize the following conversation completely. Ensure every distinct point discussed in the unread messages is represented, and attach the correct message link [#@<id>](#narrow/id/<id>) to every summary point.\n\n"
        f"Messages:\n{messages_text}"
    )

    print("DEBUG: generate_ai_recap called")
    api_key = os.getenv("LITELLM_API_KEY")
    if not api_key:
        print("DEBUG: API key missing!")
        return "Error: API key not found. Please set LITELLM_API_KEY or OPENAI_API_KEY."
    print(f"DEBUG: API Key present (ends with {api_key[-4:] if len(api_key)>4 else '****'})")
    
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
        return response.choices[0].message.content
    except Exception as e:
        print(f"DEBUG: litellm exception: {e}")
        return f"Error generating summary: {str(e)}"

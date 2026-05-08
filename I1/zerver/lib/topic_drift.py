"""
Topic Drift Detection Library

Provides functions to detect when a conversation has drifted from its original topic.
Uses a two-tier approach: fast FTS filtering followed by AI confirmation.
"""

import re
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from zerver.models import Message


# Common words to ignore when extracting topic keywords
STOP_WORDS = {
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'can', 'to', 'of', 'in', 'for',
    'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
    'before', 'after', 'above', 'below', 'between', 'under', 'again',
    'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
    'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
    'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    's', 't', 'just', 'don', 'now', 'and', 'but', 'or', 'if', 'this', 'that',
    'these', 'those', 'what', 'which', 'who', 'whom', 're', 'about', 'up',
}

# Resolved topic prefix to strip
RESOLVED_PREFIX = "✔ "


def extract_topic_keywords(topic_name: str) -> set[str]:
    """
    Extracts meaningful keywords from a topic title.
    
    Args:
        topic_name: The topic title string.
        
    Returns:
        A set of lowercase keyword strings.
    """
    # Remove resolved prefix if present
    if topic_name.startswith(RESOLVED_PREFIX):
        topic_name = topic_name[len(RESOLVED_PREFIX):]
    
    # Lowercase and extract words (alphanumeric sequences)
    words = re.findall(r'[a-zA-Z0-9]+', topic_name.lower())
    
    # Filter out stop words and very short words (allow 2-letter words like AI, Go, JS)
    keywords = {w for w in words if w not in STOP_WORDS and len(w) >= 2}
    
    return keywords


def check_for_potential_drift(message: "Message") -> bool:
    """
    Fast Tier 1 check using FTS tokens to detect potential topic drift.
    
    This function checks if ANY of the topic's keywords appear in the
    message content. If NONE of the keywords appear, we suspect drift.
    
    Args:
        message: The Message object to check.
        
    Returns:
        True if potential drift is detected (no topic keywords in message).
        False if the message seems on-topic.
    """
    # Only check channel messages
    if not message.is_channel_message:
        return False
    
    topic_name = message.topic_name()
    topic_keywords = extract_topic_keywords(topic_name)
    
    # If topic has no meaningful keywords, we can't detect drift
    if not topic_keywords:
        print(f"DEBUG: Topic '{topic_name}' has no extractable keywords")
        return False
    
    return detect_drift_in_content(message.content, topic_keywords)


def detect_drift_in_content(content: str, topic_keywords: set[str]) -> bool:
    """
    Checks if the content matches the topic keywords.
    Returns True if drift is suspected (no keywords found).
    """
    # Get the message content (lowercase for comparison)
    content_lower = content.lower()
    
    # Check if ANY topic keyword appears in the message content
    for keyword in topic_keywords:
        if keyword in content_lower:
            # print(f"DEBUG: Keyword '{keyword}' found in message, no drift")
            return False
            
    # No keywords found - potential drift
    # print(f"DEBUG: No topic keywords {topic_keywords} found in message, potential drift detected")
    return True


def should_check_drift(message: "Message", min_messages_in_topic: int = 3) -> bool:
    """
    Determines if we should run drift detection on this message.
    
    We only check drift after the topic has established context (min messages).
    
    Args:
        message: The Message object.
        min_messages_in_topic: Minimum messages before we start checking drift.
        
    Returns:
        True if drift check should be performed.
    """
    # Only for channel messages
    if not message.is_channel_message:
        return False
    
    # Don't check bot messages
    if message.sender.is_bot:
        return False
    
    # Count messages in this topic (simple check)
    # Note: This is a simplified check; in production you might cache this
    from zerver.lib.topic import messages_for_topic
    
    topic_message_count = messages_for_topic(
        message.realm_id,
        message.recipient_id,
        message.topic_name()
    ).count()
    
    return topic_message_count >= min_messages_in_topic

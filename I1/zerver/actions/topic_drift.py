"""
Topic Drift Detection Actions

Provides functions to trigger topic drift detection after message sending.
"""

from zerver.lib.queue import queue_json_publish_rollback_unsafe
from zerver.lib.topic_drift import check_for_potential_drift, should_check_drift
from zerver.models import Message


def maybe_queue_topic_drift_check(message: Message) -> bool:
    """
    Checks if topic drift detection should be triggered for this message.
    If Tier 1 filter detects potential drift, queues a background task for Tier 2 confirmation.
    
    Args:
        message: The newly sent Message object.
        
    Returns:
        True if a drift check was queued, False otherwise.
    """
    # First check if we should even run drift detection
    if not should_check_drift(message):
        return False
    
    # Tier 1: Fast FTS-based check
    if not check_for_potential_drift(message):
        return False
    
    # Potential drift detected - queue background task for Tier 2
    print(f"DEBUG: Queueing topic drift check for message {message.id}")
    
    # Get stream_id from recipient
    from zerver.models import Stream
    stream = Stream.objects.filter(recipient_id=message.recipient_id).first()
    stream_id = stream.id if stream else 0
    
    event = {
        "type": "check_topic_drift",
        "message_id": message.id,
        "sender_id": message.sender_id,
        "realm_id": message.realm_id,
        "stream_recipient_id": message.recipient_id,
        "topic_name": message.topic_name(),
        "stream_id": stream_id,
    }
    
    queue_json_publish_rollback_unsafe("deferred_work", event)
    return True

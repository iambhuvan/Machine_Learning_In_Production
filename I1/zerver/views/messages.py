from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext as _
from pydantic import Json

from zerver.lib.message_recap import get_unread_recap_messages, generate_ai_recap
from zerver.lib.topic_improver import get_topic_context_messages, generate_topic_suggestion
from zerver.lib.response import json_success
from zerver.lib.typed_endpoint import typed_endpoint
from zerver.lib.streams import access_stream_by_name, access_stream_by_id
from zerver.models import UserProfile
from zerver.lib.exceptions import JsonableError

@typed_endpoint
def get_recap(
    request: HttpRequest,
    user_profile: UserProfile,
    *,
    stream_name: str,
    topic_name: str,
) -> HttpResponse:
    
    # 1. Verify access to stream (is user subscribed or is it public?)
    # access_stream_by_name gives us the stream object and validates access
    stream, sub = access_stream_by_name(user_profile, stream_name)
    
    # 2. Get unread messages
    messages = get_unread_recap_messages(
        user_profile=user_profile,
        stream_name=stream_name,
        topic_name=topic_name
    )
    
    # 3. Generate AI summary
    recap_text = generate_ai_recap(messages)
    
    return json_success(request, data={"recap": recap_text})


@typed_endpoint
def get_topic_suggestion(
    request: HttpRequest,
    user_profile: UserProfile,
    *,
    stream_id: Json[int],
    topic_name: str,
) -> HttpResponse:
    """
    Returns an AI-generated topic title suggestion based on conversation content.
    """
    # 1. Verify access to stream
    stream, sub = access_stream_by_id(user_profile, stream_id)
    
    if stream.recipient_id is None:
        raise JsonableError(_("Invalid stream"))
    
    # 2. Get context messages (last 15 messages regardless of read status)
    messages = get_topic_context_messages(
        stream_id=stream.id,
        topic_name=topic_name,
        limit=3,
    )
    
    if not messages:
        return json_success(request, data={"suggestion": topic_name})
    
    # 3. Generate AI suggestion
    suggestion = generate_topic_suggestion(messages, topic_name)
    
    return json_success(request, data={"suggestion": suggestion})

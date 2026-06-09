"""Chat Context preparation for LLM inference."""

import logging
from typing import Optional
from services.conversation_manager import ConversationManager
from config import get_config

logger = logging.getLogger(__name__)


def build_chat_context(
    conversation_id: int,
    model_name: Optional[str] = None,
    max_tokens: int = 4096,
) -> tuple:
    """
    Fetch, optionally compress, and format a Conversation's Messages for Backend inference.

    Returns (formatted_messages, context_metadata). formatted_messages is a list of
    {role, content} dicts ready for any LLMInterface.generate_response() call.
    Summary Messages produced by Compression are promoted to the 'system' role.
    """
    messages = ConversationManager.get_messages(conversation_id)

    if not model_name:
        conversation = ConversationManager.get_conversation(conversation_id)
        if conversation:
            model_name = conversation['model']

    compression_cfg = get_config().get('compression', {})
    if compression_cfg.get('enabled', False):
        from services.context_compressor import get_context_compressor
        compressed_messages, compression_metadata = get_context_compressor().compress_context(
            messages=messages,
            conversation_id=conversation_id,
            model_name=model_name,
            max_context_tokens=max_tokens,
        )
    else:
        compressed_messages, compression_metadata = messages, None

    formatted = []
    for msg in compressed_messages:
        if msg.get('is_summary', False):
            formatted.append({'role': 'system', 'content': msg['content']})
        else:
            formatted.append({'role': msg['role'], 'content': msg['content']})

    context_metadata = {
        'conversation_id': conversation_id,
        'message_count': len(formatted),
        'compression_applied': (
            compression_metadata is not None
            and compression_metadata.get('compression_applied', False)
        ),
        'compression_metadata': compression_metadata,
        'context_optimized': True,
    }

    logger.debug(
        "Built chat context for conversation %s: %d messages, compression=%s",
        conversation_id, len(formatted), context_metadata['compression_applied'],
    )

    return formatted, context_metadata

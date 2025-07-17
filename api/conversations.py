"""Conversation API routes for Chat-O-Llama."""

import os
import logging
from flask import request, jsonify, Blueprint
from services.conversation_manager import ConversationManager
from services.llm_factory import get_active_backend
from utils.database import get_db

logger = logging.getLogger(__name__)

OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')

conversations_bp = Blueprint('conversations', __name__)


@conversations_bp.route('/api/conversations')
def api_conversations():
    """Get all conversations."""
    conversations = ConversationManager.get_conversations()
    return jsonify({
        'conversations': [dict(conv) for conv in conversations]
    })


@conversations_bp.route('/api/conversations', methods=['POST'])
def api_create_conversation():
    """Create new conversation."""
    data = request.get_json()
    title = data.get('title', 'New Chat')
    model = data.get('model', 'llama3.2')

    # Get current backend type
    try:
        backend = get_active_backend()
        backend_info = backend.get_backend_info()
        backend_type = str(backend_info.get('backend_type', 'ollama'))  # Ensure it's a string
    except Exception as e:
        logger.warning(f"Could not get backend type: {e}, defaulting to 'ollama'")
        backend_type = 'ollama'

    conv_id = ConversationManager.create_conversation(title, model, backend_type)
    return jsonify({'conversation_id': conv_id})


@conversations_bp.route('/api/conversations/<int:conversation_id>')
def api_get_conversation(conversation_id):
    """Get conversation with messages and stats."""
    conversation = ConversationManager.get_conversation(conversation_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    messages = ConversationManager.get_messages(conversation_id)
    stats = ConversationManager.get_conversation_stats(conversation_id)
    
    return jsonify({
        'conversation': dict(conversation),
        'messages': [dict(msg) for msg in messages],
        'stats': stats
    })


@conversations_bp.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
def api_delete_conversation(conversation_id):
    """Delete conversation."""
    ConversationManager.delete_conversation(conversation_id)
    return jsonify({'success': True})


@conversations_bp.route('/api/conversations/<int:conversation_id>', methods=['PUT'])
def api_update_conversation(conversation_id):
    """Update conversation (rename)."""
    data = request.get_json()
    new_title = data.get('title', '').strip()

    if not new_title:
        return jsonify({'error': 'Title cannot be empty'}), 400

    if len(new_title) > 100:
        return jsonify({'error': 'Title too long (max 100 characters)'}), 400

    # Update the conversation title
    db = get_db()
    result = db.execute(
        'UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (new_title, conversation_id)
    )
    db.commit()

    if result.rowcount == 0:
        return jsonify({'error': 'Conversation not found'}), 404

    return jsonify({'success': True, 'title': new_title})


@conversations_bp.route('/api/search')
def api_search():
    """Search conversations and messages."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'results': []})

    db = get_db()
    results = db.execute('''
        SELECT DISTINCT c.id, c.title, c.model, c.updated_at,
               m.content, m.role, m.timestamp, m.response_time_ms, m.estimated_tokens
        FROM conversations c
        JOIN messages m ON c.id = m.conversation_id
        WHERE m.content LIKE ? OR c.title LIKE ?
        ORDER BY c.updated_at DESC
        LIMIT 50
    ''', (f'%{query}%', f'%{query}%')).fetchall()

    return jsonify({
        'results': [dict(result) for result in results]
    })


@conversations_bp.route('/api/stats/<int:conversation_id>')
def api_conversation_stats(conversation_id):
    """Get detailed statistics for a conversation."""
    stats = ConversationManager.get_conversation_stats(conversation_id)
    
    # Get additional detailed stats
    db = get_db()
    detailed_stats = db.execute('''
        SELECT 
            role,
            COUNT(*) as count,
            AVG(LENGTH(content)) as avg_length,
            SUM(estimated_tokens) as total_tokens,
            AVG(response_time_ms) as avg_response_time
        FROM messages 
        WHERE conversation_id = ?
        GROUP BY role
    ''', (conversation_id,)).fetchall()
    
    return jsonify({
        'summary': stats,
        'by_role': [dict(stat) for stat in detailed_stats]
    })
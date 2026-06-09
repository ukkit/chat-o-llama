"""Conversation storage and retrieval for Chat-O-Llama."""

import logging
from typing import List, Dict
from utils.database import get_db


logger = logging.getLogger(__name__)


class ConversationManager:
    """Manage conversations and messages with enhanced metrics."""

    @staticmethod
    def create_conversation(title, model, backend_type='ollama'):
        """Create a new conversation."""
        db = get_db()
        cursor = db.execute(
            'INSERT INTO conversations (title, model, backend_type) VALUES (?, ?, ?)',
            (title, model, backend_type)
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_conversations():
        """Get all conversations ordered by last update."""
        db = get_db()
        return db.execute(
            'SELECT * FROM conversations ORDER BY updated_at DESC'
        ).fetchall()

    @staticmethod
    def get_conversation(conversation_id):
        """Get conversation by ID."""
        db = get_db()
        return db.execute(
            'SELECT * FROM conversations WHERE id = ?',
            (conversation_id,)
        ).fetchone()

    @staticmethod
    def update_conversation_timestamp(conversation_id):
        """Update conversation timestamp."""
        db = get_db()
        db.execute(
            'UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (conversation_id,)
        )
        db.commit()

    @staticmethod
    def delete_conversation(conversation_id):
        """Delete conversation and all messages."""
        db = get_db()
        db.execute('DELETE FROM conversations WHERE id = ?',
                   (conversation_id,))
        db.commit()

    @staticmethod
    def add_message(conversation_id, role, content, model=None, response_time_ms=None, estimated_tokens=None, backend_type='ollama'):
        """Add message to conversation with metrics."""
        db = get_db()
        db.execute(
            'INSERT INTO messages (conversation_id, role, content, model, response_time_ms, estimated_tokens, backend_type) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (conversation_id, role, content, model, response_time_ms, estimated_tokens, backend_type)
        )
        db.commit()
        ConversationManager.update_conversation_timestamp(conversation_id)

    @staticmethod
    def get_messages(conversation_id) -> List[Dict]:
        """Get all raw Messages for a Conversation, ordered by timestamp."""
        db = get_db()
        rows = db.execute(
            'SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp',
            (conversation_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_conversation_stats(conversation_id):
        """Get conversation statistics."""
        db = get_db()
        stats = db.execute('''
            SELECT 
                COUNT(*) as total_messages,
                COUNT(CASE WHEN role = 'assistant' THEN 1 END) as assistant_messages,
                AVG(CASE WHEN role = 'assistant' AND response_time_ms IS NOT NULL THEN response_time_ms END) as avg_response_time,
                SUM(CASE WHEN role = 'assistant' AND estimated_tokens IS NOT NULL THEN estimated_tokens END) as total_tokens
            FROM messages 
            WHERE conversation_id = ?
        ''', (conversation_id,)).fetchone()
        
        return dict(stats) if stats else {}
    

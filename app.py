#!/usr/bin/env python3
"""
Ollama Chat Frontend with History Storage
A Flask web application for chatting with Ollama models with persistent history.
"""

import os
import sqlite3
import requests
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, g
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'

# Configuration
OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'ollama_chat.db')

# Database schema
SCHEMA = '''
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    model TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
'''


def get_db():
    """Get database connection."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(error):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database with schema."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    logger.info(f"Database initialized: {DATABASE_PATH}")


@app.teardown_appcontext
def close_db_on_teardown(error):
    close_db(error)


class OllamaAPI:
    """Ollama API client."""

    @staticmethod
    def get_models():
        """Get available models from Ollama."""
        try:
            print(f"Attempting to fetch models from {OLLAMA_API_URL}/api/tags")
            response = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=10)

            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                model_names = [model['name']
                               for model in models if 'name' in model]
                print(
                    f"Successfully fetched {len(model_names)} models: {model_names}")
                return model_names
            else:
                print(
                    f"Ollama API returned status {response.status_code}: {response.text}")
                return []

        except requests.exceptions.ConnectionError as e:
            print(f"Connection error to Ollama: {e}")
            print("Make sure Ollama is running with: ollama serve")
            return []
        except requests.exceptions.Timeout as e:
            print(f"Timeout connecting to Ollama: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching models: {e}")
            return []

    @staticmethod
    def generate_response(model, prompt, conversation_history=None):
        """Generate response from Ollama."""
        try:
            # Define your system personality here
            system_prompt = """Your name is Bhaai, a helpful, friendly, and knowledgeable AI assistant . You have a warm personality and enjoy helping users solve problems. You're curious about technology and always try to provide practical, actionable advice. You occasionally use light humor when appropriate, but remain professional and focused on being genuinely helpful."""

            # Build context from conversation history
            context = f"{system_prompt}\n\n"

            if conversation_history:
                # Last 10 messages for context
                for msg in conversation_history[-10:]:
                    role = "Human" if msg['role'] == 'user' else "Assistant"
                    context += f"{role}: {msg['content']}\n"

            full_prompt = f"{context}Human: {prompt}\nAssistant:"

            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40
                }
            }

            response = requests.post(
                f"{OLLAMA_API_URL}/api/generate",
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('response', 'No response generated')
            else:
                return f"Error: HTTP {response.status_code}"

        except requests.RequestException as e:
            logger.error(f"Ollama API error: {e}")
            return f"Error connecting to Ollama: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return f"Unexpected error: {str(e)}"


class ConversationManager:
    """Manage conversations and messages."""

    @staticmethod
    def create_conversation(title, model):
        """Create a new conversation."""
        db = get_db()
        cursor = db.execute(
            'INSERT INTO conversations (title, model) VALUES (?, ?)',
            (title, model)
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
    def add_message(conversation_id, role, content, model=None):
        """Add message to conversation."""
        db = get_db()
        db.execute(
            'INSERT INTO messages (conversation_id, role, content, model) VALUES (?, ?, ?, ?)',
            (conversation_id, role, content, model)
        )
        db.commit()
        ConversationManager.update_conversation_timestamp(conversation_id)

    @staticmethod
    def get_messages(conversation_id):
        """Get all messages for a conversation."""
        db = get_db()
        return db.execute(
            'SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp',
            (conversation_id,)
        ).fetchall()

# Routes


@app.route('/')
def index():
    """Main chat interface."""
    return render_template('index.html')


@app.route('/api/models')
def api_models():
    """Get available models."""
    try:
        models = OllamaAPI.get_models()
        return jsonify({
            'models': models,
            'count': len(models),
            'ollama_url': OLLAMA_API_URL
        })
    except Exception as e:
        logger.error(f"Error in /api/models endpoint: {e}")
        return jsonify({
            'models': [],
            'count': 0,
            'error': str(e),
            'ollama_url': OLLAMA_API_URL
        }), 500


@app.route('/api/conversations')
def api_conversations():
    """Get all conversations."""
    conversations = ConversationManager.get_conversations()
    return jsonify({
        'conversations': [dict(conv) for conv in conversations]
    })


@app.route('/api/conversations', methods=['POST'])
def api_create_conversation():
    """Create new conversation."""
    data = request.get_json()
    title = data.get('title', 'New Chat')
    model = data.get('model', 'llama3.2')

    conv_id = ConversationManager.create_conversation(title, model)
    return jsonify({'conversation_id': conv_id})


@app.route('/api/conversations/<int:conversation_id>')
def api_get_conversation(conversation_id):
    """Get conversation with messages."""
    conversation = ConversationManager.get_conversation(conversation_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    messages = ConversationManager.get_messages(conversation_id)
    return jsonify({
        'conversation': dict(conversation),
        'messages': [dict(msg) for msg in messages]
    })


@app.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
def api_delete_conversation(conversation_id):
    """Delete conversation."""
    ConversationManager.delete_conversation(conversation_id)
    return jsonify({'success': True})


@app.route('/api/conversations/<int:conversation_id>', methods=['PUT'])
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


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Send message and get response."""
    data = request.get_json()
    conversation_id = data.get('conversation_id')
    message = data.get('message')
    model = data.get('model', 'llama3.2')

    if not conversation_id or not message:
        return jsonify({'error': 'Missing conversation_id or message'}), 400

    # Add user message
    ConversationManager.add_message(conversation_id, 'user', message)

    # Get conversation history for context
    messages = ConversationManager.get_messages(conversation_id)
    history = [{'role': msg['role'], 'content': msg['content']}
               for msg in messages[:-1]]

    # Generate response
    response = OllamaAPI.generate_response(model, message, history)

    # Add assistant response
    ConversationManager.add_message(
        conversation_id, 'assistant', response, model)

    return jsonify({
        'response': response,
        'model': model
    })


@app.route('/api/search')
def api_search():
    """Search conversations and messages."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'results': []})

    db = get_db()
    results = db.execute('''
        SELECT DISTINCT c.id, c.title, c.model, c.updated_at,
               m.content, m.role, m.timestamp
        FROM conversations c
        JOIN messages m ON c.id = m.conversation_id
        WHERE m.content LIKE ? OR c.title LIKE ?
        ORDER BY c.updated_at DESC
        LIMIT 50
    ''', (f'%{query}%', f'%{query}%')).fetchall()

    return jsonify({
        'results': [dict(result) for result in results]
    })


if __name__ == '__main__':
    # Initialize database
    init_db()

    # Check Ollama connection
    models = OllamaAPI.get_models()
    if models:
        logger.info(f"Connected to Ollama. Available models: {models}")
    else:
        logger.warning("Could not connect to Ollama or no models available")

    # Run the app
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8080)),  # Changed default from 5000 to 8080
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )

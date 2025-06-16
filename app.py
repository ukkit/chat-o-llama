#!/usr/bin/env python3
"""
Ollama Chat Frontend with History Storage
A Flask web application for chatting with Ollama models with persistent history.
Enhanced with response metrics tracking.
"""

import os
import sqlite3
import requests
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, g
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# For future use
app.config['SECRET_KEY'] = 'your-secret-key-change-this'

# Enable threading for better performance
app.config['THREADED'] = True

# Load configuration from JSON file
def load_config():
    """Load configuration from config.json file."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info("Configuration loaded from config.json")
        return config
    except FileNotFoundError:
        logger.warning(
            f"Config file not found at {config_path}, using defaults")
        return get_default_config()
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}, using defaults")
        return get_default_config()


def get_default_config():
    """Get default configuration if config.json is not available."""
    return {
        "timeouts": {
            "ollama_timeout": 180,
            "ollama_connect_timeout": 15
        },
        "model_options": {
            "temperature": 0.5,
            "top_p": 0.8,
            "top_k": 30,
            "num_predict": 2048,
            "num_ctx": 4096,
            "repeat_penalty": 1.1,
            "stop": ["\n\nHuman:", "\n\nUser:"]
        },
        "performance": {
            "context_history_limit": 10,
            "batch_size": 1,
            "use_mlock": True,
            "use_mmap": True,
            "num_thread": -1,
            "num_gpu": 0
        },
        "system_prompt": "Your name is Bhaai, a helpful, friendly, and knowledgeable AI assistant. You have a warm personality and enjoy helping users solve problems. You're curious about technology and always try to provide practical, actionable advice. You occasionally use light humor when appropriate, but remain professional and focused on being genuinely helpful.",
        "response_optimization": {
            "stream": False,
            "keep_alive": "5m",
            "low_vram": False,
            "f16_kv": True,
            "logits_all": False,
            "vocab_only": False,
            "use_mmap": True,
            "use_mlock": False,
            "embedding_only": False,
            "numa": False
        }
    }


# Load configuration
CONFIG = load_config()

# Configuration
OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'ollama_chat.db')
OLLAMA_TIMEOUT = CONFIG['timeouts']['ollama_timeout']
OLLAMA_CONNECT_TIMEOUT = CONFIG['timeouts']['ollama_connect_timeout']

# Enhanced database schema with metrics tracking
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
    response_time_ms INTEGER,
    estimated_tokens INTEGER,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
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


def estimate_tokens(text):
    """Estimate token count based on character length."""
    # Rough estimation: ~4 characters per token for English text
    return max(1, len(text) // 4)


class OllamaAPI:
    """Ollama API client with enhanced metrics tracking."""

    @staticmethod
    def get_models():
        """Get available models from Ollama."""
        try:
            print(f"Attempting to fetch models from {OLLAMA_API_URL}/api/tags")
            response = requests.get(
                f"{OLLAMA_API_URL}/api/tags",
                timeout=(OLLAMA_CONNECT_TIMEOUT, 30)
            )

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
        """Generate response from Ollama with timing metrics."""
        start_time = time.time()
        
        try:
            # Get system prompt from config
            system_prompt = CONFIG['system_prompt']

            # Build context from conversation history
            context = f"{system_prompt}\n\n"

            if conversation_history:
                # Use configurable history limit
                history_limit = CONFIG['performance']['context_history_limit']
                for msg in conversation_history[-history_limit:]:
                    role = "Human" if msg['role'] == 'user' else "Assistant"
                    context += f"{role}: {msg['content']}\n"

            full_prompt = f"{context}Human: {prompt}\nAssistant:"

            # Build payload with all configuration options
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": CONFIG['response_optimization']['stream'],
                "options": {
                    # Model generation options from config
                    "temperature": CONFIG['model_options']['temperature'],
                    "top_p": CONFIG['model_options']['top_p'],
                    "top_k": CONFIG['model_options']['top_k'],
                    "num_predict": CONFIG['model_options']['num_predict'],
                    "num_ctx": CONFIG['model_options']['num_ctx'],
                    "repeat_penalty": CONFIG['model_options']['repeat_penalty'],
                    "stop": CONFIG['model_options']['stop'],

                    # Performance optimization options
                    "num_thread": CONFIG['performance']['num_thread'],
                    "num_gpu": CONFIG['performance']['num_gpu'],
                    "use_mlock": CONFIG['performance']['use_mlock'],
                    "use_mmap": CONFIG['performance']['use_mmap'],

                    # Response optimization options
                    "f16_kv": CONFIG['response_optimization']['f16_kv'],
                    "logits_all": CONFIG['response_optimization']['logits_all'],
                    "vocab_only": CONFIG['response_optimization']['vocab_only'],
                    "embedding_only": CONFIG['response_optimization']['embedding_only'],
                    "numa": CONFIG['response_optimization']['numa'],
                },
                "keep_alive": CONFIG['response_optimization']['keep_alive']
            }

            # Add low_vram option if enabled
            if CONFIG['response_optimization']['low_vram']:
                payload['options']['low_vram'] = True

            response = requests.post(
                f"{OLLAMA_API_URL}/api/generate",
                json=payload,
                timeout=(OLLAMA_CONNECT_TIMEOUT, OLLAMA_TIMEOUT)
            )

            # Calculate response time
            response_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds

            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', 'No response generated')
                
                # Estimate tokens
                estimated_tokens = estimate_tokens(response_text)
                
                # Try to get actual token counts from response if available
                if 'eval_count' in data:
                    estimated_tokens = data['eval_count']
                
                return {
                    'response': response_text,
                    'response_time_ms': response_time,
                    'estimated_tokens': estimated_tokens,
                    'eval_count': data.get('eval_count'),
                    'eval_duration': data.get('eval_duration'),
                    'load_duration': data.get('load_duration'),
                    'prompt_eval_count': data.get('prompt_eval_count'),
                    'prompt_eval_duration': data.get('prompt_eval_duration'),
                    'total_duration': data.get('total_duration')
                }
            else:
                return {
                    'response': f"Error: HTTP {response.status_code}",
                    'response_time_ms': response_time,
                    'estimated_tokens': 0
                }

        except requests.exceptions.ReadTimeout as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(
                f"Ollama read timeout after {OLLAMA_TIMEOUT} seconds: {e}")
            return {
                'response': f"Response timed out after {OLLAMA_TIMEOUT} seconds. Try a shorter prompt or increase timeout.",
                'response_time_ms': response_time,
                'estimated_tokens': 0
            }
        except requests.exceptions.ConnectTimeout as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(f"Ollama connection timeout: {e}")
            return {
                'response': "Connection to Ollama timed out. Make sure Ollama is running and accessible.",
                'response_time_ms': response_time,
                'estimated_tokens': 0
            }
        except requests.RequestException as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(f"Ollama API error: {e}")
            return {
                'response': f"Error connecting to Ollama: {str(e)}",
                'response_time_ms': response_time,
                'estimated_tokens': 0
            }
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(f"Unexpected error: {e}")
            return {
                'response': f"Unexpected error: {str(e)}",
                'response_time_ms': response_time,
                'estimated_tokens': 0
            }


class ConversationManager:
    """Manage conversations and messages with enhanced metrics."""

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
    def add_message(conversation_id, role, content, model=None, response_time_ms=None, estimated_tokens=None):
        """Add message to conversation with metrics."""
        db = get_db()
        db.execute(
            'INSERT INTO messages (conversation_id, role, content, model, response_time_ms, estimated_tokens) VALUES (?, ?, ?, ?, ?, ?)',
            (conversation_id, role, content, model, response_time_ms, estimated_tokens)
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


@app.route('/api/config')
def api_config():
    """Get current configuration (excluding sensitive data)."""
    config_display = {
        'timeouts': CONFIG['timeouts'],
        'model_options': CONFIG['model_options'],
        'performance': CONFIG['performance'],
        'response_optimization': {k: v for k, v in CONFIG['response_optimization'].items() if k != 'system_prompt'}
    }
    return jsonify(config_display)


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
    """Send message and get response with enhanced metrics."""
    data = request.get_json()
    conversation_id = data.get('conversation_id')
    message = data.get('message')
    model = data.get('model', 'llama3.2')

    if not conversation_id or not message:
        return jsonify({'error': 'Missing conversation_id or message'}), 400

    # Add user message
    user_tokens = estimate_tokens(message)
    ConversationManager.add_message(
        conversation_id, 'user', message, model, None, user_tokens
    )

    # Get conversation history for context
    messages = ConversationManager.get_messages(conversation_id)
    history = [{'role': msg['role'], 'content': msg['content']}
               for msg in messages[:-1]]

    # Generate response with metrics
    response_data = OllamaAPI.generate_response(model, message, history)

    # Add assistant response with metrics
    ConversationManager.add_message(
        conversation_id, 
        'assistant', 
        response_data['response'], 
        model,
        response_data['response_time_ms'],
        response_data['estimated_tokens']
    )

    return jsonify({
        'response': response_data['response'],
        'model': model,
        'response_time_ms': response_data['response_time_ms'],
        'estimated_tokens': response_data['estimated_tokens'],
        'metrics': {
            'eval_count': response_data.get('eval_count'),
            'eval_duration': response_data.get('eval_duration'),
            'load_duration': response_data.get('load_duration'),
            'prompt_eval_count': response_data.get('prompt_eval_count'),
            'prompt_eval_duration': response_data.get('prompt_eval_duration'),
            'total_duration': response_data.get('total_duration')
        }
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


@app.route('/api/stats/<int:conversation_id>')
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


if __name__ == '__main__':
    # Initialize database
    init_db()

    # Check Ollama connection
    models = OllamaAPI.get_models()
    if models:
        logger.info(f"Connected to Ollama. Available models: {models}")
    else:
        logger.warning("Could not connect to Ollama or no models available")

    # Log current configuration
    logger.info(f"Ollama timeout: {OLLAMA_TIMEOUT}s")
    logger.info(
        f"Context history limit: {CONFIG['performance']['context_history_limit']} messages")
    logger.info(f"Temperature: {CONFIG['model_options']['temperature']}")

    # Run the app with threading enabled
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8080)),
        debug=os.getenv('DEBUG', 'False').lower() == 'true',
        threaded=True
    )
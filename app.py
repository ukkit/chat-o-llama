#!/usr/bin/env python3
"""
Flask Chat Application with Multi-Backend Support
Integrated with BackendManagerSync for Phase 1.4 completion
"""

import os
import json
import logging
import uuid
import time
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any, List

from flask import Flask, render_template, request, jsonify, session
from werkzeug.serving import WSGIRequestHandler

# Import our new backend system
from config_manager import ConfigManager
from backends.manager import BackendManagerSync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ChatApplication:
    """Main chat application with multi-backend support"""
    
    def __init__(self, config_path: str = 'config.json'):
        """Initialize the chat application"""
        self.app = Flask(__name__)
        self.config_path = config_path
        
        # Load configuration
        try:
            self.config_manager = ConfigManager(config_path)
            logger.info("✅ Configuration loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            raise
        
        # Initialize Flask app
        self._setup_flask_app()
        
        # Initialize backend manager
        try:
            self.backend_manager = BackendManagerSync(self.config_manager.config)
            logger.info("✅ BackendManager initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize BackendManager: {e}")
            raise
        
        # Initialize database
        self._setup_database()
        
        # Setup routes
        self._setup_routes()
        
        # Perform startup health check
        self._startup_health_check()
    
    def _setup_flask_app(self):
        """Configure Flask application settings"""
        app_config = self.config_manager.get('app', default={})
        
        self.app.secret_key = app_config.get('secret_key', os.urandom(24))
        self.app.config['DEBUG'] = app_config.get('debug', False)
        
        # Disable Flask's request logging in production
        if not self.app.config['DEBUG']:
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)
    
    def _setup_database(self):
        """Initialize SQLite database with backend tracking"""
        db_config = self.config_manager.get('database', default={})
        self.db_path = db_config.get('path', 'chat_history.db')
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create conversations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        model_name TEXT,
                        backend TEXT DEFAULT 'ollama'
                    )
                ''')
                
                # Create messages table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        model_name TEXT,
                        backend TEXT DEFAULT 'ollama',
                        response_time REAL,
                        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                    )
                ''')
                
                # Create indexes for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
                    ON messages(conversation_id)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_messages_backend 
                    ON messages(backend)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_conversations_backend 
                    ON conversations(backend)
                ''')
                
                conn.commit()
                logger.info("✅ Database initialized successfully")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def _startup_health_check(self):
        """Perform health check on startup and log backend status"""
        try:
            health_status = self.backend_manager.get_health_status()
            available_backends = self.backend_manager.get_available_backends()
            
            if available_backends:
                logger.info(f"✅ Application started with backends: {', '.join(available_backends)}")
                
                # Log available models
                models = self.backend_manager.get_models()
                logger.info(f"📊 Available models: {len(models)} across {len(available_backends)} backends")
                
                # Log model details
                if models:
                    model_counts = {}
                    for model in models:
                        # Extract backend from model name if it follows pattern "model (backend)"
                        if " (" in model and model.endswith(")"):
                            backend = model.split(" (")[-1][:-1]
                            model_counts[backend] = model_counts.get(backend, 0) + 1
                    
                    for backend, count in model_counts.items():
                        logger.info(f"   {backend}: {count} models")
                        
            else:
                logger.warning("⚠️  No backends available on startup")
                logger.info("💡 Make sure Ollama/llama.cpp services are running")
                
        except Exception as e:
            logger.error(f"❌ Startup health check failed: {e}")
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main chat interface"""
            return render_template('index.html')
        
        @self.app.route('/api/models', methods=['GET'])
        def get_models():
            """Get available models from all backends with backend information"""
            try:
                models = self.backend_manager.get_models()
                available_backends = self.backend_manager.get_available_backends()
                
                # Transform models to include backend information
                enhanced_models = []
                for model in models:
                    # Parse backend from model name if it follows pattern "model (backend)"
                    if " (" in model and model.endswith(")"):
                        parts = model.rsplit(" (", 1)
                        model_name = parts[0]
                        backend = parts[1][:-1]
                    else:
                        model_name = model
                        backend = "unknown"
                    
                    enhanced_models.append({
                        'name': model_name,
                        'backend': backend,
                        'display_name': model,
                        'available': backend in available_backends
                    })
                
                return jsonify({
                    'success': True,
                    'models': enhanced_models,
                    'backend_count': len(available_backends),
                    'total_models': len(models)
                })
                
            except Exception as e:
                logger.error(f"Error fetching models: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to fetch models: {str(e)}'
                }), 500
        
        @self.app.route('/api/backends', methods=['GET'])
        def get_backends():
            """Get backend health status and information"""
            try:
                health_status = self.backend_manager.get_health_status()
                available_backends = self.backend_manager.get_available_backends()
                
                backend_info = {}
                for backend_name, health in health_status.items():
                    backend_config = self.config_manager.get_backend_config(backend_name)
                    
                    backend_info[backend_name] = {
                        'available': backend_name in available_backends,
                        'health': health,
                        'url': backend_config.url if backend_config else 'Unknown',
                        'type': backend_config.__class__.__name__ if backend_config else 'Unknown',
                        'enabled': backend_config.enabled if backend_config else False
                    }
                
                return jsonify({
                    'success': True,
                    'backends': backend_info,
                    'available_count': len(available_backends),
                    'total_count': len(backend_info)
                })
                
            except Exception as e:
                logger.error(f"Error fetching backend status: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to fetch backend status: {str(e)}'
                }), 500
        
        @self.app.route('/api/chat', methods=['POST'])
        def chat():
            """Enhanced chat endpoint with backend routing and model selection"""
            try:
                data = request.get_json()
                
                # Extract request parameters
                message = data.get('message', '').strip()
                model_name = data.get('model', '').strip()
                conversation_id = data.get('conversation_id')
                
                # Validation
                if not message:
                    return jsonify({
                        'success': False,
                        'error': 'Message cannot be empty'
                    }), 400
                
                if not model_name:
                    return jsonify({
                        'success': False,
                        'error': 'Model must be specified'
                    }), 400
                
                # Generate conversation ID if not provided
                if not conversation_id:
                    conversation_id = str(uuid.uuid4())
                
                # Parse model name to extract backend info
                if " (" in model_name and model_name.endswith(")"):
                    parts = model_name.rsplit(" (", 1)
                    actual_model = parts[0]
                    backend = parts[1][:-1]
                else:
                    actual_model = model_name
                    backend = None
                
                # Save user message to database
                self._save_message(conversation_id, 'user', message, actual_model, backend)
                
                # Generate response using backend manager
                start_time = time.time()
                
                try:
                    # Use the BackendManagerSync.generate_response method
                    response = self.backend_manager.generate_response(
                        model=actual_model,
                        prompt=message
                    )
                    
                    response_time = time.time() - start_time
                    
                    # Extract response content
                    if isinstance(response, dict):
                        response_text = response.get('response', '')
                        estimated_tokens = response.get('estimated_tokens', 0)
                    else:
                        response_text = str(response)
                        estimated_tokens = 0
                    
                    # Determine which backend was actually used
                    # This is a simplified approach - in practice you'd get this from the response
                    used_backend = backend or self.config_manager.get_default_backend()
                    
                    # Save assistant response to database
                    self._save_message(
                        conversation_id, 
                        'assistant', 
                        response_text, 
                        actual_model,
                        used_backend,
                        response_time
                    )
                    
                    # Update conversation metadata
                    self._update_conversation(conversation_id, actual_model, used_backend)
                    
                    return jsonify({
                        'success': True,
                        'response': response_text,
                        'conversation_id': conversation_id,
                        'model': actual_model,
                        'backend': used_backend,
                        'response_time': response_time,
                        'estimated_tokens': estimated_tokens
                    })
                    
                except Exception as e:
                    logger.error(f"Backend response generation failed: {e}")
                    return jsonify({
                        'success': False,
                        'error': f'Failed to generate response: {str(e)}',
                        'backend_error': True
                    }), 500
                
            except Exception as e:
                logger.error(f"Chat endpoint error: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Internal server error: {str(e)}'
                }), 500
        
        @self.app.route('/api/conversations', methods=['GET'])
        def get_conversations():
            """Get conversation list with backend information"""
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT id, title, created_at, updated_at, model_name, backend
                        FROM conversations 
                        ORDER BY updated_at DESC
                        LIMIT 50
                    ''')
                    
                    conversations = []
                    for row in cursor.fetchall():
                        conversations.append({
                            'id': row[0],
                            'title': row[1],
                            'created_at': row[2],
                            'updated_at': row[3],
                            'model_name': row[4],
                            'backend': row[5] or 'unknown'
                        })
                    
                    return jsonify({
                        'success': True,
                        'conversations': conversations
                    })
                    
            except Exception as e:
                logger.error(f"Error fetching conversations: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to fetch conversations: {str(e)}'
                }), 500
        
        @self.app.route('/api/conversations/<conversation_id>/messages', methods=['GET'])
        def get_conversation_messages(conversation_id):
            """Get messages for a specific conversation"""
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT role, content, timestamp, model_name, backend, response_time
                        FROM messages 
                        WHERE conversation_id = ?
                        ORDER BY timestamp ASC
                    ''', (conversation_id,))
                    
                    messages = []
                    for row in cursor.fetchall():
                        messages.append({
                            'role': row[0],
                            'content': row[1],
                            'timestamp': row[2],
                            'model_name': row[3],
                            'backend': row[4],
                            'response_time': row[5]
                        })
                    
                    return jsonify({
                        'success': True,
                        'messages': messages,
                        'conversation_id': conversation_id
                    })
                    
            except Exception as e:
                logger.error(f"Error fetching messages: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to fetch messages: {str(e)}'
                }), 500
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Application health check endpoint"""
            try:
                backend_health = self.backend_manager.get_health_status()
                available_backends = self.backend_manager.get_available_backends()
                
                app_healthy = len(available_backends) > 0
                
                return jsonify({
                    'success': True,
                    'healthy': app_healthy,
                    'backends': backend_health,
                    'available_backends': available_backends,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return jsonify({
                    'success': False,
                    'healthy': False,
                    'error': str(e)
                }), 500
    
    def _save_message(self, conversation_id: str, role: str, content: str, 
                     model_name: str, backend: str = None, response_time: float = None):
        """Save message to database with backend information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO messages (conversation_id, role, content, model_name, backend, response_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (conversation_id, role, content, model_name, backend, response_time))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving message: {e}")
    
    def _update_conversation(self, conversation_id: str, model_name: str, backend: str = None):
        """Update or create conversation metadata"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if conversation exists
                cursor.execute('SELECT id FROM conversations WHERE id = ?', (conversation_id,))
                if cursor.fetchone():
                    # Update existing conversation
                    cursor.execute('''
                        UPDATE conversations 
                        SET updated_at = CURRENT_TIMESTAMP, model_name = ?, backend = ?
                        WHERE id = ?
                    ''', (model_name, backend, conversation_id))
                else:
                    # Create new conversation
                    title = f"Chat with {model_name}"
                    if backend:
                        title += f" ({backend})"
                        
                    cursor.execute('''
                        INSERT INTO conversations (id, title, model_name, backend)
                        VALUES (?, ?, ?, ?)
                    ''', (conversation_id, title, model_name, backend))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating conversation: {e}")
    
    def run(self, host: str = None, port: int = None, debug: bool = None):
        """Run the Flask application"""
        app_config = self.config_manager.get('app', default={})
        
        # Use config values as defaults, allow override
        host = host or app_config.get('host', '127.0.0.1')
        port = port or app_config.get('port', 5000)
        debug = debug if debug is not None else app_config.get('debug', False)
        
        logger.info(f"🚀 Starting chat application on {host}:{port}")
        logger.info(f"🔧 Debug mode: {debug}")
        
        # Show backend status
        try:
            available = self.backend_manager.get_available_backends()
            if available:
                logger.info(f"✅ Available backends: {', '.join(available)}")
            else:
                logger.warning("⚠️  No backends available - check service status")
        except Exception as e:
            logger.error(f"❌ Error checking backend status: {e}")
        
        self.app.run(host=host, port=port, debug=debug, threaded=True)


# Application factory function
def create_app(config_path: str = 'config.json') -> ChatApplication:
    """Create and configure the chat application"""
    return ChatApplication(config_path)


if __name__ == '__main__':
    # Initialize and run the application
    try:
        app = create_app()
        app.run()
    except KeyboardInterrupt:
        logger.info("🛑 Application shutdown requested")
    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        raise

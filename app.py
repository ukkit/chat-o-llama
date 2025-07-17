#!/usr/bin/env python3
"""
Chat-O-Llama: A Flask web application for chatting with Ollama models.
Enhanced with MCP integration, persistent history, and response metrics tracking.
"""

import os
import logging
from flask import Flask

# Import our modular components
from config import get_config
from utils.logging import setup_logging
from utils.database import close_db
from persistence.database import init_database_schema
from services.llm_factory import get_active_backend, get_llm_factory
from api.routes import register_routes

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['THREADED'] = True

# Register database teardown handler
@app.teardown_appcontext
def close_db_on_teardown(error):
    close_db(error)

# Register all routes
register_routes(app)


def main():
    """Main application entry point."""
    # Initialize database
    init_database_schema()

    # Check backend connections
    try:
        factory = get_llm_factory()
        backend = get_active_backend()
        backend_type = factory.get_active_backend_type()
        models = backend.get_models()
        
        if models:
            logger.info(f"Connected to {backend_type} backend. Available models: {models}")
        else:
            logger.warning(f"Connected to {backend_type} backend but no models available")
            
        # Log status of all backends
        backend_models = factory.get_available_models()
        for bt, model_list in backend_models.items():
            logger.info(f"{bt} backend: {len(model_list)} models available")
            
    except Exception as e:
        logger.error(f"Failed to initialize backends: {e}")
        logger.warning("Application starting without backend connection")

    # Log current configuration
    config = get_config()
    logger.info(f"Ollama timeout: {config['timeouts']['ollama_timeout']}s")
    logger.info(f"Context history limit: {config['performance']['context_history_limit']} messages")
    logger.info(f"Temperature: {config['model_options']['temperature']}")

    # Run the app with threading enabled
    app.run(
        host=config.get('server', {}).get('host', '0.0.0.0'),
        port=config.get('server', {}).get('port', 3113),
        debug=config.get('server', {}).get('debug', False),
        threaded=True
    )


if __name__ == '__main__':
    main()
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
    init_database_schema()

    config = get_config()
    logger.info(f"Starting chat-o-llama on port {config.get('server', {}).get('port', 3113)}")

    # Backend connection is deferred — the LLM factory initialises lazily on first request.
    app.run(
        host=config.get('server', {}).get('host', '0.0.0.0'),
        port=config.get('server', {}).get('port', 3113),
        debug=config.get('server', {}).get('debug', False),
        threaded=True
    )


if __name__ == '__main__':
    main()
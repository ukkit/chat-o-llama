"""Route registration for Chat-O-Llama API modules."""

from flask import render_template
from .conversations import conversations_bp
from .chat import chat_bp
from .mcp import mcp_bp
from .backend import backend_bp


def register_routes(app):
    """Register all API route blueprints with the Flask app."""
    
    # Main route
    @app.route('/')
    def index():
        """Main chat interface."""
        return render_template('index.html')
    
    # Register API blueprints
    app.register_blueprint(conversations_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(mcp_bp)
    app.register_blueprint(backend_bp)
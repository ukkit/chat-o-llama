from flask import Flask, request, jsonify
import logging
import sys
from config_manager import init_config, get_config_manager, ConfigurationError

def create_app(config_path="config.json"):
    """Application factory with configuration management."""
    
    app = Flask(__name__)
    
    # Initialize configuration
    try:
        config_manager = init_config(config_path)
        app.config['CONFIG_MANAGER'] = config_manager
        
        # Apply Flask configuration
        app.config['SECRET_KEY'] = config_manager.get('app', 'secret_key', default='dev-key-change-in-production')
        app.config['DEBUG'] = config_manager.get('app', 'debug', default=False)
        
        # Setup logging
        log_level = config_manager.get('logging', 'level', default='INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(config_manager.get('logging', 'file', default='app.log')),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info("Application starting with configuration validation successful")
        
        # Test backend connectivity during startup
        enabled_backends = config_manager.get_enabled_backends()
        for backend_name in enabled_backends:
            is_healthy, message = config_manager.test_backend_connectivity(backend_name)
            if is_healthy:
                logger.info(f"✓ {message}")
            else:
                logger.warning(f"✗ {message}")
        
    except ConfigurationError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Startup Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Configuration endpoint for debugging/monitoring
    @app.route('/api/config/status')
    def config_status():
        """Get configuration and backend status."""
        config_manager = app.config['CONFIG_MANAGER']
        
        status = {
            "enabled_backends": config_manager.get_enabled_backends(),
            "default_backend": config_manager.get_default_backend(),
            "backend_status": {}
        }
        
        # Check each enabled backend
        for backend_name in status["enabled_backends"]:
            is_healthy, message = config_manager.test_backend_connectivity(backend_name)
            status["backend_status"][backend_name] = {
                "healthy": is_healthy,
                "message": message,
                "config": {
                    "url": config_manager.get('backends', backend_name, 'url'),
                    "timeout": config_manager.get('backends', backend_name, 'timeout'),
                    "enabled": config_manager.get('backends', backend_name, 'enabled')
                }
            }
        
        return jsonify(status)
    
    @app.route('/api/config/test-backend/<backend_name>')
    def test_backend(backend_name):
        """Test connectivity to a specific backend."""
        config_manager = app.config['CONFIG_MANAGER']
        
        is_healthy, message = config_manager.test_backend_connectivity(backend_name)
        
        return jsonify({
            "backend": backend_name,
            "healthy": is_healthy,
            "message": message
        })
    
    # Error handlers
    @app.errorhandler(ConfigurationError)
    def handle_config_error(error):
        return jsonify({
            "error": "Configuration Error",
            "message": str(error)
        }), 500
    
    return app

def main():
    """Main application entry point."""
    app = create_app()
    config_manager = app.config['CONFIG_MANAGER']
    
    # Get host and port from configuration
    host = config_manager.get('app', 'host', default='0.0.0.0')
    port = config_manager.get('app', 'port', default=5000)
    debug = config_manager.get('app', 'debug', default=False)
    
    # Enable threading for better performance as suggested
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True  # Enable thread pool for concurrent request handling
    )

if __name__ == '__main__':
    main()
"""Backend management API routes for Chat-O-Llama."""

import logging
from typing import Dict, Any
from flask import request, jsonify, Blueprint
from services.llm_factory import get_llm_factory, BackendType
from config import get_config

logger = logging.getLogger(__name__)

backend_bp = Blueprint('backend', __name__)


@backend_bp.route('/api/backend/status')
def api_backend_status():
    """Get detailed status information for all backends."""
    try:
        factory = get_llm_factory()
        
        # Get comprehensive status for all backends
        status_data = factory.get_backend_status()
        
        # Add configuration information
        config = get_config()
        backend_config = config.get('backend', {})
        
        response = {
            'status': 'success',
            'backends': status_data['backends'],
            'active_backend': status_data['active_backend'],
            'configuration': {
                'auto_fallback': status_data['auto_fallback'],
                'health_check_interval': backend_config.get('health_check_interval', 30),
                'available_backends': [bt.value for bt in BackendType]
            },
            'timestamp': factory._last_health_check
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in /api/backend/status endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'backends': {},
            'active_backend': None
        }), 500


@backend_bp.route('/api/backend/info')
def api_backend_info():
    """Get detailed information about the currently active backend."""
    try:
        factory = get_llm_factory()
        active_backend_type = factory.get_active_backend_type()
        
        if not active_backend_type:
            return jsonify({
                'status': 'error',
                'error': 'No active backend found',
                'backend_type': None,
                'backend_info': {}
            }), 404
        
        # Get the active backend and its info
        active_backend = factory.get_backend(active_backend_type)
        backend_info = active_backend.get_backend_info()
        
        # Get backend status
        backend_status = factory.get_backend_status(active_backend_type)
        
        response = {
            'status': 'success',
            'backend_type': active_backend_type,
            'backend_info': backend_info,
            'backend_status': backend_status,
            'models': active_backend.get_models(),
            'capabilities': {
                'streaming': backend_info.get('capabilities', {}).get('streaming', False),
                'conversation_history': backend_info.get('capabilities', {}).get('conversation_history', True),
                'model_switching': backend_info.get('capabilities', {}).get('model_switching', True)
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in /api/backend/info endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'backend_type': None,
            'backend_info': {}
        }), 500


@backend_bp.route('/api/backend/switch', methods=['POST'])
def api_backend_switch():
    """Switch to a different backend at runtime."""
    try:
        data = request.get_json(silent=True)
        
        if not data or 'backend_type' not in data:
            return jsonify({
                'status': 'error',
                'error': 'Missing backend_type in request body',
                'available_backends': [bt.value for bt in BackendType]
            }), 400
        
        new_backend_type = data['backend_type']
        
        # Validate backend type
        valid_backends = [bt.value for bt in BackendType]
        if new_backend_type not in valid_backends:
            return jsonify({
                'status': 'error',
                'error': f'Invalid backend type: {new_backend_type}',
                'available_backends': valid_backends
            }), 400
        
        factory = get_llm_factory()
        current_backend = factory.get_active_backend_type()
        
        # Check if already using the requested backend
        if current_backend == new_backend_type:
            return jsonify({
                'status': 'success',
                'message': f'Already using {new_backend_type} backend',
                'previous_backend': current_backend,
                'current_backend': new_backend_type,
                'switched': False
            })
        
        # Attempt to switch backend
        switch_successful = factory.switch_backend(new_backend_type)
        
        if switch_successful:
            # Get info about the new backend
            new_backend = factory.get_backend(new_backend_type)
            backend_info = new_backend.get_backend_info()
            
            logger.info(f"Successfully switched from {current_backend} to {new_backend_type}")
            
            return jsonify({
                'status': 'success',
                'message': f'Successfully switched to {new_backend_type} backend',
                'previous_backend': current_backend,
                'current_backend': new_backend_type,
                'switched': True,
                'backend_info': backend_info,
                'available_models': new_backend.get_models()
            })
        else:
            return jsonify({
                'status': 'error',
                'error': f'Failed to switch to {new_backend_type} backend',
                'previous_backend': current_backend,
                'current_backend': factory.get_active_backend_type(),
                'switched': False
            }), 500
            
    except Exception as e:
        logger.error(f"Error in /api/backend/switch endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'switched': False,
            'available_backends': [bt.value for bt in BackendType]
        }), 500


@backend_bp.route('/api/backend/models')
def api_backend_models():
    """Get available models from all backends with detailed information."""
    try:
        factory = get_llm_factory()
        
        # Get models from all backends
        backend_models = factory.get_available_models()
        
        # Get backend status to provide additional context
        backend_status = factory.get_backend_status()
        
        # Format response with detailed information
        response = {
            'status': 'success',
            'models_by_backend': backend_models,
            'backend_status': backend_status['backends'],
            'active_backend': backend_status['active_backend'],
            'summary': {
                'total_backends': len(backend_models),
                'active_backends': sum(1 for models in backend_models.values() if len(models) > 0),
                'total_models': sum(len(models) for models in backend_models.values()),
                'models_by_backend_count': {
                    backend: len(models) for backend, models in backend_models.items()
                }
            }
        }
        
        # Add models with backend prefixes for easy identification
        prefixed_models = []
        for backend_type, models in backend_models.items():
            for model in models:
                prefixed_models.append(f"{backend_type}:{model}")
        
        response['prefixed_models'] = prefixed_models
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in /api/backend/models endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'models_by_backend': {},
            'backend_status': {},
            'active_backend': None
        }), 500


@backend_bp.route('/api/backend/health', methods=['POST'])
def api_backend_health():
    """Perform health check on specified backend or all backends."""
    try:
        data = request.get_json(silent=True)
        backend_type = data.get('backend_type') if data else None
        
        factory = get_llm_factory()
        
        # Perform health check
        health_results = factory.health_check(backend_type)
        
        # Get updated status after health check
        status_data = factory.get_backend_status(backend_type)
        
        response = {
            'status': 'success',
            'health_check_results': health_results,
            'backend_status': status_data if backend_type else status_data['backends'],
            'timestamp': factory._last_health_check
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in /api/backend/health endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'health_check_results': {},
            'backend_status': {}
        }), 500
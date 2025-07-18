"""Chat API routes for Chat-O-Llama."""

import os
import re
import logging
from typing import Dict, List, Any
from flask import request, jsonify, Blueprint
from services.llm_factory import get_active_backend, get_llm_factory
from services.conversation_manager import ConversationManager
from services.mcp_manager import MCPManager
from services.request_manager import get_request_manager
from utils.token_estimation import estimate_tokens
from config import get_config

logger = logging.getLogger(__name__)

OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')

chat_bp = Blueprint('chat', __name__)

# Initialize MCP Manager for this module
mcp_manager = MCPManager()


def detect_and_execute_mcp_tools(message: str) -> List[Dict[str, Any]]:
    """Detect and execute MCP tools based on user message."""
    tool_results = []
    
    if not mcp_manager.enabled:
        return tool_results
    
    # Simple pattern matching for tool detection
    # This is a basic implementation - in production you might want more sophisticated NLP
    message_lower = message.lower()
    
    # Check for file operations
    if any(keyword in message_lower for keyword in ['read file', 'write file', 'list files', 'file content']):
        # Try to execute file system tools if available
        for server_id, connection_info in mcp_manager.connections.items():
            if connection_info.get('capabilities') and connection_info['capabilities'].get('tools'):
                for tool in connection_info['capabilities']['tools']:
                    if 'file' in tool['name'].lower() or 'read' in tool['name'].lower():
                        # Extract file path from message (basic implementation)
                        file_matches = re.findall(r'["\']([^"\']+)["\']', message)
                        if file_matches:
                            try:
                                result = mcp_manager.sync_execute_tool(
                                    server_id, 
                                    tool['name'], 
                                    {'path': file_matches[0]}
                                )
                                if result and result.get('success'):
                                    tool_results.append({
                                        'tool': tool['name'],
                                        'server': server_id,
                                        'result': result
                                    })
                            except Exception as e:
                                logger.error(f"Tool execution failed: {e}")
    
    # Check for memory operations
    if any(keyword in message_lower for keyword in ['remember', 'recall', 'store', 'save information']):
        # Try to execute memory tools if available
        for server_id, connection_info in mcp_manager.connections.items():
            if connection_info.get('capabilities') and connection_info['capabilities'].get('tools'):
                for tool in connection_info['capabilities']['tools']:
                    if 'memory' in tool['name'].lower() or 'store' in tool['name'].lower():
                        try:
                            # Extract what to remember/recall
                            content = message.replace('remember', '').replace('recall', '').strip()
                            result = mcp_manager.sync_execute_tool(
                                server_id,
                                tool['name'],
                                {'content': content}
                            )
                            if result and result.get('success'):
                                tool_results.append({
                                    'tool': tool['name'],
                                    'server': server_id,
                                    'result': result
                                })
                        except Exception as e:
                            logger.error(f"Memory tool execution failed: {e}")
    
    return tool_results


def format_tool_results_for_context(tool_results: List[Dict[str, Any]]) -> str:
    """Format tool execution results for inclusion in chat context."""
    if not tool_results:
        return ""
    
    formatted_results = []
    for tool_result in tool_results:
        tool_name = tool_result['tool']
        server_name = tool_result['server']
        result = tool_result['result']
        
        if result.get('success'):
            content = result.get('content', [])
            if isinstance(content, list):
                content_str = '\n'.join(str(item) for item in content)
            else:
                content_str = str(content)
            
            formatted_results.append(f"**{tool_name}** (from {server_name}):\n{content_str}")
        else:
            error_msg = result.get('error', 'Unknown error')
            formatted_results.append(f"**{tool_name}** (from {server_name}): Error - {error_msg}")
    
    return '\n\n'.join(formatted_results)


@chat_bp.route('/api/models')
def api_models():
    """Get available models from all backends."""
    try:
        factory = get_llm_factory()
        
        # Get models from all backends
        backend_models = factory.get_available_models()
        
        # Get backend health status for additional context
        backend_health = factory.health_check()
        
        # Aggregate all models into a single list
        all_models = []
        backend_info = {}
        
        for backend_type, models in backend_models.items():
            backend_info[backend_type] = {
                'models': models,
                'count': len(models),
                'available': len(models) > 0,
                'healthy': backend_health.get(backend_type, False)
            }
            # Add backend prefix to model names for identification
            for model in models:
                all_models.append(f"{backend_type}:{model}")
        
        # Get active backend status
        active_backend_type = factory.get_active_backend_type()
        active_backend_status = factory.get_backend_status(active_backend_type) if active_backend_type else None
        
        # Get models only from the active backend
        active_backend_models = backend_models.get(active_backend_type, []) if active_backend_type else []
        
        # Also provide models from all backends for advanced use cases
        compatibility_models = []
        for models in backend_models.values():
            compatibility_models.extend(models)
        
        return jsonify({
            'models': active_backend_models,  # Only models from active backend
            'models_with_backend': all_models,
            'all_models': list(set(compatibility_models)),  # All models for reference
            'backends': backend_info,
            'count': len(active_backend_models),
            'active_backend': active_backend_type,
            'active_backend_status': active_backend_status,
            'health_check': backend_health,
            'ollama_url': OLLAMA_API_URL
        })
    except Exception as e:
        logger.error(f"Error in /api/models endpoint: {e}")
        return jsonify({
            'models': [],
            'models_with_backend': [],
            'backends': {},
            'count': 0,
            'error': str(e),
            'active_backend': None,
            'active_backend_status': None,
            'health_check': {},
            'ollama_url': OLLAMA_API_URL
        }), 500


@chat_bp.route('/api/config')
def api_config():
    """Get current configuration (excluding sensitive data)."""
    config = get_config()
    config_display = {
        'timeouts': config['timeouts'],
        'model_options': config['model_options'],
        'performance': config['performance'],
        'response_optimization': {k: v for k, v in config['response_optimization'].items() if k != 'system_prompt'}
    }
    return jsonify(config_display)


@chat_bp.route('/api/chat', methods=['POST'])
def api_chat():
    """Send message and get response with enhanced metrics."""
    data = request.get_json()
    conversation_id = data.get('conversation_id')
    message = data.get('message')
    model = data.get('model', 'llama3.2')

    if not conversation_id or not message:
        return jsonify({'error': 'Missing conversation_id or message'}), 400

    # Get the conversation to use its original model
    conversation = ConversationManager.get_conversation(conversation_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    # Always use the conversation's original model, not the one from the request
    conversation_model = conversation['model']
    logger.info(f"Using conversation's original model '{conversation_model}' instead of requested model '{model}'")

    # Get backend type for storing in database
    try:
        backend = get_active_backend()
        backend_info = backend.get_backend_info()
        backend_type = str(backend_info.get('backend_type', 'ollama'))  # Ensure it's a string
    except Exception as e:
        logger.warning(f"Could not get backend type: {e}, defaulting to 'ollama'")
        backend_type = 'ollama'
    
    # Create request tracking
    request_manager = get_request_manager()
    request_id = request_manager.create_request(
        conversation_id=conversation_id,
        model=conversation_model,
        message=message,
        backend_type=backend_type,
        user_session=request.headers.get('X-Session-Id'),
        metadata={
            'user_agent': request.headers.get('User-Agent'),
            'ip_address': request.remote_addr
        }
    )
    
    # Add user message
    user_tokens = estimate_tokens(message)
    ConversationManager.add_message(
        conversation_id, 'user', message, conversation_model, None, user_tokens, backend_type
    )

    # Get conversation history for context with compression
    config = get_config()
    max_context_tokens = config.get('model_options', {}).get('num_ctx', 4096)
    
    # Use compression-enabled context preparation
    formatted_messages, context_metadata = ConversationManager.prepare_context_for_llm(
        conversation_id, conversation_model, max_context_tokens
    )
    
    # Remove the last message (current user message) from history for context
    history = formatted_messages[:-1] if len(formatted_messages) > 1 else []

    # Check for MCP tool usage before generating response
    mcp_context = ""
    tool_results = []
    
    if mcp_manager.enabled:
        # Simple tool detection - look for tool invocation patterns
        tool_results = detect_and_execute_mcp_tools(message)
        if tool_results:
            mcp_context = format_tool_results_for_context(tool_results)
    
    # Generate response with metrics (including MCP context if available)
    enhanced_message = message
    if mcp_context:
        enhanced_message = f"{message}\n\nTool Results:\n{mcp_context}"
    
    # Update request status to processing
    from services.request_manager import RequestStatus
    request_manager.update_request_status(request_id, RequestStatus.PROCESSING)
    
    # Get backend instance and generate response (reuse backend from earlier)
    try:
        if 'backend' not in locals():
            backend = get_active_backend()
        
        # Get the cancellation token for this request
        request_info = request_manager.get_request(request_id)
        cancellation_token = request_info.cancellation_token if request_info else None
        
        # Pass cancellation token and request_id to backend if supported
        response_data = backend.generate_response(
            conversation_model, enhanced_message, history, 
            cancellation_token=cancellation_token,
            request_id=request_id
        )
        
        # Check if request was cancelled during generation
        if request_info and request_info.is_cancelled():
            request_manager.update_request_status(request_id, RequestStatus.CANCELLED)
            return jsonify({
                'error': 'Request was cancelled',
                'request_id': request_id,
                'cancelled': True
            }), 400
        
        # Mark request as completed
        request_manager.update_request_status(
            request_id, RequestStatus.COMPLETED,
            metadata={'response_tokens': response_data.get('estimated_tokens', 0)}
        )
        
    except Exception as e:
        logger.error(f"Failed to generate response with active backend: {e}")
        request_manager.update_request_status(
            request_id, RequestStatus.FAILED,
            metadata={'error': str(e)}
        )
        return jsonify({'error': f'Backend error: {str(e)}'}), 500

    # Add assistant response with metrics
    ConversationManager.add_message(
        conversation_id, 
        'assistant', 
        response_data['response'], 
        conversation_model,
        response_data['response_time_ms'],
        response_data['estimated_tokens'],
        backend_type
    )

    return jsonify({
        'response': response_data['response'],
        'model': conversation_model,
        'backend_type': backend_type,
        'response_time_ms': response_data['response_time_ms'],
        'estimated_tokens': response_data['estimated_tokens'],
        'request_id': request_id,
        'metrics': {
            'eval_count': response_data.get('eval_count'),
            'eval_duration': response_data.get('eval_duration'),
            'load_duration': response_data.get('load_duration'),
            'prompt_eval_count': response_data.get('prompt_eval_count'),
            'prompt_eval_duration': response_data.get('prompt_eval_duration'),
            'total_duration': response_data.get('total_duration')
        },
        'context_compression': {
            'enabled': context_metadata.get('compression_applied', False),
            'compression_metadata': context_metadata.get('compression_metadata'),
            'context_optimized': context_metadata.get('context_optimized', False),
            'message_count': context_metadata.get('message_count', 0)
        },
        'mcp_tools': {
            'enabled': mcp_manager.enabled,
            'tools_executed': len(tool_results),
            'results': tool_results if tool_results else []
        }
    })


@chat_bp.route('/api/chat/compression/recommendations/<int:conversation_id>')
def api_compression_recommendations(conversation_id):
    """Get compression recommendations for a conversation."""
    try:
        model = request.args.get('model', 'llama3.2')
        recommendations = ConversationManager.get_compression_recommendations(conversation_id, model)
        return jsonify(recommendations)
    except Exception as e:
        logger.error(f"Error getting compression recommendations: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/compression/analyze/<int:conversation_id>')
def api_compression_analyze(conversation_id):
    """Analyze message importance in a conversation."""
    try:
        analysis = ConversationManager.analyze_conversation_importance(conversation_id)
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Error analyzing conversation importance: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/compression/stats/<int:conversation_id>')
def api_compression_stats(conversation_id):
    """Get compression statistics for a conversation."""
    try:
        stats = ConversationManager.get_conversation_compression_stats(conversation_id)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting compression stats: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/compression/force/<int:conversation_id>', methods=['POST'])
def api_force_compression(conversation_id):
    """Force compression on a conversation."""
    try:
        data = request.get_json() or {}
        model = data.get('model', 'llama3.2')
        strategy = data.get('strategy')  # Optional: force specific strategy
        max_tokens = data.get('max_tokens', 4096)
        
        # Get messages with forced compression
        result = ConversationManager.get_messages(
            conversation_id,
            include_compression_metadata=True,
            compress_context={
                'force': True,
                'model_name': model,
                'max_tokens': max_tokens
            }
        )
        
        return jsonify({
            'compressed': True,
            'message_count': len(result['messages']),
            'compression_metadata': result['compression_metadata']
        })
        
    except Exception as e:
        logger.error(f"Error forcing compression: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/compression/status')
def api_compression_status():
    """Get global compression status and configuration."""
    try:
        from services.context_compressor import get_context_compressor
        compressor = get_context_compressor()
        status = compressor.get_compression_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting compression status: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/cancel/<request_id>', methods=['POST'])
def api_cancel_request(request_id):
    """Cancel a specific chat request."""
    try:
        request_manager = get_request_manager()
        
        # Validate request ID format
        if not request_id or len(request_id) != 36:  # UUID format
            return jsonify({'error': 'Invalid request ID format'}), 400
        
        # Attempt to cancel the request
        success = request_manager.cancel_request(request_id)
        
        if success:
            request_info = request_manager.get_request(request_id)
            logger.info(f"Request {request_id} cancelled successfully")
            
            return jsonify({
                'success': True,
                'message': 'Request cancelled successfully',
                'request_id': request_id,
                'status': request_info.status.value if request_info else 'cancelled',
                'cancelled_at': request_info.cancelled_at.isoformat() if request_info and request_info.cancelled_at else None
            })
        else:
            # Request not found or not active
            request_info = request_manager.get_request(request_id)
            if request_info:
                return jsonify({
                    'success': False,
                    'message': f'Request is not active (status: {request_info.status.value})',
                    'request_id': request_id,
                    'status': request_info.status.value
                }), 400
            else:
                return jsonify({
                    'success': False,
                    'message': 'Request not found',
                    'request_id': request_id
                }), 404
        
    except Exception as e:
        logger.error(f"Error cancelling request {request_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'request_id': request_id
        }), 500


@chat_bp.route('/api/chat/cancel/conversation/<conversation_id>', methods=['POST'])
def api_cancel_conversation_requests(conversation_id):
    """Cancel all active requests for a conversation."""
    try:
        request_manager = get_request_manager()
        
        # Validate conversation ID
        if not conversation_id:
            return jsonify({'error': 'Missing conversation ID'}), 400
        
        # Cancel all active requests for this conversation
        cancelled_count = request_manager.cancel_conversation_requests(conversation_id)
        
        logger.info(f"Cancelled {cancelled_count} requests for conversation {conversation_id}")
        
        return jsonify({
            'success': True,
            'message': f'Cancelled {cancelled_count} requests for conversation',
            'conversation_id': conversation_id,
            'cancelled_count': cancelled_count
        })
        
    except Exception as e:
        logger.error(f"Error cancelling conversation requests {conversation_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'conversation_id': conversation_id
        }), 500


@chat_bp.route('/api/chat/requests/active')
def api_get_active_requests():
    """Get all active requests."""
    try:
        request_manager = get_request_manager()
        active_requests = request_manager.get_active_requests()
        
        # Convert to serializable format
        requests_data = []
        for req in active_requests:
            requests_data.append({
                'request_id': req.request_id,
                'conversation_id': req.conversation_id,
                'model': req.model,
                'backend_type': req.backend_type,
                'status': req.status.value,
                'created_at': req.created_at.isoformat(),
                'started_at': req.started_at.isoformat() if req.started_at else None,
                'duration_seconds': req.duration_seconds,
                'user_session': req.user_session,
                'metadata': req.metadata
            })
        
        return jsonify({
            'active_requests': requests_data,
            'count': len(requests_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting active requests: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/requests/stats')
def api_get_request_stats():
    """Get request statistics."""
    try:
        request_manager = get_request_manager()
        stats = request_manager.get_request_stats()
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting request stats: {e}")
        return jsonify({'error': str(e)}), 500
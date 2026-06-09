"""MCP API routes for Chat-O-Llama."""

import logging
from flask import request, jsonify, Blueprint
from services.mcp_manager import get_mcp_manager, MCP_AVAILABLE

logger = logging.getLogger(__name__)

mcp_bp = Blueprint('mcp', __name__)


@mcp_bp.route('/api/mcp/status')
def api_mcp_status():
    """Get MCP server status and availability."""
    try:
        return jsonify(get_mcp_manager().get_server_status())
    except Exception as e:
        logger.error(f"Error getting MCP status: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_bp.route('/api/mcp/servers')
def api_mcp_servers():
    """List all configured MCP servers and their capabilities."""
    try:
        mcp = get_mcp_manager()
        servers = {}
        for server_id, info in mcp.connections.items():
            servers[server_id] = {
                'id': server_id,
                'name': info['config'].get('name', server_id),
                'status': info['status'],
                'transport': info['config'].get('transport', 'stdio'),
                'enabled': info['config'].get('enabled', False),
                'last_connected': info['last_connected'].isoformat() if info['last_connected'] else None,
                'capabilities': info['capabilities'],
            }
        return jsonify({'enabled': mcp.enabled, 'mcp_available': MCP_AVAILABLE, 'servers': servers})
    except Exception as e:
        logger.error(f"Error getting MCP servers: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_bp.route('/api/mcp/servers/<server_id>/capabilities')
def api_mcp_server_capabilities(server_id):
    """Get capabilities for a specific MCP server."""
    try:
        capabilities = get_mcp_manager().sync_get_server_capabilities(server_id)
        if capabilities is None:
            return jsonify({'error': 'Server not found or not available'}), 404
        return jsonify(capabilities)
    except Exception as e:
        logger.error(f"Error getting capabilities for server {server_id}: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_bp.route('/api/mcp/tools')
def api_mcp_tools():
    """Get all available tools from all MCP servers."""
    try:
        mcp = get_mcp_manager()
        all_tools = []
        for server_id, info in mcp.connections.items():
            if info.get('capabilities') and info['capabilities'].get('tools'):
                for tool in info['capabilities']['tools']:
                    all_tools.append({**tool, 'server_id': server_id, 'server_name': info['config'].get('name', server_id)})
        return jsonify({'tools': all_tools})
    except Exception as e:
        logger.error(f"Error getting MCP tools: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_bp.route('/api/mcp/tools/execute', methods=['POST'])
def api_mcp_execute_tool():
    """Execute a tool on an MCP server."""
    try:
        data = request.get_json()
        server_id = data.get('server_id')
        tool_name = data.get('tool_name')
        if not server_id or not tool_name:
            return jsonify({'error': 'server_id and tool_name are required'}), 400
        result = get_mcp_manager().sync_execute_tool(server_id, tool_name, data.get('arguments', {}))
        if result is None:
            return jsonify({'error': 'Server not found or tool execution failed'}), 404
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error executing MCP tool: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_bp.route('/api/mcp/resources')
def api_mcp_resources():
    """Get all available resources from all MCP servers."""
    try:
        mcp = get_mcp_manager()
        all_resources = []
        for server_id, info in mcp.connections.items():
            if info.get('capabilities') and info['capabilities'].get('resources'):
                for resource in info['capabilities']['resources']:
                    all_resources.append({**resource, 'server_id': server_id, 'server_name': info['config'].get('name', server_id)})
        return jsonify({'resources': all_resources})
    except Exception as e:
        logger.error(f"Error getting MCP resources: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_bp.route('/api/mcp/prompts')
def api_mcp_prompts():
    """Get all available prompts from all MCP servers."""
    try:
        mcp = get_mcp_manager()
        all_prompts = []
        for server_id, info in mcp.connections.items():
            if info.get('capabilities') and info['capabilities'].get('prompts'):
                for prompt in info['capabilities']['prompts']:
                    all_prompts.append({**prompt, 'server_id': server_id, 'server_name': info['config'].get('name', server_id)})
        return jsonify({'prompts': all_prompts})
    except Exception as e:
        logger.error(f"Error getting MCP prompts: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_bp.route('/api/mcp/resources/<server_id>/<path:resource_uri>')
def api_mcp_get_resource(server_id, resource_uri):
    """Get content from a specific MCP resource."""
    try:
        mcp = get_mcp_manager()
        if not mcp.enabled or server_id not in mcp.connections:
            return jsonify({'error': 'Server not found or MCP not enabled'}), 404
        result = mcp.sync_get_resource(server_id, resource_uri)
        if result is None:
            return jsonify({'error': 'Resource not found or server not available'}), 404
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting MCP resource: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_bp.route('/api/mcp/prompts/execute', methods=['POST'])
def api_mcp_execute_prompt():
    """Execute a prompt on an MCP server."""
    try:
        data = request.get_json()
        server_id = data.get('server_id')
        prompt_name = data.get('prompt_name')
        if not server_id or not prompt_name:
            return jsonify({'error': 'server_id and prompt_name are required'}), 400
        result = get_mcp_manager().sync_execute_prompt(server_id, prompt_name, data.get('arguments', {}))
        if result is None:
            return jsonify({'error': 'Prompt not found or server not available'}), 404
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error executing MCP prompt: {e}")
        return jsonify({'error': str(e)}), 500

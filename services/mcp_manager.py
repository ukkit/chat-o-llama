"""MCP server management service for Chat-O-Llama."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from config import get_config

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None

logger = logging.getLogger(__name__)


class MCPManager:
    """Manage MCP server connections and operations."""
    
    def __init__(self):
        self.connections: Dict[str, Any] = {}
        config = get_config()
        self.servers_config = config.get('mcp_servers', {})
        self.enabled = self.servers_config.get('enabled', True) and MCP_AVAILABLE
        self.auto_connect = self.servers_config.get('auto_connect', True)
        
        if not MCP_AVAILABLE:
            logger.warning("MCP is not available - install with 'pip install mcp[cli]'")
            return
            
        if self.enabled and self.auto_connect:
            self.initialize_servers()
    
    def initialize_servers(self):
        """Initialize configured MCP servers."""
        if not self.enabled:
            return
            
        servers = self.servers_config.get('servers', {})
        for server_id, server_config in servers.items():
            if server_config.get('enabled', False):
                try:
                    self.connect_server(server_id, server_config)
                except Exception as e:
                    logger.error(f"Failed to initialize MCP server {server_id}: {e}")
    
    def connect_server(self, server_id: str, config: Dict[str, Any]):
        """Connect to an MCP server."""
        if not self.enabled:
            logger.warning("MCP is disabled")
            return False
            
        try:
            transport = config.get('transport', 'stdio')
            
            if transport == 'stdio':
                command = config.get('command')
                args = config.get('args', [])
                env = config.get('env', {})
                
                if not command:
                    logger.error(f"No command specified for MCP server {server_id}")
                    return False
                
                server_params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=env
                )
                
                # Store connection info for later use
                self.connections[server_id] = {
                    'config': config,
                    'params': server_params,
                    'status': 'configured',
                    'capabilities': None,
                    'last_connected': None
                }
                
                logger.info(f"MCP server {server_id} configured successfully")
                return True
            else:
                logger.error(f"Unsupported transport type: {transport}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect MCP server {server_id}: {e}")
            return False
    
    async def get_server_capabilities(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get capabilities from an MCP server."""
        if not self.enabled or server_id not in self.connections:
            return None
            
        try:
            connection_info = self.connections[server_id]
            server_params = connection_info['params']
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    await session.initialize()
                    
                    # Get server capabilities
                    capabilities = {
                        'tools': [],
                        'resources': [],
                        'prompts': []
                    }
                    
                    # List available tools
                    try:
                        tools_result = await session.list_tools()
                        capabilities['tools'] = [
                            {
                                'name': tool.name,
                                'description': tool.description,
                                'input_schema': tool.inputSchema
                            }
                            for tool in tools_result.tools
                        ]
                    except Exception as e:
                        logger.debug(f"No tools available for {server_id}: {e}")
                    
                    # List available resources
                    try:
                        resources_result = await session.list_resources()
                        capabilities['resources'] = [
                            {
                                'uri': resource.uri,
                                'name': resource.name,
                                'description': resource.description,
                                'mimeType': resource.mimeType
                            }
                            for resource in resources_result.resources
                        ]
                    except Exception as e:
                        logger.debug(f"No resources available for {server_id}: {e}")
                    
                    # List available prompts
                    try:
                        prompts_result = await session.list_prompts()
                        capabilities['prompts'] = [
                            {
                                'name': prompt.name,
                                'description': prompt.description,
                                'arguments': prompt.arguments
                            }
                            for prompt in prompts_result.prompts
                        ]
                    except Exception as e:
                        logger.debug(f"No prompts available for {server_id}: {e}")
                    
                    # Update connection info
                    self.connections[server_id]['capabilities'] = capabilities
                    self.connections[server_id]['status'] = 'connected'
                    self.connections[server_id]['last_connected'] = datetime.now()
                    
                    return capabilities
                    
        except Exception as e:
            logger.error(f"Failed to get capabilities for MCP server {server_id}: {e}")
            self.connections[server_id]['status'] = 'error'
            return None
    
    async def execute_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a tool on an MCP server."""
        if not self.enabled or server_id not in self.connections:
            return None
            
        try:
            connection_info = self.connections[server_id]
            server_params = connection_info['params']
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    await session.initialize()
                    
                    # Execute the tool
                    result = await session.call_tool(tool_name, arguments)
                    
                    return {
                        'success': True,
                        'content': result.content,
                        'isError': result.isError if hasattr(result, 'isError') else False
                    }
                    
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name} on server {server_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_resource(self, server_id: str, resource_uri: str) -> Optional[Dict[str, Any]]:
        """Get content from an MCP resource."""
        if not self.enabled or server_id not in self.connections:
            return None
            
        try:
            connection_info = self.connections[server_id]
            server_params = connection_info['params']
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    await session.initialize()
                    
                    # Read the resource
                    result = await session.read_resource(resource_uri)
                    
                    return {
                        'success': True,
                        'content': result.contents,
                        'uri': resource_uri
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get resource {resource_uri} from server {server_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def execute_prompt(self, server_id: str, prompt_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a prompt on an MCP server."""
        if not self.enabled or server_id not in self.connections:
            return None
            
        try:
            connection_info = self.connections[server_id]
            server_params = connection_info['params']
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    await session.initialize()
                    
                    # Get the prompt
                    result = await session.get_prompt(prompt_name, arguments)
                    
                    return {
                        'success': True,
                        'messages': result.messages,
                        'description': result.description
                    }
                    
        except Exception as e:
            logger.error(f"Failed to execute prompt {prompt_name} on server {server_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_get_server_capabilities(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for getting server capabilities."""
        if not self.enabled:
            return None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.get_server_capabilities(server_id))
        except Exception as e:
            logger.error(f"Failed to get capabilities synchronously: {e}")
            return None
        finally:
            loop.close()
    
    def sync_execute_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for tool execution."""
        if not self.enabled:
            return None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.execute_tool(server_id, tool_name, arguments))
        except Exception as e:
            logger.error(f"Failed to execute tool synchronously: {e}")
            return None
        finally:
            loop.close()
    
    def sync_get_resource(self, server_id: str, resource_uri: str) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for resource access."""
        if not self.enabled:
            return None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.get_resource(server_id, resource_uri))
        except Exception as e:
            logger.error(f"Failed to get resource synchronously: {e}")
            return None
        finally:
            loop.close()
    
    def sync_execute_prompt(self, server_id: str, prompt_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for prompt execution."""
        if not self.enabled:
            return None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.execute_prompt(server_id, prompt_name, arguments))
        except Exception as e:
            logger.error(f"Failed to execute prompt synchronously: {e}")
            return None
        finally:
            loop.close()
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get status of all configured servers."""
        return {
            'enabled': self.enabled,
            'mcp_available': MCP_AVAILABLE,
            'servers': {
                server_id: {
                    'name': info['config'].get('name', server_id),
                    'status': info['status'],
                    'last_connected': info['last_connected'].isoformat() if info['last_connected'] else None,
                    'has_capabilities': info['capabilities'] is not None
                }
                for server_id, info in self.connections.items()
            }
        }
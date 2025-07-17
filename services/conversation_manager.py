"""Conversation management service for Chat-O-Llama."""

import logging
from typing import List, Dict, Optional, Tuple, Any
from utils.database import get_db
from services.context_compressor import get_context_compressor


logger = logging.getLogger(__name__)


class ConversationManager:
    """Manage conversations and messages with enhanced metrics."""

    @staticmethod
    def create_conversation(title, model, backend_type='ollama'):
        """Create a new conversation."""
        db = get_db()
        cursor = db.execute(
            'INSERT INTO conversations (title, model, backend_type) VALUES (?, ?, ?)',
            (title, model, backend_type)
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
    def add_message(conversation_id, role, content, model=None, response_time_ms=None, estimated_tokens=None, backend_type='ollama'):
        """Add message to conversation with metrics."""
        db = get_db()
        db.execute(
            'INSERT INTO messages (conversation_id, role, content, model, response_time_ms, estimated_tokens, backend_type) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (conversation_id, role, content, model, response_time_ms, estimated_tokens, backend_type)
        )
        db.commit()
        ConversationManager.update_conversation_timestamp(conversation_id)

    @staticmethod
    def get_messages(conversation_id, include_compression_metadata=False, compress_context=None):
        """
        Get all messages for a conversation with optional context compression.
        
        Args:
            conversation_id: ID of the conversation
            include_compression_metadata: Whether to include compression metadata
            compress_context: Optional compression configuration
                - True: Auto-compress if needed
                - False: Never compress
                - Dict: Compression options (force, max_tokens, etc.)
                - None: Use default compression settings
        
        Returns:
            List of messages, optionally with compression metadata
        """
        db = get_db()
        messages = db.execute(
            'SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp',
            (conversation_id,)
        ).fetchall()
        
        # Convert to list of dictionaries for easier manipulation
        message_list = []
        for row in messages:
            message_dict = dict(row)
            message_list.append(message_dict)
        
        # Apply compression if requested
        compression_metadata = None
        if compress_context is not False and message_list:
            try:
                compressor = get_context_compressor()
                
                # Determine compression parameters
                if isinstance(compress_context, dict):
                    # Use provided options
                    force = compress_context.get('force', False)
                    max_tokens = compress_context.get('max_tokens', 4096)
                    model_name = compress_context.get('model_name')
                else:
                    # Use defaults
                    force = False
                    max_tokens = 4096
                    model_name = None
                
                # Get conversation for model info if needed
                if not model_name:
                    conversation = ConversationManager.get_conversation(conversation_id)
                    if conversation:
                        model_name = conversation['model']
                
                # Perform compression
                compressed_messages, compression_metadata = compressor.compress_context(
                    messages=message_list,
                    conversation_id=conversation_id,
                    model_name=model_name,
                    max_context_tokens=max_tokens,
                    force=force
                )
                
                # Update message list with compressed version
                if compressed_messages != message_list:
                    message_list = compressed_messages
                    logger.info(f"Applied context compression to conversation {conversation_id}")
                
            except Exception as e:
                logger.error(f"Context compression failed for conversation {conversation_id}: {str(e)}")
                # Continue with original messages if compression fails
        
        # Return with or without metadata based on request
        if include_compression_metadata:
            return {
                'messages': message_list,
                'compression_metadata': compression_metadata
            }
        else:
            return message_list

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
    
    @staticmethod
    def prepare_context_for_llm(conversation_id, model_name=None, max_context_tokens=4096):
        """
        Prepare conversation context optimized for LLM processing.
        
        This method automatically applies compression if needed and formats
        messages in the expected format for LLM backends.
        
        Args:
            conversation_id: ID of the conversation
            model_name: Target model name for optimization
            max_context_tokens: Maximum context window size
            
        Returns:
            Tuple of (formatted_messages, context_metadata)
        """
        try:
            # Get messages with compression
            result = ConversationManager.get_messages(
                conversation_id,
                include_compression_metadata=True,
                compress_context={
                    'max_tokens': max_context_tokens,
                    'model_name': model_name
                }
            )
            
            messages = result['messages']
            compression_metadata = result['compression_metadata']
            
            # Format messages for LLM consumption
            formatted_messages = []
            for msg in messages:
                # Skip metadata-only entries like summaries unless they're important
                if msg.get('is_summary', False):
                    # Include summaries as system messages
                    formatted_messages.append({
                        'role': 'system',
                        'content': msg['content']
                    })
                else:
                    # Regular user/assistant messages
                    formatted_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
            
            # Create context metadata
            context_metadata = {
                'conversation_id': conversation_id,
                'message_count': len(formatted_messages),
                'compression_applied': compression_metadata is not None and compression_metadata.get('compression_applied', False),
                'compression_metadata': compression_metadata,
                'context_optimized': True
            }
            
            logger.debug(f"Prepared context for conversation {conversation_id}: "
                        f"{len(formatted_messages)} messages, "
                        f"compression={context_metadata['compression_applied']}")
            
            return formatted_messages, context_metadata
            
        except Exception as e:
            logger.error(f"Error preparing context for conversation {conversation_id}: {str(e)}")
            # Fallback to simple message retrieval
            messages = ConversationManager.get_messages(conversation_id)
            formatted_messages = [{'role': msg['role'], 'content': msg['content']} for msg in messages]
            return formatted_messages, {'error': str(e), 'context_optimized': False}
    
    @staticmethod
    def get_compression_recommendations(conversation_id, model_name=None):
        """
        Get compression recommendations for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            model_name: Target model name for optimization
            
        Returns:
            Dictionary with compression recommendations
        """
        try:
            messages = ConversationManager.get_messages(conversation_id)
            
            # Convert to format expected by compressor
            message_list = []
            for row in messages:
                message_dict = dict(row)
                message_list.append(message_dict)
            
            compressor = get_context_compressor()
            return compressor.get_compression_recommendations(message_list, model_name)
            
        except Exception as e:
            logger.error(f"Error getting compression recommendations for conversation {conversation_id}: {str(e)}")
            return {'error': str(e)}
    
    @staticmethod
    def analyze_conversation_importance(conversation_id):
        """
        Analyze message importance in a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Dictionary with importance analysis results
        """
        try:
            messages = ConversationManager.get_messages(conversation_id)
            
            # Convert to format expected by compressor
            message_list = []
            for row in messages:
                message_dict = dict(row)
                message_list.append(message_dict)
            
            compressor = get_context_compressor()
            return compressor.analyze_importance(message_list)
            
        except Exception as e:
            logger.error(f"Error analyzing conversation importance {conversation_id}: {str(e)}")
            return {'error': str(e)}
    
    @staticmethod
    def get_conversation_compression_stats(conversation_id):
        """
        Get compression statistics for a specific conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Dictionary with compression statistics
        """
        try:
            compressor = get_context_compressor()
            return compressor.get_compression_status(conversation_id)
            
        except Exception as e:
            logger.error(f"Error getting compression stats for conversation {conversation_id}: {str(e)}")
            return {'error': str(e)}
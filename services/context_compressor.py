"""Context compression service for Chat-O-Llama application integration."""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from utils.compression_engine import get_compression_engine, CompressionResult
from utils.compression_strategies import CompressionContext
from utils.context_analyzer import analyze_conversation_context
from utils.token_estimation import estimate_tokens
from config.settings import get_config


logger = logging.getLogger(__name__)


class ContextCompressor:
    """Service for managing context compression in the Chat-O-Llama application."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the context compressor."""
        self.config = config or get_config().get('compression', {})
        self.engine = get_compression_engine()
        self.enabled = self.config.get('enabled', False)
        
    def compress_context(self, messages: List[Dict], 
                        conversation_id: int = None,
                        model_name: str = None,
                        max_context_tokens: int = 4096,
                        force: bool = False) -> Tuple[List[Dict], Optional[Dict[str, Any]]]:
        """
        Compress conversation context and return compressed messages with metadata.
        
        Args:
            messages: List of conversation messages
            conversation_id: Optional conversation ID for caching/tracking
            model_name: Model name for optimization
            max_context_tokens: Maximum context window size
            force: Force compression even if not needed
            
        Returns:
            Tuple of (compressed_messages, compression_metadata)
        """
        if not self.enabled and not force:
            logger.debug("Context compression disabled")
            return messages, None
        
        if not messages:
            logger.debug("No messages to compress")
            return messages, None
        
        try:
            # Check if compression is needed
            should_compress, reason = self.engine.should_compress(messages, conversation_id)
            if not should_compress and not force:
                logger.debug(f"Compression not needed: {reason}")
                return messages, {
                    'compression_applied': False,
                    'reason': reason,
                    'original_token_count': sum(estimate_tokens(msg.get('content', '')) for msg in messages),
                    'compressed_token_count': sum(estimate_tokens(msg.get('content', '')) for msg in messages),
                    'compression_ratio': 1.0,
                    'compression_time_ms': 0
                }
            
            # Perform compression
            result = self.engine.compress_conversation(
                messages=messages,
                conversation_id=conversation_id,
                model_name=model_name,
                max_context_tokens=max_context_tokens,
                force_strategy=None
            )
            
            if result:
                compression_metadata = {
                    'compression_applied': True,
                    'reason': reason if should_compress else 'forced',
                    'original_token_count': result.original_token_count,
                    'compressed_token_count': result.compressed_token_count,
                    'compression_ratio': result.compression_ratio,
                    'compression_time_ms': result.compression_time_ms,
                    'quality_score': result.quality_score,
                    'strategy_used': result.strategy_used,
                    'metadata': result.metadata,
                    'savings': self._calculate_savings(result)
                }
                
                logger.info(f"Context compressed: {result.compression_ratio:.2f} ratio, "
                           f"{compression_metadata['savings']['tokens_saved']} tokens saved")
                
                return result.compressed_messages, compression_metadata
            else:
                logger.warning("Compression failed, returning original messages")
                return messages, {
                    'compression_applied': False,
                    'reason': 'compression_failed',
                    'original_token_count': sum(estimate_tokens(msg.get('content', '')) for msg in messages),
                    'compressed_token_count': sum(estimate_tokens(msg.get('content', '')) for msg in messages),
                    'compression_ratio': 1.0,
                    'compression_time_ms': 0,
                    'error': 'Compression operation failed'
                }
                
        except Exception as e:
            logger.error(f"Context compression error: {str(e)}")
            return messages, {
                'compression_applied': False,
                'reason': 'compression_error',
                'original_token_count': sum(estimate_tokens(msg.get('content', '')) for msg in messages),
                'compressed_token_count': sum(estimate_tokens(msg.get('content', '')) for msg in messages),
                'compression_ratio': 1.0,
                'compression_time_ms': 0,
                'error': str(e)
            }
    
    def summarize_messages(self, messages: List[Dict], 
                          strategy: str = 'intelligent_summary',
                          target_length_ratio: float = 0.3) -> Tuple[str, Dict[str, Any]]:
        """
        Create a summary of conversation messages.
        
        Args:
            messages: List of messages to summarize
            strategy: Summarization strategy to use
            target_length_ratio: Target summary length as ratio of original
            
        Returns:
            Tuple of (summary_text, summary_metadata)
        """
        if not messages:
            return "", {'error': 'No messages to summarize'}
        
        try:
            # Force intelligent summary strategy for summarization
            result = self.engine.compress_conversation(
                messages=messages,
                force_strategy='intelligent_summary'
            )
            
            if result and result.compressed_messages:
                # Extract summary from compressed messages
                for msg in result.compressed_messages:
                    if msg.get('is_summary', False):
                        summary_text = msg.get('content', '').replace('[CONVERSATION SUMMARY]\n', '')
                        
                        metadata = {
                            'summary_created': True,
                            'original_message_count': len(messages),
                            'original_token_count': result.original_token_count,
                            'summary_token_count': estimate_tokens(summary_text),
                            'compression_ratio': result.compression_ratio,
                            'quality_score': result.quality_score,
                            'strategy_used': result.strategy_used,
                            'compression_time_ms': result.compression_time_ms
                        }
                        
                        return summary_text, metadata
                
                # No summary found in result
                return "", {'error': 'No summary generated in compression result'}
            else:
                return "", {'error': 'Summary generation failed'}
                
        except Exception as e:
            logger.error(f"Message summarization error: {str(e)}")
            return "", {'error': str(e)}
    
    def analyze_importance(self, messages: List[Dict]) -> List[Dict[str, Any]]:
        """
        Analyze the importance of messages in a conversation.
        
        Args:
            messages: List of messages to analyze
            
        Returns:
            List of message importance analysis results
        """
        if not messages:
            return []
        
        try:
            # Analyze conversation context
            analysis = analyze_conversation_context(messages, self.config)
            importance_scores = []
            
            for i, message in enumerate(messages):
                # Calculate importance using the analyzer
                importance = self.engine.analyzer.analyze_message_importance(
                    message, len(messages) - i - 1
                )
                
                content = message.get('content', '')
                
                analysis_result = {
                    'message_index': i,
                    'importance_score': importance,
                    'is_question': self.engine.analyzer._is_question(content),
                    'contains_code': self.engine.analyzer._contains_code(content),
                    'estimated_tokens': estimate_tokens(content),
                    'role': message.get('role', 'unknown'),
                    'timestamp': message.get('timestamp'),
                    'preservation_priority': self._calculate_preservation_priority(message, importance)
                }
                
                importance_scores.append(analysis_result)
            
            # Add conversation-level insights
            metrics = analysis['metrics']
            conversation_insights = {
                'total_messages': len(messages),
                'total_tokens': metrics.total_tokens,
                'compression_candidate': metrics.compression_candidate,
                'context_utilization': metrics.context_utilization,
                'high_importance_count': sum(1 for score in importance_scores if score['importance_score'] > 0.7),
                'medium_importance_count': sum(1 for score in importance_scores if 0.4 <= score['importance_score'] <= 0.7),
                'low_importance_count': sum(1 for score in importance_scores if score['importance_score'] < 0.4)
            }
            
            return {
                'message_importance': importance_scores,
                'conversation_insights': conversation_insights,
                'compression_candidates': analysis['compression_candidates']
            }
            
        except Exception as e:
            logger.error(f"Importance analysis error: {str(e)}")
            return {'error': str(e)}
    
    def get_compression_recommendations(self, messages: List[Dict], 
                                     model_name: str = None) -> Dict[str, Any]:
        """
        Get compression recommendations for a conversation.
        
        Args:
            messages: List of conversation messages
            model_name: Model name for optimization
            
        Returns:
            Dictionary with compression recommendations
        """
        try:
            return self.engine.get_compression_recommendations(messages, model_name)
        except Exception as e:
            logger.error(f"Error getting compression recommendations: {str(e)}")
            return {'error': str(e)}
    
    def get_compression_status(self, conversation_id: int = None) -> Dict[str, Any]:
        """
        Get compression status and statistics.
        
        Args:
            conversation_id: Optional conversation ID for specific stats
            
        Returns:
            Dictionary with compression status information
        """
        try:
            # Get compression statistics
            stats = self.engine.get_compression_stats(conversation_id)
            
            # Add current configuration status
            status = {
                'enabled': self.enabled,
                'configuration': {
                    'trigger_token_threshold': self.config.get('trigger_token_threshold', 3000),
                    'trigger_message_count': self.config.get('trigger_message_count', 20),
                    'preserve_recent_messages': self.config.get('preserve_recent_messages', 10),
                    'compression_ratio_target': self.config.get('compression_ratio_target', 0.4),
                    'strategy': self.config.get('strategy', 'rolling_window'),
                    'cache_enabled': self.config.get('cache_enabled', True)
                },
                'statistics': stats
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting compression status: {str(e)}")
            return {'error': str(e)}
    
    def cleanup_cache(self):
        """Clean up expired compression cache entries."""
        try:
            self.engine.cleanup_expired_cache()
        except Exception as e:
            logger.error(f"Error cleaning up compression cache: {str(e)}")
    
    def _calculate_preservation_priority(self, message: Dict, importance_score: float) -> str:
        """Calculate preservation priority for a message."""
        content = message.get('content', '')
        role = message.get('role', '')
        
        # High priority conditions
        if importance_score > 0.8:
            return 'critical'
        elif importance_score > 0.6:
            return 'high'
        elif (self.engine.analyzer._is_question(content) or 
              self.engine.analyzer._contains_code(content) or
              role == 'user'):
            return 'medium'
        else:
            return 'low'
    
    def _calculate_savings(self, result: CompressionResult) -> Dict[str, Any]:
        """Calculate compression savings metrics."""
        if result.original_token_count == 0:
            return {
                'tokens_saved': 0,
                'percentage_saved': 0.0,
                'estimated_cost_savings': 0.0,
                'response_time_improvement': 0.0
            }
        
        tokens_saved = result.original_token_count - result.compressed_token_count
        percentage_saved = (tokens_saved / result.original_token_count) * 100
        
        # Estimate cost savings (approximate $0.002 per 1K tokens)
        estimated_cost_savings = (tokens_saved / 1000) * 0.002
        
        # Estimate response time improvement (approximate 2ms per token saved)
        response_time_improvement = tokens_saved * 2
        
        return {
            'tokens_saved': tokens_saved,
            'percentage_saved': round(percentage_saved, 2),
            'estimated_cost_savings': round(estimated_cost_savings, 4),
            'response_time_improvement_ms': response_time_improvement
        }


# Global context compressor instance
_context_compressor = None


def get_context_compressor() -> ContextCompressor:
    """Get global context compressor instance."""
    global _context_compressor
    if _context_compressor is None:
        _context_compressor = ContextCompressor()
    return _context_compressor


def compress_conversation_context(messages: List[Dict], **kwargs) -> Tuple[List[Dict], Optional[Dict[str, Any]]]:
    """Convenience function to compress conversation context."""
    compressor = get_context_compressor()
    return compressor.compress_context(messages, **kwargs)
"""Compression execution engine for conversation context management."""

import time
import logging
import sqlite3
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

from utils.compression_strategies import (
    CompressionStrategy, CompressionResult, CompressionContext,
    get_compression_strategy, get_available_strategies
)
from utils.context_analyzer import ContextAnalyzer, analyze_conversation_context
from utils.database import DATABASE_PATH
from config.settings import get_config


logger = logging.getLogger(__name__)


class CompressionEngine:
    """Main engine for executing compression operations."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize compression engine."""
        self.config = config or get_config().get('compression', {})
        self.analyzer = ContextAnalyzer(self.config)
        self.cache_enabled = self.config.get('cache_enabled', True)
        self.cache_ttl_hours = self.config.get('cache_ttl_hours', 24)
        
    def should_compress(self, messages: List[Dict], conversation_id: int = None) -> Tuple[bool, str]:
        """Determine if compression should be applied."""
        if not self.config.get('enabled', False):
            return False, "compression_disabled"
        
        if not messages:
            return False, "no_messages"
        
        # Check if already recently compressed
        if conversation_id and self._recently_compressed(conversation_id):
            return False, "recently_compressed"
        
        # Analyze conversation metrics
        metrics = self.analyzer.analyze_conversation(messages)
        
        # Check triggers
        if metrics.compression_candidate:
            if metrics.total_tokens >= self.config.get('trigger_token_threshold', 3000):
                return True, "token_threshold"
            elif metrics.total_messages >= self.config.get('trigger_message_count', 20):
                return True, "message_threshold"
            elif metrics.context_utilization > self.config.get('trigger_utilization_percent', 80):
                return True, "utilization_threshold"
        
        return False, "no_triggers"
    
    def compress_conversation(self, messages: List[Dict], 
                            conversation_id: int = None,
                            model_name: str = None,
                            max_context_tokens: int = 4096,
                            force_strategy: str = None) -> Optional[CompressionResult]:
        """Compress a conversation using the best available strategy."""
        if not messages:
            logger.warning("No messages to compress")
            return None
        
        # Check if compression is needed
        should_compress, reason = self.should_compress(messages, conversation_id)
        if not should_compress and not force_strategy:
            logger.info(f"Compression not needed: {reason}")
            return None
        
        # Check cache first
        if self.cache_enabled and not force_strategy:
            cached_result = self._get_cached_compression(messages, conversation_id)
            if cached_result:
                logger.info("Using cached compression result")
                return cached_result
        
        # Determine best strategy
        strategy_name = force_strategy or self._select_best_strategy(messages, model_name)
        if not strategy_name:
            logger.error("No suitable compression strategy available")
            return None
        
        # Create compression context
        context = CompressionContext(
            messages=messages,
            max_context_tokens=max_context_tokens,
            preserve_recent_count=self.config.get('preserve_recent_messages', 10),
            target_compression_ratio=self.config.get('compression_ratio_target', 0.4),
            model_name=model_name,
            conversation_id=conversation_id
        )
        
        # Execute compression
        try:
            strategy = get_compression_strategy(strategy_name, self.config)
            if not strategy:
                logger.error(f"Failed to create strategy: {strategy_name}")
                return None
            
            logger.info(f"Compressing conversation using {strategy_name} strategy")
            result = strategy.compress(context)
            
            # Log compression metrics
            self._log_compression_metrics(result, conversation_id, reason)
            
            # Cache result
            if self.cache_enabled:
                self._cache_compression_result(result, messages, conversation_id)
            
            # Store performance metrics
            self._store_performance_metrics(result, strategy_name, True)
            
            logger.info(f"Compression completed: {result.compression_ratio:.2f} ratio, "
                       f"{result.quality_score:.2f} quality, {result.compression_time_ms}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Compression failed with {strategy_name}: {str(e)}")
            self._store_performance_metrics(None, strategy_name, False, str(e))
            return None
    
    def get_compression_recommendations(self, messages: List[Dict], 
                                     model_name: str = None) -> Dict[str, Any]:
        """Get compression recommendations without executing compression."""
        if not messages:
            return {'recommended': False, 'reason': 'no_messages'}
        
        # Analyze conversation
        analysis = analyze_conversation_context(messages, self.config)
        metrics = analysis['metrics']
        
        # Check each available strategy
        available_strategies = get_available_strategies(self.config)
        strategy_evaluations = {}
        
        for strategy_name in available_strategies:
            strategy = get_compression_strategy(strategy_name, self.config)
            if strategy:
                context = CompressionContext(
                    messages=messages,
                    max_context_tokens=4096,
                    preserve_recent_count=self.config.get('preserve_recent_messages', 10),
                    target_compression_ratio=self.config.get('compression_ratio_target', 0.4),
                    model_name=model_name
                )
                
                can_compress = strategy.can_compress(context)
                estimated_time = strategy.estimate_compression_time(context)
                
                strategy_evaluations[strategy_name] = {
                    'available': can_compress,
                    'estimated_time_ms': estimated_time,
                    'estimated_ratio': self._estimate_compression_ratio(strategy_name, len(messages))
                }
        
        # Determine recommendation
        should_compress, reason = self.should_compress(messages)
        recommended_strategy = self._select_best_strategy(messages, model_name) if should_compress else None
        
        return {
            'recommended': should_compress,
            'reason': reason,
            'recommended_strategy': recommended_strategy,
            'conversation_metrics': {
                'total_messages': metrics.total_messages,
                'total_tokens': metrics.total_tokens,
                'context_utilization': metrics.context_utilization,
                'compression_candidate': metrics.compression_candidate
            },
            'available_strategies': strategy_evaluations,
            'compression_candidates': analysis['compression_candidates']
        }
    
    def _select_best_strategy(self, messages: List[Dict], model_name: str = None) -> Optional[str]:
        """Select the best compression strategy for the given context."""
        available_strategies = get_available_strategies(self.config)
        
        if not available_strategies:
            return None
        
        # Get configured strategy preference
        preferred_strategy = self.config.get('strategy', 'rolling_window')
        if preferred_strategy in available_strategies:
            strategy = get_compression_strategy(preferred_strategy, self.config)
            if strategy:
                context = CompressionContext(
                    messages=messages,
                    max_context_tokens=4096,
                    preserve_recent_count=self.config.get('preserve_recent_messages', 10),
                    target_compression_ratio=self.config.get('compression_ratio_target', 0.4),
                    model_name=model_name
                )
                
                if strategy.can_compress(context):
                    return preferred_strategy
        
        # Fallback: find first available strategy
        for strategy_name in available_strategies:
            strategy = get_compression_strategy(strategy_name, self.config)
            if strategy:
                context = CompressionContext(
                    messages=messages,
                    max_context_tokens=4096,
                    preserve_recent_count=self.config.get('preserve_recent_messages', 10),
                    target_compression_ratio=self.config.get('compression_ratio_target', 0.4),
                    model_name=model_name
                )
                
                if strategy.can_compress(context):
                    return strategy_name
        
        return None
    
    def _estimate_compression_ratio(self, strategy_name: str, message_count: int) -> float:
        """Estimate compression ratio for a strategy."""
        # Historical averages based on strategy
        estimates = {
            'rolling_window': 0.4,
            'intelligent_summary': 0.3,
            'hybrid': 0.35
        }
        
        base_ratio = estimates.get(strategy_name, 0.4)
        
        # Adjust based on message count
        if message_count > 50:
            base_ratio -= 0.1  # Better compression for longer conversations
        elif message_count < 20:
            base_ratio += 0.1  # Less compression for shorter conversations
        
        return max(0.1, min(0.8, base_ratio))
    
    def _recently_compressed(self, conversation_id: int) -> bool:
        """Check if conversation was recently compressed."""
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                # Check for recent compression
                cutoff_time = datetime.now() - timedelta(hours=1)
                cursor.execute("""
                    SELECT COUNT(*) FROM conversation_compression_stats 
                    WHERE conversation_id = ? AND compression_timestamp > ?
                """, (conversation_id, cutoff_time.isoformat()))
                
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            logger.error(f"Error checking recent compression: {e}")
            return False
    
    def _get_cached_compression(self, messages: List[Dict], 
                              conversation_id: int = None) -> Optional[CompressionResult]:
        """Get cached compression result if available."""
        try:
            from utils.compression_strategies import CompressionStrategy
            
            # Create hash for messages
            strategy = get_compression_strategy('rolling_window', self.config)
            if not strategy:
                return None
            
            context_hash = strategy._create_compression_hash(messages)
            
            with sqlite3.connect(DATABASE_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Look for cached result
                cursor.execute("""
                    SELECT * FROM compression_cache 
                    WHERE context_hash = ? AND expires_at > datetime('now')
                    ORDER BY created_at DESC LIMIT 1
                """, (context_hash,))
                
                row = cursor.fetchone()
                if row:
                    # Update access count
                    cursor.execute("""
                        UPDATE compression_cache 
                        SET access_count = access_count + 1, 
                            last_accessed = datetime('now')
                        WHERE id = ?
                    """, (row['id'],))
                    conn.commit()
                    
                    # Parse cached result
                    import json
                    compressed_messages = json.loads(row['compressed_context'])
                    
                    return CompressionResult(
                        compressed_messages=compressed_messages,
                        original_token_count=row['original_token_count'],
                        compressed_token_count=row['compressed_token_count'],
                        compression_ratio=row['compressed_token_count'] / row['original_token_count'],
                        compression_time_ms=0,  # Cached, no time
                        quality_score=0.8,  # Assume good quality for cached
                        strategy_used=row['compression_strategy'],
                        metadata={'cached': True, 'cache_id': row['id']}
                    )
                
        except Exception as e:
            logger.error(f"Error retrieving cached compression: {e}")
        
        return None
    
    def _cache_compression_result(self, result: CompressionResult, 
                                messages: List[Dict], 
                                conversation_id: int = None):
        """Cache compression result."""
        try:
            from utils.compression_strategies import CompressionStrategy
            import json
            
            strategy = get_compression_strategy('rolling_window', self.config)
            if not strategy:
                return
            
            context_hash = strategy._create_compression_hash(messages)
            expires_at = datetime.now() + timedelta(hours=self.cache_ttl_hours)
            
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO compression_cache 
                    (conversation_id, context_hash, compressed_context, 
                     original_token_count, compressed_token_count, 
                     compression_strategy, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    conversation_id,
                    context_hash,
                    json.dumps(result.compressed_messages),
                    result.original_token_count,
                    result.compressed_token_count,
                    result.strategy_used,
                    expires_at.isoformat()
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error caching compression result: {e}")
    
    def _log_compression_metrics(self, result: CompressionResult, 
                               conversation_id: int = None, 
                               trigger_reason: str = None):
        """Log compression metrics to database."""
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO conversation_compression_stats 
                    (conversation_id, original_token_count, compressed_token_count, 
                     compression_ratio, compression_strategy, compression_time_ms, 
                     quality_score, messages_compressed, messages_preserved, 
                     triggered_by, compression_config, effectiveness_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    conversation_id,
                    result.original_token_count,
                    result.compressed_token_count,
                    result.compression_ratio,
                    result.strategy_used,
                    result.compression_time_ms,
                    result.quality_score,
                    len(result.compressed_messages),
                    result.metadata.get('recent_preserved', 0),
                    trigger_reason,
                    str(result.metadata),
                    result.quality_score * result.compression_ratio  # Effectiveness
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error logging compression metrics: {e}")
    
    def _store_performance_metrics(self, result: Optional[CompressionResult], 
                                 strategy_name: str, 
                                 success: bool, 
                                 error_message: str = None):
        """Store performance metrics for monitoring."""
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO compression_performance_metrics 
                    (compression_strategy, operation_type, duration_ms, 
                     input_token_count, output_token_count, compression_ratio, 
                     quality_score, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy_name,
                    'compression',
                    result.compression_time_ms if result else 0,
                    result.original_token_count if result else 0,
                    result.compressed_token_count if result else None,
                    result.compression_ratio if result else None,
                    result.quality_score if result else None,
                    success,
                    error_message
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error storing performance metrics: {e}")
    
    def cleanup_expired_cache(self):
        """Clean up expired cache entries."""
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM compression_cache 
                    WHERE expires_at < datetime('now')
                """)
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired cache entries")
                
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
    
    def get_compression_stats(self, conversation_id: int = None, 
                            days: int = 7) -> Dict[str, Any]:
        """Get compression statistics."""
        try:
            from utils.database import get_compression_stats
            return get_compression_stats(conversation_id, days)
        except Exception as e:
            logger.error(f"Error getting compression stats: {e}")
            return {}


# Global compression engine instance
_compression_engine = None


def get_compression_engine() -> CompressionEngine:
    """Get global compression engine instance."""
    global _compression_engine
    if _compression_engine is None:
        _compression_engine = CompressionEngine()
    return _compression_engine


def compress_conversation(messages: List[Dict], **kwargs) -> Optional[CompressionResult]:
    """Convenience function to compress a conversation."""
    engine = get_compression_engine()
    return engine.compress_conversation(messages, **kwargs)


def should_compress_conversation(messages: List[Dict], **kwargs) -> Tuple[bool, str]:
    """Convenience function to check if compression is needed."""
    engine = get_compression_engine()
    return engine.should_compress(messages, **kwargs)
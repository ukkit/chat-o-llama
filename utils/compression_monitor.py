"""Performance monitoring and optimization for compression system."""

import time
import logging
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, deque

from utils.database import DATABASE_PATH


logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for compression operations."""
    strategy_name: str
    avg_duration_ms: float
    avg_compression_ratio: float
    avg_quality_score: float
    success_rate: float
    total_operations: int
    tokens_processed: int
    tokens_saved: int
    last_updated: datetime


@dataclass
class CompressionAlert:
    """Alert for compression performance issues."""
    alert_type: str
    message: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    timestamp: datetime
    strategy_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None


class CompressionMonitor:
    """Monitor compression performance and provide optimization recommendations."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize compression monitor."""
        self.config = config or {}
        self.performance_thresholds = {
            'max_duration_ms': self.config.get('max_duration_ms', 5000),
            'min_compression_ratio': self.config.get('min_compression_ratio', 0.1),
            'min_quality_score': self.config.get('min_quality_score', 0.3),
            'min_success_rate': self.config.get('min_success_rate', 0.85),
            'max_failure_rate': self.config.get('max_failure_rate', 0.15)
        }
        
        # In-memory performance tracking
        self.recent_operations = deque(maxlen=1000)
        self.strategy_stats = defaultdict(lambda: {
            'durations': deque(maxlen=100),
            'ratios': deque(maxlen=100),
            'qualities': deque(maxlen=100),
            'successes': deque(maxlen=100)
        })
    
    def record_operation(self, strategy_name: str, duration_ms: int, 
                        compression_ratio: Optional[float] = None,
                        quality_score: Optional[float] = None,
                        success: bool = True,
                        tokens_processed: int = 0,
                        error_message: str = None):
        """Record a compression operation for monitoring."""
        timestamp = datetime.now()
        
        # Record in memory for quick access
        operation = {
            'timestamp': timestamp,
            'strategy': strategy_name,
            'duration_ms': duration_ms,
            'compression_ratio': compression_ratio,
            'quality_score': quality_score,
            'success': success,
            'tokens_processed': tokens_processed,
            'error_message': error_message
        }
        
        self.recent_operations.append(operation)
        
        # Update strategy-specific stats
        stats = self.strategy_stats[strategy_name]
        stats['durations'].append(duration_ms)
        stats['successes'].append(success)
        
        if compression_ratio is not None:
            stats['ratios'].append(compression_ratio)
        if quality_score is not None:
            stats['qualities'].append(quality_score)
        
        # Store in database for persistence
        self._store_performance_metric(
            strategy_name, duration_ms, compression_ratio, 
            quality_score, success, tokens_processed, error_message
        )
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the specified time period."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with sqlite3.connect(DATABASE_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get overall metrics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_operations,
                        AVG(duration_ms) as avg_duration,
                        AVG(compression_ratio) as avg_ratio,
                        AVG(quality_score) as avg_quality,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as success_rate,
                        SUM(input_token_count) as total_tokens_processed,
                        SUM(input_token_count - COALESCE(output_token_count, input_token_count)) as total_tokens_saved
                    FROM compression_performance_metrics 
                    WHERE timestamp > ?
                """, (cutoff_time.isoformat(),))
                
                overall = dict(cursor.fetchone() or {})
                
                # Get per-strategy metrics
                cursor.execute("""
                    SELECT 
                        compression_strategy,
                        COUNT(*) as operations,
                        AVG(duration_ms) as avg_duration,
                        AVG(compression_ratio) as avg_ratio,
                        AVG(quality_score) as avg_quality,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as success_rate
                    FROM compression_performance_metrics 
                    WHERE timestamp > ?
                    GROUP BY compression_strategy
                    ORDER BY operations DESC
                """, (cutoff_time.isoformat(),))
                
                by_strategy = [dict(row) for row in cursor.fetchall()]
                
                # Get recent errors
                cursor.execute("""
                    SELECT 
                        compression_strategy,
                        error_message,
                        timestamp,
                        COUNT(*) as error_count
                    FROM compression_performance_metrics 
                    WHERE timestamp > ? AND success = 0 AND error_message IS NOT NULL
                    GROUP BY compression_strategy, error_message
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, (cutoff_time.isoformat(),))
                
                recent_errors = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'period_hours': hours,
                    'overall': overall,
                    'by_strategy': by_strategy,
                    'recent_errors': recent_errors,
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}
    
    def get_strategy_metrics(self, strategy_name: str, hours: int = 24) -> PerformanceMetrics:
        """Get detailed metrics for a specific strategy."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with sqlite3.connect(DATABASE_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_operations,
                        AVG(duration_ms) as avg_duration,
                        AVG(compression_ratio) as avg_ratio,
                        AVG(quality_score) as avg_quality,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as success_rate,
                        SUM(input_token_count) as tokens_processed,
                        SUM(input_token_count - COALESCE(output_token_count, input_token_count)) as tokens_saved,
                        MAX(timestamp) as last_operation
                    FROM compression_performance_metrics 
                    WHERE compression_strategy = ? AND timestamp > ?
                """, (strategy_name, cutoff_time.isoformat()))
                
                row = cursor.fetchone()
                
                if not row or row['total_operations'] == 0:
                    return PerformanceMetrics(
                        strategy_name=strategy_name,
                        avg_duration_ms=0.0,
                        avg_compression_ratio=0.0,
                        avg_quality_score=0.0,
                        success_rate=0.0,
                        total_operations=0,
                        tokens_processed=0,
                        tokens_saved=0,
                        last_updated=datetime.now()
                    )
                
                return PerformanceMetrics(
                    strategy_name=strategy_name,
                    avg_duration_ms=row['avg_duration'] or 0.0,
                    avg_compression_ratio=row['avg_ratio'] or 0.0,
                    avg_quality_score=row['avg_quality'] or 0.0,
                    success_rate=row['success_rate'] or 0.0,
                    total_operations=row['total_operations'] or 0,
                    tokens_processed=row['tokens_processed'] or 0,
                    tokens_saved=row['tokens_saved'] or 0,
                    last_updated=datetime.fromisoformat(row['last_operation']) if row['last_operation'] else datetime.now()
                )
                
        except Exception as e:
            logger.error(f"Error getting strategy metrics for {strategy_name}: {e}")
            return PerformanceMetrics(
                strategy_name=strategy_name,
                avg_duration_ms=0.0,
                avg_compression_ratio=0.0,
                avg_quality_score=0.0,
                success_rate=0.0,
                total_operations=0,
                tokens_processed=0,
                tokens_saved=0,
                last_updated=datetime.now()
            )
    
    def check_performance_alerts(self, hours: int = 1) -> List[CompressionAlert]:
        """Check for performance issues and generate alerts."""
        alerts = []
        
        try:
            # Get recent performance metrics
            summary = self.get_performance_summary(hours)
            
            if not summary.get('overall'):
                return alerts
            
            overall = summary['overall']
            
            # Check overall performance
            if overall.get('avg_duration', 0) > self.performance_thresholds['max_duration_ms']:
                alerts.append(CompressionAlert(
                    alert_type='high_duration',
                    message=f"Average compression duration ({overall['avg_duration']:.0f}ms) exceeds threshold ({self.performance_thresholds['max_duration_ms']}ms)",
                    severity='medium',
                    timestamp=datetime.now(),
                    metric_value=overall['avg_duration'],
                    threshold=self.performance_thresholds['max_duration_ms']
                ))
            
            if overall.get('success_rate', 1.0) < self.performance_thresholds['min_success_rate']:
                severity = 'critical' if overall['success_rate'] < 0.5 else 'high'
                alerts.append(CompressionAlert(
                    alert_type='low_success_rate',
                    message=f"Compression success rate ({overall['success_rate']:.2%}) below threshold ({self.performance_thresholds['min_success_rate']:.2%})",
                    severity=severity,
                    timestamp=datetime.now(),
                    metric_value=overall['success_rate'],
                    threshold=self.performance_thresholds['min_success_rate']
                ))
            
            # Check per-strategy performance
            for strategy in summary.get('by_strategy', []):
                strategy_name = strategy['compression_strategy']
                
                if strategy.get('avg_duration', 0) > self.performance_thresholds['max_duration_ms']:
                    alerts.append(CompressionAlert(
                        alert_type='strategy_high_duration',
                        message=f"Strategy {strategy_name} duration ({strategy['avg_duration']:.0f}ms) exceeds threshold",
                        severity='low',
                        timestamp=datetime.now(),
                        strategy_name=strategy_name,
                        metric_value=strategy['avg_duration'],
                        threshold=self.performance_thresholds['max_duration_ms']
                    ))
                
                if strategy.get('success_rate', 1.0) < self.performance_thresholds['min_success_rate']:
                    alerts.append(CompressionAlert(
                        alert_type='strategy_low_success_rate',
                        message=f"Strategy {strategy_name} success rate ({strategy['success_rate']:.2%}) below threshold",
                        severity='medium',
                        timestamp=datetime.now(),
                        strategy_name=strategy_name,
                        metric_value=strategy['success_rate'],
                        threshold=self.performance_thresholds['min_success_rate']
                    ))
            
            # Check for frequent errors
            recent_errors = summary.get('recent_errors', [])
            if len(recent_errors) >= 5:
                alerts.append(CompressionAlert(
                    alert_type='frequent_errors',
                    message=f"High error frequency: {len(recent_errors)} different error types in last {hours}h",
                    severity='high',
                    timestamp=datetime.now(),
                    metric_value=len(recent_errors)
                ))
            
        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")
            alerts.append(CompressionAlert(
                alert_type='monitoring_error',
                message=f"Failed to check performance alerts: {str(e)}",
                severity='medium',
                timestamp=datetime.now()
            ))
        
        return alerts
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations based on performance data."""
        recommendations = []
        
        try:
            # Get performance summary for analysis
            summary = self.get_performance_summary(hours=24)
            
            if not summary.get('by_strategy'):
                return recommendations
            
            strategies = summary['by_strategy']
            
            # Analyze strategy performance
            for strategy in strategies:
                strategy_name = strategy['compression_strategy']
                
                # Recommend switching away from slow strategies
                if strategy.get('avg_duration', 0) > 2000:  # > 2 seconds
                    recommendations.append({
                        'type': 'strategy_optimization',
                        'priority': 'medium',
                        'title': f'Optimize {strategy_name} performance',
                        'description': f'Strategy {strategy_name} has high average duration ({strategy["avg_duration"]:.0f}ms). Consider using rolling_window for better performance.',
                        'action': f'Switch to rolling_window strategy or optimize {strategy_name} configuration',
                        'strategy': strategy_name
                    })
                
                # Recommend configuration tuning for poor quality
                if strategy.get('avg_quality', 0) < 0.5:
                    recommendations.append({
                        'type': 'quality_optimization',
                        'priority': 'low',
                        'title': f'Improve {strategy_name} quality',
                        'description': f'Strategy {strategy_name} has low average quality score ({strategy["avg_quality"]:.2f}). Consider adjusting configuration parameters.',
                        'action': f'Tune {strategy_name} parameters like importance_threshold or preserve_recent_messages',
                        'strategy': strategy_name
                    })
                
                # Recommend disabling unreliable strategies
                if strategy.get('success_rate', 1.0) < 0.7:
                    recommendations.append({
                        'type': 'reliability_optimization',
                        'priority': 'high',
                        'title': f'Address {strategy_name} reliability issues',
                        'description': f'Strategy {strategy_name} has low success rate ({strategy["success_rate"]:.2%}). Check configuration and dependencies.',
                        'action': f'Review {strategy_name} configuration, check LLM backend availability, or temporarily disable strategy',
                        'strategy': strategy_name
                    })
            
            # Recommend enabling compression if not being used
            overall = summary.get('overall', {})
            if overall.get('total_operations', 0) == 0:
                recommendations.append({
                    'type': 'usage_optimization',
                    'priority': 'low',
                    'title': 'Enable compression for better context management',
                    'description': 'No compression operations detected. Enabling compression can help manage long conversations more efficiently.',
                    'action': 'Review compression configuration and ensure it\'s enabled with appropriate triggers'
                })
            
            # Recommend caching if not being used effectively
            elif overall.get('total_operations', 0) > 100:
                recommendations.append({
                    'type': 'caching_optimization',
                    'priority': 'low',
                    'title': 'Consider optimizing compression caching',
                    'description': f'High compression volume ({overall["total_operations"]} operations). Ensure caching is enabled to reduce redundant compression.',
                    'action': 'Verify compression caching is enabled and tune cache TTL settings'
                })
            
        except Exception as e:
            logger.error(f"Error generating optimization recommendations: {e}")
            recommendations.append({
                'type': 'error',
                'priority': 'medium',
                'title': 'Failed to generate recommendations',
                'description': f'Error analyzing performance data: {str(e)}',
                'action': 'Check compression monitoring configuration and database connectivity'
            })
        
        return recommendations
    
    def cleanup_old_metrics(self, days_to_keep: int = 30):
        """Clean up old performance metrics to prevent database bloat."""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM compression_performance_metrics 
                    WHERE timestamp < ?
                """, (cutoff_time.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old performance metrics (older than {days_to_keep} days)")
                
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {e}")
    
    def _store_performance_metric(self, strategy_name: str, duration_ms: int,
                                compression_ratio: Optional[float],
                                quality_score: Optional[float],
                                success: bool,
                                tokens_processed: int,
                                error_message: Optional[str]):
        """Store performance metric in database."""
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
                    duration_ms,
                    tokens_processed,
                    int(tokens_processed * compression_ratio) if compression_ratio else None,
                    compression_ratio,
                    quality_score,
                    success,
                    error_message
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error storing performance metric: {e}")


# Global monitor instance
_compression_monitor = None


def get_compression_monitor() -> CompressionMonitor:
    """Get global compression monitor instance."""
    global _compression_monitor
    if _compression_monitor is None:
        _compression_monitor = CompressionMonitor()
    return _compression_monitor


def record_compression_operation(strategy_name: str, **kwargs):
    """Convenience function to record compression operation."""
    monitor = get_compression_monitor()
    monitor.record_operation(strategy_name, **kwargs)


def get_performance_summary(**kwargs) -> Dict[str, Any]:
    """Convenience function to get performance summary."""
    monitor = get_compression_monitor()
    return monitor.get_performance_summary(**kwargs)


def check_performance_alerts(**kwargs) -> List[CompressionAlert]:
    """Convenience function to check performance alerts."""
    monitor = get_compression_monitor()
    return monitor.check_performance_alerts(**kwargs)
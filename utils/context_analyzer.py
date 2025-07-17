"""Context analysis utilities for conversation compression and optimization."""

import re
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from utils.token_estimation import estimate_tokens


@dataclass
class ConversationMetrics:
    """Metrics for a conversation context."""
    total_messages: int
    total_tokens: int
    user_messages: int
    assistant_messages: int
    average_message_length: float
    context_utilization: float  # Percentage of context window used
    conversation_age_minutes: float
    last_activity: datetime
    compression_candidate: bool


@dataclass
class ContextWindow:
    """Represents a context window with token limits."""
    max_tokens: int
    current_tokens: int
    remaining_tokens: int
    utilization_percent: float
    
    @property
    def is_near_limit(self) -> bool:
        """Check if context is near token limit (>80%)."""
        return self.utilization_percent > 80.0
    
    @property
    def requires_compression(self) -> bool:
        """Check if context requires compression (>90%)."""
        return self.utilization_percent > 90.0


class ContextAnalyzer:
    """Analyzes conversation context for compression opportunities."""
    
    def __init__(self, compression_config: Optional[Dict] = None):
        """Initialize context analyzer with compression configuration."""
        self.compression_config = compression_config or {}
        self.token_threshold = self.compression_config.get('trigger_token_threshold', 3000)
        self.message_threshold = self.compression_config.get('trigger_message_count', 20)
        self.preserve_recent = self.compression_config.get('preserve_recent_messages', 10)
        
    def analyze_conversation(self, messages: List[Dict], max_context_tokens: int = 4096) -> ConversationMetrics:
        """Analyze a conversation for compression opportunities."""
        if not messages:
            return self._empty_metrics()
            
        # Count messages by role
        user_messages = sum(1 for msg in messages if msg.get('role') == 'user')
        assistant_messages = sum(1 for msg in messages if msg.get('role') == 'assistant')
        total_messages = len(messages)
        
        # Calculate token counts
        total_tokens = 0
        message_lengths = []
        
        for message in messages:
            content = message.get('content', '')
            tokens = self._estimate_message_tokens(message)
            total_tokens += tokens
            message_lengths.append(len(content))
        
        # Calculate metrics
        avg_length = sum(message_lengths) / len(message_lengths) if message_lengths else 0
        context_utilization = (total_tokens / max_context_tokens) * 100
        
        # Calculate conversation age
        oldest_timestamp = self._get_oldest_timestamp(messages)
        conversation_age = self._calculate_age_minutes(oldest_timestamp)
        
        # Determine if compression is needed
        compression_candidate = self._should_compress(
            total_messages, total_tokens, context_utilization
        )
        
        return ConversationMetrics(
            total_messages=total_messages,
            total_tokens=total_tokens,
            user_messages=user_messages,
            assistant_messages=assistant_messages,
            average_message_length=avg_length,
            context_utilization=context_utilization,
            conversation_age_minutes=conversation_age,
            last_activity=self._get_latest_timestamp(messages),
            compression_candidate=compression_candidate
        )
    
    def analyze_context_window(self, messages: List[Dict], max_tokens: int = 4096) -> ContextWindow:
        """Analyze current context window utilization."""
        current_tokens = sum(self._estimate_message_tokens(msg) for msg in messages)
        remaining_tokens = max(0, max_tokens - current_tokens)
        utilization_percent = (current_tokens / max_tokens) * 100
        
        return ContextWindow(
            max_tokens=max_tokens,
            current_tokens=current_tokens,
            remaining_tokens=remaining_tokens,
            utilization_percent=utilization_percent
        )
    
    def analyze_message_importance(self, message: Dict, position_from_end: int) -> float:
        """Analyze importance score of a message (0.0 to 1.0)."""
        content = message.get('content', '')
        role = message.get('role', '')
        
        # Base importance score - start lower for assistant messages
        importance = 0.3 if role == 'assistant' else 0.5
        
        # Recent messages are more important
        recency_boost = max(0, 1.0 - (position_from_end / 20))
        importance += recency_boost * 0.2
        
        # User questions are important
        if role == 'user':
            importance += 0.2
            if self._is_question(content):
                importance += 0.1
        
        # Technical content is important
        if self._contains_code(content):
            importance += 0.2
        
        # Long, detailed responses are important
        if len(content) > 500:
            importance += 0.1
        
        # Specific keywords indicate importance
        important_keywords = ['error', 'bug', 'fix', 'solution', 'important', 'critical']
        if any(keyword.lower() in content.lower() for keyword in important_keywords):
            importance += 0.15  # Increased from 0.1 to give more weight to important content
        
        # Generic responses are less important
        generic_patterns = ['general response', 'just a', 'number']
        if any(pattern.lower() in content.lower() for pattern in generic_patterns):
            importance -= 0.2
        
        return min(1.0, importance)
    
    def identify_compression_candidates(self, messages: List[Dict]) -> List[Tuple[int, str]]:
        """Identify messages that are candidates for compression."""
        candidates = []
        
        for i, message in enumerate(messages):
            # Skip recent messages (preserve them)
            if i >= len(messages) - self.preserve_recent:
                continue
                
            importance = self.analyze_message_importance(message, len(messages) - i - 1)
            
            # Low importance messages are compression candidates
            if importance < 0.4:
                reason = self._get_compression_reason(message, importance)
                candidates.append((i, reason))
        
        return candidates
    
    def get_sliding_window(self, messages: List[Dict], window_size: int = None) -> List[Dict]:
        """Get a sliding window of recent messages."""
        if window_size is None:
            window_size = self.preserve_recent
        
        return messages[-window_size:] if messages else []
    
    def calculate_compression_savings(self, original_tokens: int, compressed_tokens: int) -> Dict[str, float]:
        """Calculate compression savings metrics."""
        if original_tokens == 0:
            return {'ratio': 0.0, 'savings_percent': 0.0, 'tokens_saved': 0}
        
        ratio = compressed_tokens / original_tokens
        savings_percent = ((original_tokens - compressed_tokens) / original_tokens) * 100
        tokens_saved = original_tokens - compressed_tokens
        
        return {
            'ratio': ratio,
            'savings_percent': savings_percent,
            'tokens_saved': tokens_saved
        }
    
    def _estimate_message_tokens(self, message: Dict) -> int:
        """Estimate tokens for a single message including metadata."""
        content = message.get('content', '')
        role = message.get('role', '')
        
        # Base content tokens
        content_tokens = estimate_tokens(content)
        
        # Add tokens for role and formatting
        role_tokens = estimate_tokens(f"Role: {role}\n")
        
        # Add some overhead for message structure
        overhead_tokens = 5
        
        return content_tokens + role_tokens + overhead_tokens
    
    def _should_compress(self, message_count: int, token_count: int, utilization: float) -> bool:
        """Determine if conversation should be compressed."""
        return (
            message_count >= self.message_threshold or
            token_count >= self.token_threshold or
            utilization > 80.0
        )
    
    def _is_question(self, content: str) -> bool:
        """Check if content is likely a question."""
        question_patterns = [
            r'\?$',  # Ends with question mark
            r'^(what|how|why|when|where|who|which|can|could|would|should|is|are|do|does|did)',
            r'(help|explain|tell me|show me|guide)'
        ]
        
        content_lower = content.lower().strip()
        return any(re.search(pattern, content_lower) for pattern in question_patterns)
    
    def _contains_code(self, content: str) -> bool:
        """Check if content contains code blocks or technical content."""
        code_indicators = [
            r'```',  # Code blocks
            r'`[^`]+`',  # Inline code
            r'\bdef\s+\w+\s*\(|\bclass\s+\w+|\bfunction\s+\w+|\bvar\s+\w+|\blet\s+\w+|\bconst\s+\w+',  # Programming keywords with context
            r'\bSELECT\s+.*\bFROM\b|\bINSERT\s+INTO\b|\bUPDATE\s+.*\bSET\b|\bDELETE\s+FROM\b',  # SQL patterns with context
            r'{\s*["\w]+\s*:\s*["\w]',  # JSON-like structures with values
            r'<\w+[^>]*>.*</\w+>|<\w+\s+[^>]*/>',  # HTML/XML tags with content
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in code_indicators)
    
    def _get_compression_reason(self, message: Dict, importance: float) -> str:
        """Get reason why message is a compression candidate."""
        content = message.get('content', '')
        
        # Check length first
        if len(content) < 50:
            return "short_message"
        
        # Check importance score
        if importance < 0.2:
            return "low_importance"
        
        # Check if it's technical content
        if not self._contains_code(content) and not self._is_question(content):
            return "non_technical"
        
        return "general"
    
    def _get_oldest_timestamp(self, messages: List[Dict]) -> Optional[datetime]:
        """Get the oldest timestamp from messages."""
        if not messages:
            return None
        
        # Try to get timestamp from first message
        first_msg = messages[0]
        timestamp_str = first_msg.get('timestamp')
        
        if timestamp_str:
            try:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        # Fallback to current time minus estimated age
        return datetime.now()
    
    def _get_latest_timestamp(self, messages: List[Dict]) -> datetime:
        """Get the latest timestamp from messages."""
        if not messages:
            return datetime.now()
        
        # Try to get timestamp from last message
        last_msg = messages[-1]
        timestamp_str = last_msg.get('timestamp')
        
        if timestamp_str:
            try:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        return datetime.now()
    
    def _calculate_age_minutes(self, oldest_timestamp: Optional[datetime]) -> float:
        """Calculate conversation age in minutes."""
        if oldest_timestamp is None:
            return 0.0
        
        # Make both timestamps timezone-aware or timezone-naive for comparison
        current_time = datetime.now()
        if oldest_timestamp.tzinfo is not None:
            # If oldest has timezone info, make current time timezone-aware
            from datetime import timezone
            current_time = datetime.now(timezone.utc)
        elif hasattr(oldest_timestamp, 'tzinfo') and oldest_timestamp.tzinfo is not None:
            # Remove timezone info from oldest if current is naive
            oldest_timestamp = oldest_timestamp.replace(tzinfo=None)
        
        age_delta = current_time - oldest_timestamp
        return age_delta.total_seconds() / 60
    
    def _empty_metrics(self) -> ConversationMetrics:
        """Return empty metrics for empty conversations."""
        return ConversationMetrics(
            total_messages=0,
            total_tokens=0,
            user_messages=0,
            assistant_messages=0,
            average_message_length=0.0,
            context_utilization=0.0,
            conversation_age_minutes=0.0,
            last_activity=datetime.now(),
            compression_candidate=False
        )


def analyze_conversation_context(messages: List[Dict], config: Optional[Dict] = None) -> Dict:
    """Convenience function to analyze conversation context."""
    analyzer = ContextAnalyzer(config)
    metrics = analyzer.analyze_conversation(messages)
    context_window = analyzer.analyze_context_window(messages)
    compression_candidates = analyzer.identify_compression_candidates(messages)
    
    return {
        'metrics': metrics,
        'context_window': context_window,
        'compression_candidates': compression_candidates,
        'analysis_timestamp': datetime.now().isoformat()
    }
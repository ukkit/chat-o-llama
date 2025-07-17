"""Compression strategies for conversation context management."""

import json
import time
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from utils.context_analyzer import ContextAnalyzer, ConversationMetrics
from utils.token_estimation import estimate_tokens


@dataclass
class CompressionResult:
    """Result of a compression operation."""
    compressed_messages: List[Dict]
    original_token_count: int
    compressed_token_count: int
    compression_ratio: float
    compression_time_ms: int
    quality_score: float
    strategy_used: str
    metadata: Dict[str, Any]


@dataclass
class CompressionContext:
    """Context information for compression operations."""
    messages: List[Dict]
    max_context_tokens: int
    preserve_recent_count: int
    target_compression_ratio: float
    model_name: Optional[str] = None
    conversation_id: Optional[int] = None


class CompressionStrategy(ABC):
    """Abstract base class for compression strategies."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize strategy with configuration."""
        self.config = config
        self.analyzer = ContextAnalyzer(config)
        
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this compression strategy."""
        pass
    
    @abstractmethod
    def can_compress(self, context: CompressionContext) -> bool:
        """Check if this strategy can compress the given context."""
        pass
    
    @abstractmethod
    def compress(self, context: CompressionContext) -> CompressionResult:
        """Compress the conversation context."""
        pass
    
    def estimate_compression_time(self, context: CompressionContext) -> int:
        """Estimate compression time in milliseconds."""
        # Base estimation: 1ms per message
        return len(context.messages)
    
    def calculate_quality_score(self, original_messages: List[Dict], 
                              compressed_messages: List[Dict],
                              preserved_info: Dict[str, Any]) -> float:
        """Calculate quality score for compression (0.0 to 1.0)."""
        if not original_messages or not compressed_messages:
            return 0.0
        
        # Base score starts at 0.5
        quality = 0.5
        
        # Penalize excessive compression
        compression_ratio = len(compressed_messages) / len(original_messages)
        if compression_ratio < 0.1:  # Too aggressive
            quality -= 0.3
        elif compression_ratio < 0.3:  # Very aggressive
            quality -= 0.1
        elif compression_ratio > 0.8:  # Too conservative
            quality -= 0.2
        else:  # Good compression
            quality += 0.2
        
        # Reward preservation of important content
        if preserved_info.get('questions_preserved', 0) > 0:
            quality += 0.1
        if preserved_info.get('code_preserved', 0) > 0:
            quality += 0.1
        if preserved_info.get('recent_preserved', 0) > 0:
            quality += 0.1
        
        # Penalize loss of critical information
        if preserved_info.get('critical_loss', 0) > 0:
            quality -= 0.2
        
        return max(0.0, min(1.0, quality))
    
    def _calculate_tokens(self, messages: List[Dict]) -> int:
        """Calculate total tokens for a list of messages."""
        return sum(estimate_tokens(msg.get('content', '')) for msg in messages)
    
    def _create_compression_hash(self, messages: List[Dict]) -> str:
        """Create a hash for the compression input."""
        content = json.dumps([msg.get('content', '') for msg in messages], sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
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


class RollingWindowStrategy(CompressionStrategy):
    """Rolling window compression strategy."""
    
    def get_strategy_name(self) -> str:
        return "rolling_window"
    
    def can_compress(self, context: CompressionContext) -> bool:
        """Check if rolling window compression is applicable."""
        config = self.config.get('strategies', {}).get('rolling_window', {})
        if not config.get('enabled', True):
            return False
        
        # Need enough messages to make compression worthwhile
        window_size = config.get('window_size', 10)
        return len(context.messages) > window_size + 2
    
    def compress(self, context: CompressionContext) -> CompressionResult:
        """Compress using rolling window strategy."""
        start_time = time.time()
        
        config = self.config.get('strategies', {}).get('rolling_window', {})
        window_size = config.get('window_size', 10)
        importance_threshold = config.get('importance_threshold', 0.3)
        
        # Preserve recent messages
        recent_messages = context.messages[-context.preserve_recent_count:]
        older_messages = context.messages[:-context.preserve_recent_count]
        
        # Select important messages from older messages
        important_messages = []
        preserved_info = {
            'questions_preserved': 0,
            'code_preserved': 0,
            'recent_preserved': len(recent_messages),
            'critical_loss': 0
        }
        
        for i, message in enumerate(older_messages):
            importance = self.analyzer.analyze_message_importance(
                message, len(older_messages) - i - 1
            )
            
            if importance >= importance_threshold:
                important_messages.append(message)
                
                # Track preserved content types
                content = message.get('content', '')
                if self.analyzer._is_question(content):
                    preserved_info['questions_preserved'] += 1
                if self.analyzer._contains_code(content):
                    preserved_info['code_preserved'] += 1
        
        # Apply window size limit to important messages
        if len(important_messages) > window_size:
            # Sort by importance and take top messages
            scored_messages = []
            for msg in important_messages:
                importance = self.analyzer.analyze_message_importance(msg, 0)
                scored_messages.append((importance, msg))
            
            scored_messages.sort(key=lambda x: x[0], reverse=True)
            important_messages = [msg for _, msg in scored_messages[:window_size]]
        
        # Combine preserved messages with recent messages
        compressed_messages = important_messages + recent_messages
        
        # Calculate metrics
        original_tokens = self._calculate_tokens(context.messages)
        compressed_tokens = self._calculate_tokens(compressed_messages)
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        compression_time_ms = int((time.time() - start_time) * 1000)
        
        quality_score = self.calculate_quality_score(
            context.messages, compressed_messages, preserved_info
        )
        
        return CompressionResult(
            compressed_messages=compressed_messages,
            original_token_count=original_tokens,
            compressed_token_count=compressed_tokens,
            compression_ratio=compression_ratio,
            compression_time_ms=compression_time_ms,
            quality_score=quality_score,
            strategy_used=self.get_strategy_name(),
            metadata={
                'window_size': window_size,
                'importance_threshold': importance_threshold,
                'messages_preserved': len(important_messages),
                'recent_preserved': len(recent_messages),
                'preserved_info': preserved_info
            }
        )


class IntelligentSummaryStrategy(CompressionStrategy):
    """Intelligent summary compression strategy using LLM."""
    
    def get_strategy_name(self) -> str:
        return "intelligent_summary"
    
    def can_compress(self, context: CompressionContext) -> bool:
        """Check if intelligent summary compression is applicable."""
        config = self.config.get('strategies', {}).get('intelligent_summary', {})
        if not config.get('enabled', False):
            return False
        
        # Need LLM backend available
        try:
            from services.llm_factory import get_llm_factory
            factory = get_llm_factory()
            return factory.is_healthy()
        except Exception:
            return False
    
    def compress(self, context: CompressionContext) -> CompressionResult:
        """Compress using intelligent summary strategy."""
        start_time = time.time()
        
        config = self.config.get('strategies', {}).get('intelligent_summary', {})
        summary_length_ratio = config.get('summary_length_ratio', 0.3)
        summarization_model = config.get('summarization_model', 'llama3.2:1b')
        
        # Preserve recent messages
        recent_messages = context.messages[-context.preserve_recent_count:]
        older_messages = context.messages[:-context.preserve_recent_count]
        
        if not older_messages:
            # Nothing to summarize
            compressed_messages = recent_messages
            original_tokens = self._calculate_tokens(context.messages)
            compressed_tokens = self._calculate_tokens(compressed_messages)
        else:
            # Generate summary of older messages
            summary = self._generate_summary(older_messages, summarization_model, summary_length_ratio)
            
            # Create summary message
            summary_message = {
                'role': 'assistant',
                'content': f"[CONVERSATION SUMMARY]\n{summary}",
                'timestamp': datetime.now().isoformat(),
                'is_summary': True
            }
            
            # Combine summary with recent messages
            compressed_messages = [summary_message] + recent_messages
            
            original_tokens = self._calculate_tokens(context.messages)
            compressed_tokens = self._calculate_tokens(compressed_messages)
        
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        compression_time_ms = int((time.time() - start_time) * 1000)
        
        # Calculate preserved information
        preserved_info = {
            'questions_preserved': sum(1 for msg in recent_messages 
                                     if self.analyzer._is_question(msg.get('content', ''))),
            'code_preserved': sum(1 for msg in recent_messages 
                                if self.analyzer._contains_code(msg.get('content', ''))),
            'recent_preserved': len(recent_messages),
            'summary_created': len(older_messages) > 0,
            'critical_loss': 0
        }
        
        quality_score = self.calculate_quality_score(
            context.messages, compressed_messages, preserved_info
        )
        
        return CompressionResult(
            compressed_messages=compressed_messages,
            original_token_count=original_tokens,
            compressed_token_count=compressed_tokens,
            compression_ratio=compression_ratio,
            compression_time_ms=compression_time_ms,
            quality_score=quality_score,
            strategy_used=self.get_strategy_name(),
            metadata={
                'summary_length_ratio': summary_length_ratio,
                'summarization_model': summarization_model,
                'messages_summarized': len(older_messages),
                'recent_preserved': len(recent_messages),
                'preserved_info': preserved_info
            }
        )
    
    def _generate_summary(self, messages: List[Dict], model: str, length_ratio: float) -> str:
        """Generate a summary of the conversation."""
        try:
            # Prepare conversation text
            conversation_text = self._format_messages_for_summary(messages)
            
            # Calculate target summary length
            original_length = len(conversation_text)
            target_length = int(original_length * length_ratio)
            
            # Create summary prompt
            prompt = f"""Please provide a concise summary of this conversation in approximately {target_length} characters. Focus on key points, decisions, and important information:

{conversation_text}

Summary:"""
            
            # Get LLM factory and generate summary
            from services.llm_factory import get_llm_factory
            factory = get_llm_factory()
            response = factory.generate_response(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                stream=False
            )
            
            summary = response.get('response', 'Summary generation failed')
            
            # Clean up summary
            summary = summary.strip()
            if summary.startswith('Summary:'):
                summary = summary[8:].strip()
            
            return summary
            
        except Exception as e:
            return f"[Summary generation failed: {str(e)}]"
    
    def _format_messages_for_summary(self, messages: List[Dict]) -> str:
        """Format messages for summary generation."""
        formatted = []
        for msg in messages:
            role = msg.get('role', '').capitalize()
            content = msg.get('content', '')
            formatted.append(f"{role}: {content}")
        
        return '\n\n'.join(formatted)


class HybridStrategy(CompressionStrategy):
    """Hybrid compression strategy combining multiple approaches."""
    
    def get_strategy_name(self) -> str:
        return "hybrid"
    
    def can_compress(self, context: CompressionContext) -> bool:
        """Check if hybrid compression is applicable."""
        config = self.config.get('strategies', {}).get('hybrid', {})
        if not config.get('enabled', False):
            return False
        
        # Need sufficient messages for tiered compression
        tier1_count = config.get('tier1_messages', 5)
        tier2_count = config.get('tier2_messages', 10)
        return len(context.messages) > tier1_count + tier2_count + context.preserve_recent_count
    
    def compress(self, context: CompressionContext) -> CompressionResult:
        """Compress using hybrid strategy."""
        start_time = time.time()
        
        config = self.config.get('strategies', {}).get('hybrid', {})
        tier1_messages = config.get('tier1_messages', 5)  # Keep as-is
        tier2_messages = config.get('tier2_messages', 10)  # Selective preservation
        tier3_summary_ratio = config.get('tier3_summary_ratio', 0.2)  # Summarize
        
        # Divide messages into tiers
        # Tier 1: Most recent messages (based on config, not preserve_recent_count)
        tier1_start = len(context.messages) - tier1_messages
        tier2_start = tier1_start - tier2_messages
        tier3_end = tier2_start
        
        # Tier 1: Recent messages (keep all)
        tier1 = context.messages[tier1_start:]
        
        # Tier 2: Semi-recent messages (selective preservation)
        tier2 = context.messages[tier2_start:tier1_start] if tier2_start >= 0 else []
        
        # Tier 3: Older messages (summarize)
        tier3 = context.messages[:tier3_end] if tier3_end > 0 else []
        
        compressed_messages = []
        preserved_info = {
            'questions_preserved': 0,
            'code_preserved': 0,
            'recent_preserved': len(tier1),
            'critical_loss': 0,
            'tier1_count': len(tier1),
            'tier2_count': 0,
            'tier3_summarized': len(tier3) > 0
        }
        
        # Process Tier 3: Summarize oldest messages
        if tier3:
            summary_strategy = IntelligentSummaryStrategy(self.config)
            summary_context = CompressionContext(
                messages=tier3,
                max_context_tokens=context.max_context_tokens,
                preserve_recent_count=0,
                target_compression_ratio=tier3_summary_ratio,
                model_name=context.model_name,
                conversation_id=context.conversation_id
            )
            
            if summary_strategy.can_compress(summary_context):
                try:
                    summary_result = summary_strategy.compress(summary_context)
                    compressed_messages.extend(summary_result.compressed_messages)
                except Exception:
                    # Fallback: use rolling window for tier 3
                    window_strategy = RollingWindowStrategy(self.config)
                    window_context = CompressionContext(
                        messages=tier3,
                        max_context_tokens=context.max_context_tokens,
                        preserve_recent_count=2,
                        target_compression_ratio=0.3,
                        model_name=context.model_name,
                        conversation_id=context.conversation_id
                    )
                    window_result = window_strategy.compress(window_context)
                    compressed_messages.extend(window_result.compressed_messages)
            else:
                # If summary not available, use rolling window fallback
                window_strategy = RollingWindowStrategy(self.config)
                window_context = CompressionContext(
                    messages=tier3,
                    max_context_tokens=context.max_context_tokens,
                    preserve_recent_count=2,
                    target_compression_ratio=0.3,
                    model_name=context.model_name,
                    conversation_id=context.conversation_id
                )
                window_result = window_strategy.compress(window_context)
                compressed_messages.extend(window_result.compressed_messages)
        
        # Process Tier 2: Selective preservation
        if tier2:
            for message in tier2:
                importance = self.analyzer.analyze_message_importance(message, 0)
                if importance >= 0.4:  # Keep moderately important messages
                    compressed_messages.append(message)
                    preserved_info['tier2_count'] += 1
                    
                    content = message.get('content', '')
                    if self.analyzer._is_question(content):
                        preserved_info['questions_preserved'] += 1
                    if self.analyzer._contains_code(content):
                        preserved_info['code_preserved'] += 1
        
        # Process Tier 1: Keep all recent messages
        compressed_messages.extend(tier1)
        
        # Count preserved content in tier 1
        for message in tier1:
            content = message.get('content', '')
            if self.analyzer._is_question(content):
                preserved_info['questions_preserved'] += 1
            if self.analyzer._contains_code(content):
                preserved_info['code_preserved'] += 1
        
        # Calculate metrics
        original_tokens = self._calculate_tokens(context.messages)
        compressed_tokens = self._calculate_tokens(compressed_messages)
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        compression_time_ms = int((time.time() - start_time) * 1000)
        
        quality_score = self.calculate_quality_score(
            context.messages, compressed_messages, preserved_info
        )
        
        return CompressionResult(
            compressed_messages=compressed_messages,
            original_token_count=original_tokens,
            compressed_token_count=compressed_tokens,
            compression_ratio=compression_ratio,
            compression_time_ms=compression_time_ms,
            quality_score=quality_score,
            strategy_used=self.get_strategy_name(),
            metadata={
                'tier1_messages': tier1_messages,
                'tier2_messages': tier2_messages,
                'tier3_summary_ratio': tier3_summary_ratio,
                'tiers_processed': {
                    'tier1': len(tier1),
                    'tier2': len(tier2),
                    'tier3': len(tier3)
                },
                'preserved_info': preserved_info
            }
        )


def get_compression_strategy(strategy_name: str, config: Dict[str, Any]) -> Optional[CompressionStrategy]:
    """Factory function to get compression strategy by name."""
    strategies = {
        'rolling_window': RollingWindowStrategy,
        'intelligent_summary': IntelligentSummaryStrategy,
        'hybrid': HybridStrategy
    }
    
    strategy_class = strategies.get(strategy_name)
    if strategy_class:
        return strategy_class(config)
    
    return None


def get_available_strategies(config: Dict[str, Any]) -> List[str]:
    """Get list of available and enabled compression strategies."""
    available = []
    strategies_config = config.get('strategies', {})
    
    for strategy_name in ['rolling_window', 'intelligent_summary', 'hybrid']:
        strategy_config = strategies_config.get(strategy_name, {})
        if strategy_config.get('enabled', strategy_name == 'rolling_window'):
            available.append(strategy_name)
    
    return available
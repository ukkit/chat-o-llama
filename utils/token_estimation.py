"""Token estimation utilities for Chat-O-Llama."""

import re
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TokenEstimate:
    """Detailed token estimation with accuracy metrics."""
    estimated_tokens: int
    confidence_level: float  # 0.0 to 1.0
    estimation_method: str
    character_count: int
    word_count: int


class ModelTokenEstimator:
    """Model-specific token estimation with improved accuracy."""
    
    # Model-specific character-to-token ratios based on common models
    MODEL_RATIOS = {
        'llama': 3.8,  # Llama models (slightly more efficient)
        'llama2': 3.8,
        'llama3': 3.7,  # Even more efficient
        'llama3.2': 3.7,
        'mistral': 4.0,
        'mixtral': 4.0,
        'phi': 4.2,  # Phi models tend to use more tokens
        'gemma': 3.9,
        'qwen': 3.5,  # Chinese models are more efficient
        'deepseek': 3.6,
        'default': 4.0  # Conservative default
    }
    
    # Language-specific adjustments
    LANGUAGE_ADJUSTMENTS = {
        'chinese': 0.7,  # Chinese uses fewer tokens per character
        'japanese': 0.8,
        'korean': 0.8,
        'arabic': 0.9,
        'russian': 0.9,
        'code': 1.2,  # Code uses more tokens
        'english': 1.0,
        'default': 1.0
    }
    
    def __init__(self):
        """Initialize the token estimator."""
        self.estimation_cache = {}
    
    def estimate_tokens(self, text: str, model_name: str = None) -> TokenEstimate:
        """Estimate tokens with model-specific accuracy."""
        if not text:
            return TokenEstimate(0, 1.0, 'empty', 0, 0)
        
        # Get cached result if available
        cache_key = (text[:100], model_name)  # Cache based on first 100 chars and model
        if cache_key in self.estimation_cache:
            return self.estimation_cache[cache_key]
        
        char_count = len(text)
        word_count = len(text.split())
        
        # Determine model ratio
        model_ratio = self._get_model_ratio(model_name)
        
        # Detect content type and language
        content_type = self._detect_content_type(text)
        language = self._detect_language(text)
        
        # Apply language adjustment
        language_adjustment = self.LANGUAGE_ADJUSTMENTS.get(language, 1.0)
        adjusted_ratio = model_ratio * language_adjustment
        
        # Calculate base estimation
        base_tokens = max(1, char_count / adjusted_ratio)
        
        # Apply content-specific adjustments
        adjusted_tokens = self._apply_content_adjustments(base_tokens, text, content_type)
        
        # Round to integer
        final_tokens = max(1, round(adjusted_tokens))
        
        # Calculate confidence based on text characteristics
        confidence = self._calculate_confidence(text, content_type, model_name)
        
        # Determine estimation method
        method = f"model_specific_{model_name or 'default'}_{content_type}_{language}"
        
        result = TokenEstimate(
            estimated_tokens=final_tokens,
            confidence_level=confidence,
            estimation_method=method,
            character_count=char_count,
            word_count=word_count
        )
        
        # Cache the result
        self.estimation_cache[cache_key] = result
        return result
    
    def estimate_conversation_tokens(self, messages: List[Dict], model_name: str = None) -> Dict:
        """Estimate tokens for an entire conversation with sliding window analysis."""
        if not messages:
            return {'total_tokens': 0, 'message_breakdown': [], 'sliding_windows': []}
        
        message_breakdown = []
        total_tokens = 0
        
        # Analyze each message
        for i, message in enumerate(messages):
            content = message.get('content', '')
            role = message.get('role', 'user')
            
            # Estimate tokens for content
            content_estimate = self.estimate_tokens(content, model_name)
            
            # Add overhead for role and formatting
            role_overhead = self._estimate_role_overhead(role)
            message_tokens = content_estimate.estimated_tokens + role_overhead
            
            message_breakdown.append({
                'index': i,
                'role': role,
                'content_tokens': content_estimate.estimated_tokens,
                'role_overhead': role_overhead,
                'total_tokens': message_tokens,
                'confidence': content_estimate.confidence_level,
                'character_count': content_estimate.character_count
            })
            
            total_tokens += message_tokens
        
        # Sliding window analysis
        sliding_windows = self._analyze_sliding_windows(message_breakdown)
        
        return {
            'total_tokens': total_tokens,
            'message_breakdown': message_breakdown,
            'sliding_windows': sliding_windows,
            'average_confidence': sum(m['confidence'] for m in message_breakdown) / len(message_breakdown)
        }
    
    def compare_estimation_methods(self, text: str, model_name: str = None) -> Dict:
        """Compare different estimation methods for accuracy analysis."""
        methods = {}
        
        # Simple character-based
        methods['simple'] = max(1, len(text) // 4)
        
        # Word-based
        methods['word_based'] = max(1, len(text.split()) * 1.3)
        
        # Model-specific (our method)
        model_estimate = self.estimate_tokens(text, model_name)
        methods['model_specific'] = model_estimate.estimated_tokens
        
        # Whitespace-based
        methods['whitespace'] = max(1, len(re.findall(r'\S+', text)) * 1.4)
        
        return {
            'methods': methods,
            'recommended': model_estimate,
            'text_stats': {
                'characters': len(text),
                'words': len(text.split()),
                'lines': len(text.split('\n'))
            }
        }
    
    def _get_model_ratio(self, model_name: str) -> float:
        """Get character-to-token ratio for specific model."""
        if not model_name:
            return self.MODEL_RATIOS['default']
        
        model_lower = model_name.lower()
        
        # Check for exact matches first
        if model_lower in self.MODEL_RATIOS:
            return self.MODEL_RATIOS[model_lower]
        
        # Check for partial matches, preferring longer matches
        best_match = None
        best_match_length = 0
        
        for model_key, ratio in self.MODEL_RATIOS.items():
            if model_key != 'default' and model_key in model_lower:
                if len(model_key) > best_match_length:
                    best_match = ratio
                    best_match_length = len(model_key)
        
        if best_match is not None:
            return best_match
        
        return self.MODEL_RATIOS['default']
    
    def _detect_content_type(self, text: str) -> str:
        """Detect the type of content to apply appropriate adjustments."""
        text_lower = text.lower()
        
        # Check for code
        code_indicators = [
            r'```', r'def\s+\w+\(', r'class\s+\w+', r'function\s+\w+',
            r'import\s+\w+', r'from\s+\w+\s+import', r'<\w+[^>]*>',
            r'{\s*["\w]+\s*:', r'\w+\(\)', r'console\.log', r'print\('
        ]
        
        if any(re.search(pattern, text) for pattern in code_indicators):
            return 'code'
        
        # Check for technical content
        if any(word in text_lower for word in ['api', 'json', 'xml', 'sql', 'database', 'server']):
            return 'technical'
        
        # Check for mathematical content
        math_keywords = ['calculate', 'equation', 'solve', 'formula']
        has_math_keywords = any(word in text_lower for word in math_keywords)
        has_math_operators = re.search(r'[\+\-\*/=]', text)
        has_digits = len(re.findall(r'\d', text)) >= 2
        
        if (has_math_keywords and has_digits) or (has_math_operators and len(re.findall(r'\d', text)) >= 3):
            return 'mathematical'
        
        return 'natural_language'
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character patterns."""
        # Check for Chinese characters
        if re.search(r'[\u4e00-\u9fff]', text):
            return 'chinese'
        
        # Check for Japanese characters
        if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
            return 'japanese'
        
        # Check for Korean characters
        if re.search(r'[\uac00-\ud7af]', text):
            return 'korean'
        
        # Check for Arabic characters
        if re.search(r'[\u0600-\u06ff]', text):
            return 'arabic'
        
        # Check for Cyrillic (Russian)
        if re.search(r'[\u0400-\u04ff]', text):
            return 'russian'
        
        return 'english'
    
    def _apply_content_adjustments(self, base_tokens: float, text: str, content_type: str) -> float:
        """Apply content-specific adjustments to token estimation."""
        if content_type == 'code':
            # Code tends to use more tokens due to special characters
            return base_tokens * 1.15
        elif content_type == 'technical':
            # Technical content has more specialized terms
            return base_tokens * 1.05
        elif content_type == 'mathematical':
            # Mathematical content can be more compact
            return base_tokens * 0.95
        
        return base_tokens
    
    def _calculate_confidence(self, text: str, content_type: str, model_name: str) -> float:
        """Calculate confidence level for the estimation."""
        confidence = 0.7  # Base confidence
        
        # Higher confidence for longer texts
        if len(text) > 100:
            confidence += 0.1
        if len(text) > 500:
            confidence += 0.1
        
        # Lower confidence for very short texts
        if len(text) < 20:
            confidence -= 0.2
        
        # Higher confidence for known models
        if model_name and any(known in model_name.lower() for known in self.MODEL_RATIOS.keys()):
            confidence += 0.1
        
        # Content type affects confidence
        if content_type == 'natural_language':
            confidence += 0.1
        elif content_type == 'code':
            confidence -= 0.05  # Code is harder to estimate
        
        return min(1.0, max(0.1, confidence))
    
    def _estimate_role_overhead(self, role: str) -> int:
        """Estimate token overhead for message role and formatting."""
        role_tokens = {
            'system': 8,     # System messages have more formatting
            'user': 4,       # User messages have minimal formatting
            'assistant': 6,  # Assistant messages have moderate formatting
            'function': 10,  # Function calls have complex formatting
            'tool': 8        # Tool messages have structured formatting
        }
        
        return role_tokens.get(role, 5)  # Default overhead
    
    def _analyze_sliding_windows(self, message_breakdown: List[Dict]) -> List[Dict]:
        """Analyze token distribution in sliding windows."""
        windows = []
        window_sizes = [5, 10, 15, 20]
        
        for window_size in window_sizes:
            if len(message_breakdown) < window_size:
                continue
            
            window_analysis = []
            for i in range(len(message_breakdown) - window_size + 1):
                window_messages = message_breakdown[i:i + window_size]
                window_tokens = sum(msg['total_tokens'] for msg in window_messages)
                
                window_analysis.append({
                    'start_index': i,
                    'end_index': i + window_size - 1,
                    'total_tokens': window_tokens,
                    'average_tokens_per_message': window_tokens / window_size,
                    'message_count': window_size
                })
            
            if window_analysis:
                windows.append({
                    'window_size': window_size,
                    'windows': window_analysis,
                    'max_tokens': max(w['total_tokens'] for w in window_analysis),
                    'min_tokens': min(w['total_tokens'] for w in window_analysis),
                    'average_tokens': sum(w['total_tokens'] for w in window_analysis) / len(window_analysis)
                })
        
        return windows


# Global estimator instance
_estimator = ModelTokenEstimator()


def estimate_tokens(text: str, model_name: str = None) -> int:
    """Simple function for backward compatibility."""
    estimate = _estimator.estimate_tokens(text, model_name)
    return estimate.estimated_tokens


def estimate_tokens_detailed(text: str, model_name: str = None) -> TokenEstimate:
    """Get detailed token estimation."""
    return _estimator.estimate_tokens(text, model_name)


def estimate_conversation_tokens(messages: List[Dict], model_name: str = None) -> Dict:
    """Estimate tokens for an entire conversation."""
    return _estimator.estimate_conversation_tokens(messages, model_name)


def compare_estimation_methods(text: str, model_name: str = None) -> Dict:
    """Compare different token estimation methods."""
    return _estimator.compare_estimation_methods(text, model_name)
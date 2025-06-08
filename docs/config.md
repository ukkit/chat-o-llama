# Complete Guide to config.json Variables

## 🕒 Timeouts Section
Controls how long to wait for Ollama responses and connections.

### `ollama_timeout` (default: 600 seconds)
- **What it does**: Maximum time to wait for Ollama to generate a complete response
- **Performance impact**: Lower values fail faster but may cut off long responses
- **For your setup**: 600 seconds allows for high-quality, detailed responses
- **Speed vs Quality**: Higher values enable complex reasoning and longer responses

### `ollama_connect_timeout` (default: 45 seconds)
- **What it does**: Maximum time to wait when connecting to Ollama server
- **Performance impact**: Only affects initial connection, not response generation
- **For your setup**: 45 seconds provides robust connection handling
- **When to adjust**: Increase for unreliable networks, decrease for faster failure detection

---

## 🎛️ Model Options Section
Controls how the AI model generates responses - biggest impact on quality vs speed.

### `temperature` (default: 0.1, range: 0.0-2.0)
- **What it does**: Controls randomness/creativity in responses
- **Performance impact**: Lower values = more predictable, focused responses
- **Precision optimization**: 0.1 provides highly consistent, reliable outputs
- **Quality optimization**: Excellent for research, analysis, and factual content
- **For your setup**: 0.1 maximizes accuracy and reduces hallucinations

### `top_p` (default: 0.95, range: 0.0-1.0)
- **What it does**: Nucleus sampling - considers top % of likely next words
- **Performance impact**: Higher values allow more diverse vocabulary
- **Precision optimization**: 0.95 enables comprehensive vocabulary while maintaining focus
- **Quality trade-off**: High values ensure nuanced expression without repetition

### `top_k` (default: 50, range: 1-100+)
- **What it does**: Considers only the top K most likely next words
- **Performance impact**: Higher values = more vocabulary options, slower processing
- **Precision optimization**: 50 provides rich vocabulary for detailed responses
- **For your hardware**: Balanced setting for comprehensive language generation

### `min_p` (default: 0.01, range: 0.0-1.0)
- **What it does**: Minimum probability threshold for token selection
- **Performance impact**: **Alternative to top_p** - can be faster for CPU processing
- **Precision optimization**: 0.01 allows diverse vocabulary while filtering noise
- **For your setup**: Works well with typical_p for quality-focused responses
- **Quality**: More consistent than top_p alone, especially for factual responses

### `typical_p` (default: 0.95, range: 0.0-1.0)
- **What it does**: Typical sampling - focuses on "typical" token probabilities
- **Performance impact**: **Can replace top_p/top_k** for better quality/speed balance
- **Precision optimization**: 0.95 maintains natural language flow with high quality
- **For your hardware**: Excellent for comprehensive, well-structured responses
- **Advanced**: Works with min_p for superior precision compared to traditional sampling

### `num_predict` (default: 4096)
- **What it does**: Maximum number of tokens (words/pieces) in the response
- **Performance impact**: **BIGGEST QUALITY IMPACT** - directly affects response length
- **Precision optimization**: 4096 allows detailed, comprehensive responses (2000+ words)
- **For research**: Enables in-depth analysis, detailed explanations, and complete coverage
- **Trade-off**: Longer generation time but much more thorough responses

### `num_ctx` (default: 8192)
- **What it does**: Context window size - how much conversation history to remember
- **Performance impact**: **MAJOR QUALITY IMPACT** - larger context = better understanding
- **Precision optimization**: 8192 maintains extensive conversation context and document memory
- **Memory impact**: Higher values provide superior continuity and reference capability
- **For your setup**: Excellent for complex, multi-turn discussions and research tasks

### `repeat_penalty` (default: 1.15, range: 0.0-2.0)
- **What it does**: Prevents the model from repeating the same words/phrases
- **Performance impact**: Minimal impact on speed, major impact on quality
- **Recommended**: 1.15 provides strong repetition prevention without awkwardness
- **Too high**: Makes responses unnatural; too low allows excessive repetition

### `repeat_last_n` (default: 64)
- **What it does**: How many recent tokens to consider for repeat penalty
- **Performance impact**: Higher values = better repetition detection, slower processing
- **Precision optimization**: 64 provides comprehensive repetition checking
- **For your setup**: Ensures high-quality, varied expression throughout long responses
- **Memory impact**: Higher values improve content quality at modest performance cost

### `stop` (array of strings)
- **What it does**: Tokens that tell the model to stop generating
- **Performance impact**: Can improve response quality by preventing unwanted continuation
- **For chat**: Includes "Human:", "User:" to prevent model confusion
- **Quality benefit**: Prevents model from generating responses as both sides of conversation

### `presence_penalty` (default: 0.0, range: -2.0 to 2.0)
- **What it does**: Penalizes tokens based on whether they appear in the text
- **Performance impact**: Minimal impact on speed
- **OpenAI compatibility**: Useful for applications migrating from OpenAI
- **Precision setting**: 0.0 maintains natural language without artificial constraints

### `frequency_penalty` (default: 0.0, range: -2.0 to 2.0)
- **What it does**: Penalizes tokens based on their frequency in the text
- **Performance impact**: Minimal impact on speed
- **OpenAI compatibility**: Can reduce repetitive content
- **Precision setting**: 0.0 allows natural repetition when contextually appropriate

### `penalize_newline` (default: false)
- **What it does**: Whether to apply penalties to newline characters
- **Performance impact**: Minimal impact on speed
- **For detailed responses**: false allows natural paragraph structure and formatting
- **Quality**: Enables better organization in long, comprehensive responses

### `seed` (optional, integer)
- **What it does**: Fixed seed for reproducible outputs
- **Performance impact**: No impact on speed
- **For research**: null enables varied, creative responses
- **For testing**: Use fixed value (e.g., 42) for consistent results

---

## ⚡ Performance Section
Hardware and processing optimizations for precision-focused operation.

### `context_history_limit` (default: 15)
- **What it does**: How many previous messages to include in conversation context
- **Performance impact**: **MAJOR QUALITY IMPACT** - more messages = better continuity
- **Precision optimization**: 15 provides extensive conversation memory
- **Trade-off**: Richer context understanding at modest performance cost
- **For your setup**: Excellent for research discussions and complex problem-solving

### `use_mlock` (default: true)
- **What it does**: Locks model in RAM to prevent swapping to disk
- **Performance impact**: Prevents slowdowns from disk swapping
- **For your setup**: true if you have sufficient RAM (8GB+)
- **Precision benefit**: Ensures consistent response times for quality output

### `use_mmap` (default: true)
- **What it does**: Memory-mapped file access for model loading
- **Performance impact**: Faster model loading and efficient memory usage
- **Recommendation**: true - almost always beneficial
- **Hardware**: Especially good for systems optimizing for quality over speed

### `num_thread` (default: -1)
- **What it does**: Number of CPU threads to use (-1 = auto-detect)
- **For your setup**: Auto-detection optimizes for your hardware
- **Manual setting**: Use number of CPU cores for maximum processing power
- **Performance**: More threads = better utilization for quality generation

### `num_gpu` (default: 0)
- **What it does**: Number of GPU layers to use for processing
- **For your setup**: 0 since you're using CPU-only configuration
- **With GPU**: Higher values offload more work to GPU for speed

### `main_gpu` (default: 0)
- **What it does**: Which GPU to use as the primary GPU (for multi-GPU systems)
- **For your setup**: Not relevant since you're CPU-only
- **Multi-GPU**: Specify which GPU (0, 1, 2, etc.) to use as primary

### `num_batch` (default: 1)
- **What it does**: Batch size for token processing
- **Performance impact**: **SIGNIFICANT for quality** - affects processing efficiency
- **For your setup**: 1 provides stable, consistent processing
- **Quality optimization**: Conservative setting ensures reliable operation
- **Memory trade-off**: Lower values provide more predictable resource usage

### `num_keep` (default: 10)
- **What it does**: Number of tokens from the beginning of prompt to always keep
- **Performance impact**: Higher values preserve more context
- **Precision optimization**: 10 ensures important prompt instructions are retained
- **Context**: Maintains instruction clarity in long conversations

### `numa` (default: false)
- **What it does**: Enable Non-Uniform Memory Access optimizations
- **For your setup**: false unless you have a multi-socket CPU system
- **When to enable**: Only for high-end workstations with multiple CPU sockets
- **Performance**: Can help on NUMA systems, may hurt on single-socket systems

---

## 🎯 Response Optimization Section
Advanced settings for precision-focused response behavior.

### `stream` (default: false)
- **What it does**: Whether to stream response word-by-word or wait for complete response
- **User experience**: false = complete, polished responses; true = progressive display
- **For precision work**: false ensures complete processing before display
- **Quality**: Better for research and detailed responses

### `keep_alive` (default: "10m")
- **What it does**: How long to keep model loaded in memory after last request
- **Performance impact**: **IMPORTANT FOR CONSISTENCY** - keeps model ready
- **Precision optimization**: 10 minutes provides stable, consistent response quality
- **Memory trade-off**: Longer values maintain optimal model state
- **For your setup**: Excellent for extended research sessions

### `low_vram` (default: false)
- **What it does**: Optimizations for systems with limited graphics memory
- **For your setup**: false since you're prioritizing quality over resource constraints
- **Performance**: Allows full utilization of available system resources

### `f16_kv` (default: false)
- **What it does**: Use 16-bit floating point for key-value cache (vs 32-bit)
- **Performance impact**: Reduces memory usage with potential quality impact
- **Precision setting**: false maintains maximum numerical precision
- **Quality**: Full precision for highest quality responses

---

## 🎯 Precision Optimization Summary

**Configuration Philosophy: Quality First**
This configuration prioritizes response quality, accuracy, and comprehensiveness over speed. Ideal for:
- Research and analysis tasks
- Complex problem-solving
- Educational content creation
- Professional writing assistance
- Detailed technical explanations

**Key Precision Features:**
1. **Extended Response Length**: 4096 tokens enable 2000+ word responses
2. **Large Context Window**: 8192 tokens maintain extensive conversation memory
3. **High Context History**: 15 messages provide rich discussion continuity
4. **Low Temperature**: 0.1 ensures consistent, reliable outputs
5. **Advanced Sampling**: min_p + typical_p for superior quality
6. **Extended Keep-Alive**: 10 minutes for consistent model state

**Trade-offs:**
- **Response Time**: 2-5x longer generation time vs speed-optimized config
- **Resource Usage**: Higher memory and CPU utilization
- **Timeout Handling**: 600-second timeout accommodates complex responses

**Hardware Requirements:**
- **Minimum**: 8GB RAM, 4-core CPU
- **Recommended**: 16GB+ RAM, 6+ core CPU
- **Storage**: SSD recommended for model loading

**When to Use Precision Config:**
- Research and analysis tasks
- Academic or professional writing
- Complex problem-solving requiring detailed reasoning
- Educational content requiring comprehensive coverage
- Technical documentation and explanations

**When to Consider Speed Config:**
- Casual conversations
- Quick Q&A sessions
- Limited hardware resources
- Mobile or battery-powered devices
- Real-time chat applications

## 🔄 Configuration Switching Guide

To switch between precision and speed configurations:

1. **Save current config**: `cp config.json config-precision.json`
2. **Create speed config**: Use reduced values (num_predict: 1024, num_ctx: 2048, etc.)
3. **Switch configs**: `cp config-speed.json config.json` (restart required)
4. **Hybrid approach**: Adjust individual parameters based on current task needs

The precision configuration provides the highest quality responses at the cost of longer generation times, making it ideal for professional and research use cases where accuracy and completeness are prioritized over speed.
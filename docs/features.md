# chat-o-llama 🦙 Features

A modern, feature-rich Flask web application for chatting with Ollama models with persistent conversation history and advanced functionality.

## 🎯 Core Features

### 💬 **Chat Interface**
- **Real-time messaging** with Ollama AI models
- **Dark theme UI** with GitHub-inspired design using JetBrains Mono font
- **Auto-resizing input** textarea that adapts to content length
- **Keyboard shortcuts** - Enter to send, Shift+Enter for new line
- **Loading indicators** with "Thinking..." status during AI responses

### 🗂️ **Conversation Management**
- **Persistent chat history** stored in SQLite database
- **Multiple conversation support** with sidebar navigation
- **Conversation renaming** - double-click or edit button to rename
- **Conversation deletion** with confirmation dialog
- **Auto-timestamping** with last updated sorting
- **New chat creation** with model selection

### 🔍 **Search & Discovery**
- **Real-time search** across conversations and message content
- **Search results preview** with conversation context
- **Quick navigation** to search results
- **Fuzzy matching** for flexible search queries

## 🚀 Enhanced Features

### 📋 **Message Management**
- **Copy to clipboard** - hover over any message to reveal copy button (📋)
- **Visual feedback** - copy button changes to ✓ when successful
- **Toast notifications** for copy confirmations
- **Cross-browser support** with fallback for older browsers
- **Clean text extraction** - removes HTML formatting when copying

### 📊 **Performance Metrics**
- **Response time tracking** - displays time taken for each AI response
- **Token counting** - estimates and displays token usage
- **Tokens per second** calculation for performance insights
- **Database metrics storage** for analytics and optimization
- **Real-time performance display** under each assistant message

### 🤖 **Model Integration**
- **Dynamic model detection** from Ollama server
- **Model selection dropdown** with auto-refresh
- **Model-specific configuration** support
- **Multi-model conversations** - switch models between messages
- **Connection status monitoring** with error handling

## ⚙️ Advanced Configuration

### 🔧 **Ollama Integration**
- **Customizable API endpoints** via environment variables
- **Timeout configuration** for connection and response handling
- **Advanced model parameters**:
  - Temperature control for response creativity
  - Top-p and top-k sampling parameters
  - Context length and prediction limits
  - Repeat penalty adjustment
  - Custom stop sequences

### 🎛️ **Performance Optimization**
- **Threading support** for concurrent request handling
- **Context history limiting** to optimize memory usage
- **Connection pooling** and keep-alive settings
- **GPU acceleration support** when available
- **Memory management** with mlock/mmap options
- **Configurable batch processing**

### 📁 **Database Features**
- **SQLite backend** with optimized schema
- **Indexed queries** for fast search and retrieval
- **Foreign key constraints** for data integrity
- **Automatic schema migration** and initialization
- **Conversation statistics** tracking
- **Message metadata** storage (timestamps, models, metrics)

## 🛡️ **Security & Reliability**

### 🔐 **Security**
- **SQL injection prevention** with parameterized queries
- **Input validation** and sanitization
- **XSS protection** with HTML escaping
- **CSRF token support** (configurable)
- **Environment variable configuration** for sensitive data

### 🛠️ **Error Handling**
- **Graceful degradation** when Ollama is unavailable
- **Connection timeout handling** with user feedback
- **API error recovery** with informative error messages
- **Database error handling** with transaction rollback
- **Client-side error notifications** with auto-dismiss

### 📱 **Responsive Design**
- **Mobile-friendly interface** with touch-optimized controls
- **Adaptive layout** that works on all screen sizes
- **Accessible design** with proper contrast and semantic HTML
- **Keyboard navigation** support
- **Screen reader compatibility**

## 🎨 **User Experience**

### 🖥️ **Interface Design**
- **Clean, minimal aesthetic** inspired by modern code editors
- **Syntax highlighting** with JetBrains Mono font family
- **Smooth animations** and transitions
- **Hover effects** for interactive elements
- **Loading states** with progress indicators
- **Visual hierarchy** with proper spacing and typography

### ⚡ **Performance Features**
- **Fast message rendering** with optimized DOM updates
- **Lazy loading** for large conversation histories
- **Efficient search** with debounced input
- **Memory optimization** for long-running sessions
- **Auto-scrolling** to latest messages
- **Smooth scrolling** behavior

### 🔄 **Real-time Updates**
- **Live conversation list** updates after new messages
- **Timestamp refresh** for accurate "last updated" times
- **Model status** monitoring and updates
- **Connection health** indicators
- **Auto-retry logic** for failed requests

## 📊 **Analytics & Insights**

### 📈 **Conversation Analytics**
- **Message count tracking** per conversation
- **Average response times** calculation
- **Token usage statistics** and trends
- **Model performance comparison** across conversations
- **Usage patterns** and conversation metrics

### 🔍 **Search Analytics**
- **Search result relevance** scoring
- **Popular search terms** tracking
- **Conversation discovery** patterns
- **Content indexing** for fast retrieval

## 🚀 **Technical Specifications**

### 💻 **Backend (Flask)**
- **Python 3.7+** compatibility
- **Flask framework** with threading support
- **SQLite database** with WAL mode for performance
- **RESTful API** design with JSON responses
- **Modular architecture** with separation of concerns
- **Configuration management** via JSON files

### 🌐 **Frontend (Vanilla JavaScript)**
- **No framework dependencies** for fast loading
- **Modern ES6+ JavaScript** with async/await
- **CSS Grid and Flexbox** for responsive layouts
- **Web APIs integration** (Clipboard, Fetch, etc.)
- **Progressive enhancement** approach
- **Accessibility best practices**

### 🗄️ **Database Schema**
- **Normalized design** with proper relationships
- **Optimized indexes** for query performance
- **Constraint enforcement** for data integrity
- **Migration support** for schema updates
- **Backup-friendly** design with SQLite

## 🔧 **Configuration Options**

### ⚙️ **Runtime Configuration**
```json
{
  "timeouts": {
    "ollama_timeout": 180,
    "ollama_connect_timeout": 15
  },
  "model_options": {
    "temperature": 0.5,
    "top_p": 0.8,
    "top_k": 30,
    "num_predict": 2048,
    "num_ctx": 4096,
    "repeat_penalty": 1.1
  },
  "performance": {
    "context_history_limit": 10,
    "use_mlock": true,
    "use_mmap": true,
    "num_thread": -1,
    "num_gpu": 0
  }
}
```

### 🌍 **Environment Variables**
- `OLLAMA_API_URL` - Ollama server endpoint
- `DATABASE_PATH` - SQLite database file location
- `PORT` - Flask application port
- `DEBUG` - Debug mode toggle
- `SECRET_KEY` - Flask secret key for sessions

## 🎯 **Use Cases**

### 👩‍💻 **Development**
- **AI-assisted coding** with context-aware conversations
- **Documentation generation** with persistent chat history
- **Code review** and explanation sessions
- **Architecture discussions** with AI models

### 📚 **Research & Learning**
- **Interactive learning** sessions with AI tutors
- **Research assistance** with conversation context
- **Note-taking** and knowledge management
- **Iterative problem solving** with chat history

### 💼 **Business & Productivity**
- **Meeting preparation** with AI assistance
- **Content creation** and brainstorming sessions
- **Customer service** training and simulation
- **Process documentation** with conversational interface

---

## 🛠️ **Installation & Setup**

### Prerequisites
- Python 3.7 or higher
- Ollama server running locally or remotely
- At least one Ollama model installed

### Quick Start
1. Clone the repository
2. Install dependencies: `pip install flask requests`
3. Start Ollama: `ollama serve`
4. Run the application: `python app.py`
5. Open browser to `http://localhost:8080`

### Configuration
1. Create `config.json` for custom settings
2. Set environment variables as needed
3. Modify database path if required
4. Configure Ollama models and parameters

---

*chat-o-llama combines powerful AI conversation capabilities with a polished user experience, making it ideal for both casual chat and serious AI-assisted work.*
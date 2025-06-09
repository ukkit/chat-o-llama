# chat-o-llama 🦙 Features

A modern, feature-rich Flask web application for chatting with Ollama models with persistent conversation history, advanced markdown rendering, and professional code syntax highlighting.

## 🎯 Core Features

### 💬 **Enhanced Chat Interface**
- **Real-time messaging** with Ollama AI models
- **Professional dark theme UI** with GitHub-inspired design using JetBrains Mono font
- **Auto-resizing input** textarea that adapts to content length
- **Keyboard shortcuts** - Enter to send, Shift+Enter for new line
- **Loading indicators** with "Thinking..." status during AI responses
- **📝 Full Markdown Support** - Rich text rendering for AI responses
- **🎨 Syntax Highlighting** - Code blocks with 190+ language support via Highlight.js

### 🗂️ **Conversation Management**
- **Persistent chat history** stored in SQLite database
- **Multiple conversation support** with sidebar navigation
- **Conversation renaming** - double-click or edit button to rename
- **Conversation deletion** with confirmation dialog
- **Auto-timestamping** with last updated sorting
- **New chat creation** with model selection
- **Model restoration** - automatically restores selected model per conversation

### 🔍 **Search & Discovery**
- **Real-time search** across conversations and message content
- **Search results preview** with conversation context
- **Quick navigation** to search results
- **Fuzzy matching** for flexible search queries

## 🚀 Enhanced Features

### 📋 **Advanced Copy Functionality**
- **Dual copy system**:
  - **Message copy** - hover over any message to reveal copy button (📋)
  - **Code block copy** - dedicated copy buttons for each code block
- **Smart text extraction** - preserves formatting while removing HTML
- **Visual feedback** - copy buttons change to ✓ when successful
- **Toast notifications** for copy confirmations
- **Cross-browser support** with fallback for older browsers
- **Clean code extraction** - copies raw code without syntax highlighting markup

### 📝 **Markdown Rendering Engine**
- **GitHub-Flavored Markdown** support with marked.js
- **Rich typography** with proper heading hierarchy (H1-H6)
- **Text formatting**: **bold**, *italic*, ~~strikethrough~~
- **Lists**: ordered and unordered with proper nesting
- **Tables** with professional styling and borders
- **Blockquotes** with left border accent styling
- **Links** with hover effects and proper contrast
- **Horizontal rules** for content separation
- **Inline code** with background highlighting
- **Mathematical expressions** support (if enabled)

### 💻 **Advanced Code Support**
- **Syntax highlighting** for 190+ programming languages via Highlight.js
- **Language detection** with automatic highlighting
- **Code block headers** showing language type
- **Individual copy buttons** for each code block
- **GitHub Dark theme** optimized for readability
- **Professional formatting** with proper spacing and line numbers
- **Multi-language support** including:
  - Python, JavaScript, TypeScript, Java, C++, C#
  - HTML, CSS, SCSS, JSON, YAML, XML
  - SQL, Bash, PowerShell, Dockerfile
  - React, Vue, Angular, Svelte
  - And 180+ more languages

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

## 🎨 **Enhanced User Experience**

### 🖥️ **Professional Interface Design**
- **Code editor aesthetic** inspired by VS Code and GitHub
- **Consistent typography** with JetBrains Mono font family
- **Color-coded elements**:
  - Headers in gradient blues (#58a6ff to #a5d7ff)
  - Code in amber (#ffa657)
  - Emphasis in light blue (#a5d7ff)
  - Links in GitHub blue (#58a6ff)
- **Smooth animations** and transitions
- **Hover effects** for interactive elements
- **Loading states** with progress indicators
- **Visual hierarchy** with proper spacing and contrast

### 💡 **Content Presentation**
- **Structured messaging** with clear role distinction
- **Code block presentation**:
  - Language labels in headers
  - Copy buttons for easy code extraction
  - Syntax highlighting for readability
  - Overflow handling for long code
- **Table formatting** with borders and header styling
- **Quote styling** with left border accent
- **List formatting** with proper indentation

## ⚙️ Advanced Configuration

### 🔧 **Ollama Integration**
- **Customizable API endpoints** via environment variables
- **Timeout configuration** for connection and response handling
- **Advanced model parameters** for fine-tuning AI responses
- **Custom system prompts** for personality customization

### 🎛️ **Performance Optimization**
- **Threading support** for concurrent request handling
- **Context history limiting** to optimize memory usage
- **Connection pooling** and keep-alive settings
- **GPU acceleration support** when available
- **Memory management** optimization options
- **Configurable batch processing**

*For detailed configuration options, see [config.md](config.md)*

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
- **XSS protection** with HTML escaping for user content
- **Markdown security** - safe rendering of untrusted content
- **CSRF token support** (configurable)
- **Environment variable configuration** for sensitive data

### 🛠️ **Error Handling**
- **Graceful degradation** when Ollama is unavailable
- **Connection timeout handling** with user feedback
- **API error recovery** with informative error messages
- **Database error handling** with transaction rollback
- **Client-side error notifications** with auto-dismiss
- **Markdown parsing fallback** - graceful handling of malformed markdown

### 📱 **Responsive Design**
- **Mobile-friendly interface** with touch-optimized controls
- **Adaptive layout** that works on all screen sizes
- **Accessible design** with proper contrast and semantic HTML
- **Keyboard navigation** support
- **Screen reader compatibility**
- **Touch-friendly copy buttons** for mobile devices

## 🏗️ **Architecture & Code Organization**

### 📁 **File Structure**
```
project/
├── app.py                 # Flask backend
├── config.json           # Configuration
├── templates/
│   └── index.html        # Main HTML template
└── static/
    ├── css/
    │   └── styles.css    # Organized CSS styling
    └── js/
        └── app.js        # Modular JavaScript
```

### 🔧 **Modular Design**
- **Separation of concerns** - HTML structure, CSS styling, JS logic
- **Maintainable codebase** with organized file structure
- **Reusable components** for easy extension
- **Clean APIs** between frontend and backend
- **Version control friendly** with isolated changes

### 🌐 **Frontend Architecture**
- **Vanilla JavaScript** with modern ES6+ features
- **No framework dependencies** for fast loading
- **External library integration**:
  - **marked.js** for markdown parsing
  - **highlight.js** for syntax highlighting
- **Modular function organization**
- **Event-driven architecture**
- **Progressive enhancement** approach

## 📊 **Analytics & Insights**

### 📈 **Conversation Analytics**
- **Message count tracking** per conversation
- **Average response times** calculation
- **Token usage statistics** and trends
- **Model performance comparison** across conversations
- **Usage patterns** and conversation metrics
- **Markdown usage analytics** - tracking formatted content

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

### 🌐 **Frontend Technologies**
- **HTML5** with semantic markup
- **CSS3** with modern features (Grid, Flexbox, Custom Properties)
- **Vanilla JavaScript** with ES6+ async/await
- **External Libraries**:
  - **marked.js 5.1.1** - Fast markdown parser
  - **highlight.js 11.9.0** - Syntax highlighting
- **Web APIs integration** (Clipboard, Fetch, etc.)
- **Accessibility best practices** (ARIA, semantic HTML)

### 🗄️ **Database Schema**
- **Normalized design** with proper relationships
- **Optimized indexes** for query performance
- **Constraint enforcement** for data integrity
- **Migration support** for schema updates
- **Backup-friendly** design with SQLite

## 🔧 **Configuration Options**

*For detailed configuration settings, environment variables, and examples, see [config.md](config.md)*

## 🎯 **Use Cases**

### 👩‍💻 **Development & Programming**
- **AI-assisted coding** with syntax-highlighted code examples
- **Code documentation** with markdown formatting
- **Code review** sessions with formatted explanations
- **Algorithm discussions** with mathematical notation
- **API documentation** with structured formatting
- **Technical tutorials** with step-by-step code examples

### 📚 **Research & Learning**
- **Interactive learning** with formatted educational content
- **Research papers** discussion with citation formatting
- **Mathematical explanations** with proper notation
- **Scientific documentation** with structured presentations
- **Note-taking** with rich formatting options
- **Knowledge base building** with organized content

### 💼 **Business & Content Creation**
- **Technical documentation** with professional formatting
- **Meeting notes** with structured layouts
- **Content planning** with organized lists and headers
- **Project documentation** with tables and structured data
- **Training materials** with formatted content
- **Process documentation** with clear step-by-step formatting

### 🎓 **Education & Training**
- **Coding tutorials** with syntax-highlighted examples
- **Technical explanations** with formatted content
- **Learning materials** with structured presentations
- **Assignment help** with proper code formatting
- **Study guides** with organized information hierarchy

---

## 🛠️ **Installation & Setup**

### Prerequisites
- Python 3.7 or higher
- Ollama server running locally or remotely
- At least one Ollama model installed
- Modern web browser with JavaScript enabled

### Quick Start
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd chat-o-llama
   ```

2. **Install dependencies**
   ```bash
   pip install flask requests
   ```

3. **Create directory structure**
   ```bash
   mkdir -p static/css static/js
   ```

4. **Set up files**
   - Place `index.html` in `templates/` folder
   - Place `styles.css` in `static/css/` folder  
   - Place `app.js` in `static/js/` folder

5. **Start Ollama server**
   ```bash
   ollama serve
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Open browser**
   Navigate to `http://localhost:8080`

### Configuration
1. **Create configuration files** - see [config.md](config.md) for detailed setup
2. **Set environment variables** as needed
3. **Modify database path** if required
4. **Configure Ollama models** and parameters
5. **Customize system prompts** and response settings

### Troubleshooting
- **Models not loading**: Ensure Ollama is running and models are installed
- **Markdown not rendering**: Check browser JavaScript console for errors
- **Copy functionality not working**: Ensure HTTPS or localhost for Clipboard API
- **Syntax highlighting missing**: Verify highlight.js CDN is accessible

---

## 🆕 **Recent Updates**

### **v2.0 - Enhanced Markdown & Code Support**
- ✅ **Full markdown rendering** with GitHub-flavored syntax
- ✅ **Syntax highlighting** for 190+ programming languages
- ✅ **Individual code block copy** buttons
- ✅ **Professional code presentation** with language headers
- ✅ **Enhanced copy functionality** with smart text extraction
- ✅ **Modular file structure** for better maintainability
- ✅ **Improved error handling** and user feedback
- ✅ **Mobile-optimized** code viewing and copying

### **Key Improvements**
- **Better developer experience** with proper code formatting
- **Enhanced readability** with professional typography
- **Improved accessibility** with better contrast and structure
- **Maintainable codebase** with separated concerns
- **Modern web standards** with progressive enhancement

---

*chat-o-llama now combines powerful AI conversation capabilities with professional markdown rendering and code syntax highlighting, making it the ideal tool for technical discussions, coding assistance, and formatted content creation.*
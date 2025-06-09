# 🔌 chat-o-llama API Documentation

Complete REST API reference for chat-o-llama with examples and integration guides.

## 📋 Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [API Endpoints](#api-endpoints)
  - [Models](#models)
  - [Configuration](#configuration)
  - [Conversations](#conversations)
  - [Messages](#messages)
  - [Statistics](#statistics)
  - [Search](#search)
- [WebSocket Support](#websocket-support)
- [SDK Examples](#sdk-examples)
- [Postman Collection](#postman-collection)

---

## Overview

The chat-o-llama API provides RESTful endpoints for managing conversations, sending messages to Ollama models, and configuring the chat interface. All endpoints return JSON responses and support standard HTTP methods.

### API Features
- 🔗 **RESTful Design** - Standard HTTP methods and status codes
- 📝 **JSON Format** - All requests and responses use JSON
- 🔍 **Full-text Search** - Search conversations and messages
- ⚙️ **Configuration Management** - Runtime configuration access
- 💬 **Real-time Chat** - Streaming and non-streaming responses
- 📊 **Model Management** - Dynamic model selection and info
- ⚡ **Performance Metrics** - Response times and token tracking ⭐ *New*
- 📈 **Analytics** - Conversation statistics and insights ⭐ *New*

---

## Base URL

```
http://localhost:8080/api
```

**Production/Remote:**
```
http://your-server:port/api
```

---

## Authentication

Currently, chat-o-llama operates without authentication (local use). For production deployments, consider adding:
- API keys
- JWT tokens
- Basic authentication
- OAuth integration

---

## Response Format

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional success message"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error description",
  "code": "ERROR_CODE",
  "details": { ... }
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error

---

## Error Handling

### Common Error Types

#### Validation Error (400)
```json
{
  "error": "Missing required field: message",
  "code": "VALIDATION_ERROR",
  "field": "message"
}
```

#### Not Found Error (404)
```json
{
  "error": "Conversation not found",
  "code": "NOT_FOUND",
  "resource": "conversation",
  "id": 123
}
```

#### Server Error (500)
```json
{
  "error": "Ollama service unavailable",
  "code": "OLLAMA_ERROR",
  "details": "Connection timeout"
}
```

---

## Rate Limiting

Currently no rate limiting is implemented. For production use, consider implementing:
- Request per minute limits
- Concurrent request limits
- Model-specific limits

---

# API Endpoints

## Models

### GET /api/models
Get list of available Ollama models.

#### Request
```http
GET /api/models HTTP/1.1
Host: localhost:8080
Content-Type: application/json
```

#### Response
```json
{
  "models": [
    "qwen2.5:0.5b",
    "llama3.2:1b",
    "phi3:mini",
    "tinyllama"
  ],
  "count": 4,
  "ollama_url": "http://localhost:11434"
}
```

#### Error Response
```json
{
  "models": [],
  "count": 0,
  "error": "Connection to Ollama failed",
  "ollama_url": "http://localhost:11434"
}
```

#### cURL Example
```bash
curl -X GET http://localhost:8080/api/models
```

#### JavaScript Example
```javascript
const response = await fetch('/api/models');
const data = await response.json();
console.log('Available models:', data.models);
```

---

## Configuration

### GET /api/config
Get current application configuration (excluding sensitive data).

#### Request
```http
GET /api/config HTTP/1.1
Host: localhost:8080
```

#### Response
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
    "repeat_penalty": 1.1,
    "stop": ["\n\nHuman:", "\n\nUser:"]
  },
  "performance": {
    "context_history_limit": 10,
    "num_thread": -1,
    "num_gpu": 0,
    "use_mlock": true,
    "use_mmap": true
  },
  "response_optimization": {
    "stream": false,
    "keep_alive": "5m",
    "low_vram": false,
    "f16_kv": true,
    "logits_all": false,
    "vocab_only": false,
    "embedding_only": false,
    "numa": false
  }
}
```

#### cURL Example
```bash
curl -X GET http://localhost:8080/api/config
```

#### Python Example
```python
import requests

response = requests.get('http://localhost:8080/api/config')
config = response.json()
print(f"Timeout: {config['timeouts']['ollama_timeout']}s")
```

---

## Conversations

### GET /api/conversations
Get list of all conversations ordered by last update.

#### Request
```http
GET /api/conversations HTTP/1.1
Host: localhost:8080
```

#### Query Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Number of conversations to return (default: all) |
| `offset` | integer | Number of conversations to skip |

#### Response
```json
{
  "conversations": [
    {
      "id": 1,
      "title": "Python Development Help",
      "model": "qwen2.5:0.5b",
      "created_at": "2025-06-08T10:30:00Z",
      "updated_at": "2025-06-08T11:45:30Z"
    },
    {
      "id": 2,
      "title": "Recipe Ideas",
      "model": "llama3.2:1b",
      "created_at": "2025-06-08T09:15:00Z",
      "updated_at": "2025-06-08T09:45:00Z"
    }
  ]
}
```

#### cURL Example
```bash
curl -X GET http://localhost:8080/api/conversations
```

### POST /api/conversations
Create a new conversation.

#### Request
```http
POST /api/conversations HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "title": "New Project Discussion",
  "model": "qwen2.5:0.5b"
}
```

#### Request Body
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Conversation title |
| `model` | string | Yes | Ollama model to use |

#### Response
```json
{
  "conversation_id": 3
}
```

#### cURL Example
```bash
curl -X POST http://localhost:8080/api/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "title": "New Project Discussion",
    "model": "qwen2.5:0.5b"
  }'
```

#### JavaScript Example
```javascript
const newConversation = await fetch('/api/conversations', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: 'New Project Discussion',
    model: 'qwen2.5:0.5b'
  })
});

const conversation = await newConversation.json();
console.log('Created conversation:', conversation.conversation_id);
```

### GET /api/conversations/{id} ⭐ *Enhanced*
Get specific conversation with all messages and statistics.

#### Request
```http
GET /api/conversations/1 HTTP/1.1
Host: localhost:8080
```

#### Response
```json
{
  "conversation": {
    "id": 1,
    "title": "Python Development Help",
    "model": "qwen2.5:0.5b",
    "created_at": "2025-06-08T10:30:00Z",
    "updated_at": "2025-06-08T11:45:30Z"
  },
  "messages": [
    {
      "id": 1,
      "conversation_id": 1,
      "role": "user",
      "content": "How do I create a virtual environment in Python?",
      "model": null,
      "timestamp": "2025-06-08T10:30:15Z",
      "response_time_ms": null,
      "estimated_tokens": 12
    },
    {
      "id": 2,
      "conversation_id": 1,
      "role": "assistant",
      "content": "To create a virtual environment in Python, you can use...",
      "model": "qwen2.5:0.5b",
      "timestamp": "2025-06-08T10:30:45Z",
      "response_time_ms": 2340,
      "estimated_tokens": 89
    }
  ],
  "stats": {
    "total_messages": 12,
    "assistant_messages": 6,
    "avg_response_time": 2156.7,
    "total_tokens": 1580
  }
}
```

#### New Fields:
- **`response_time_ms`** ⭐ - Response time in milliseconds (assistant messages only)
- **`estimated_tokens`** ⭐ - Estimated token count for all messages
- **`stats`** ⭐ - Conversation statistics object

#### Error Response (404)
```json
{
  "error": "Conversation not found"
}
```

#### cURL Example
```bash
curl -X GET http://localhost:8080/api/conversations/1
```

### PUT /api/conversations/{id}
Update conversation (rename).

#### Request
```http
PUT /api/conversations/1 HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "title": "Updated Conversation Title"
}
```

#### Request Body
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | New conversation title (max 100 chars) |

#### Response
```json
{
  "success": true,
  "title": "Updated Conversation Title"
}
```

#### Error Responses
```json
// Empty title (400)
{
  "error": "Title cannot be empty"
}

// Title too long (400)
{
  "error": "Title too long (max 100 characters)"
}

// Not found (404)
{
  "error": "Conversation not found"
}
```

#### cURL Example
```bash
curl -X PUT http://localhost:8080/api/conversations/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Conversation Title"}'
```

### DELETE /api/conversations/{id}
Delete conversation and all its messages.

#### Request
```http
DELETE /api/conversations/1 HTTP/1.1
Host: localhost:8080
```

#### Response
```json
{
  "success": true
}
```

#### cURL Example
```bash
curl -X DELETE http://localhost:8080/api/conversations/1
```

---

## Messages

### POST /api/chat ⭐ *Enhanced*
Send a message and get AI response with performance metrics.

#### Request
```http
POST /api/chat HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "conversation_id": 1,
  "message": "Explain machine learning in simple terms",
  "model": "qwen2.5:0.5b"
}
```

#### Request Body
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `conversation_id` | integer | Yes | Target conversation ID |
| `message` | string | Yes | User message content |
| `model` | string | Yes | Ollama model to use |

#### Response ⭐ *Enhanced with metrics*
```json
{
  "response": "Machine learning is a type of artificial intelligence where computers learn patterns from data to make predictions or decisions without being explicitly programmed for each task...",
  "model": "qwen2.5:0.5b",
  "response_time_ms": 2340,
  "estimated_tokens": 247,
  "metrics": {
    "eval_count": 247,
    "eval_duration": 2100000000,
    "load_duration": 45000000,
    "prompt_eval_count": 89,
    "prompt_eval_duration": 240000000,
    "total_duration": 2340000000
  }
}
```

#### New Response Fields ⭐:
- **`response_time_ms`** - Total response time in milliseconds
- **`estimated_tokens`** - Estimated token count for the response
- **`metrics`** - Detailed Ollama performance metrics:
  - `eval_count` - Actual tokens generated (if available)
  - `eval_duration` - Token generation time (nanoseconds)
  - `load_duration` - Model loading time (nanoseconds)
  - `prompt_eval_count` - Input prompt tokens
  - `prompt_eval_duration` - Prompt processing time (nanoseconds)
  - `total_duration` - Total request duration (nanoseconds)

#### Performance Calculation Examples:
```javascript
// Tokens per second calculation
const tokensPerSecond = data.estimated_tokens / (data.response_time_ms / 1000);

// Convert nanoseconds to milliseconds
const loadTimeMs = data.metrics.load_duration / 1000000;
const evalTimeMs = data.metrics.eval_duration / 1000000;
```

#### Error Responses
```json
// Missing fields (400)
{
  "error": "Missing conversation_id or message"
}

// Ollama error (500)
{
  "error": "Error connecting to Ollama: Connection timeout"
}
```

#### cURL Example
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": 1,
    "message": "Explain machine learning in simple terms",
    "model": "qwen2.5:0.5b"
  }'
```

#### Python Example
```python
import requests

response = requests.post('http://localhost:8080/api/chat', json={
    'conversation_id': 1,
    'message': 'Explain machine learning in simple terms',
    'model': 'qwen2.5:0.5b'
})

data = response.json()
print(f"AI Response: {data['response']}")
print(f"Response Time: {data['response_time_ms']}ms")
print(f"Tokens: ~{data['estimated_tokens']}")
print(f"Speed: {data['estimated_tokens'] / (data['response_time_ms'] / 1000):.1f} tokens/sec")
```

#### JavaScript Example
```javascript
const chatResponse = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    conversation_id: 1,
    message: 'Explain machine learning in simple terms',
    model: 'qwen2.5:0.5b'
  })
});

const data = await chatResponse.json();
console.log('AI Response:', data.response);
console.log(`Performance: ${data.response_time_ms}ms, ~${data.estimated_tokens} tokens`);
console.log(`Speed: ${(data.estimated_tokens / (data.response_time_ms / 1000)).toFixed(1)} tok/s`);
```

---

## Statistics ⭐ *New Section*

### GET /api/stats/{conversation_id} ⭐ *New*
Get detailed conversation statistics and analytics.

#### Request
```http
GET /api/stats/1 HTTP/1.1
Host: localhost:8080
```

#### Response
```json
{
  "summary": {
    "total_messages": 24,
    "assistant_messages": 12,
    "avg_response_time": 2156.7,
    "total_tokens": 3240
  },
  "by_role": [
    {
      "role": "user",
      "count": 12,
      "avg_length": 45.3,
      "total_tokens": 156,
      "avg_response_time": null
    },
    {
      "role": "assistant",
      "count": 12,
      "avg_length": 287.5,
      "total_tokens": 3084,
      "avg_response_time": 2156.7
    }
  ]
}
```

#### Response Fields:
- **`summary`** - Overall conversation statistics:
  - `total_messages` - Total message count
  - `assistant_messages` - Number of AI responses
  - `avg_response_time` - Average response time in milliseconds
  - `total_tokens` - Total tokens used by assistant

- **`by_role`** - Statistics broken down by user/assistant:
  - `role` - "user" or "assistant"
  - `count` - Number of messages
  - `avg_length` - Average character length
  - `total_tokens` - Total tokens used
  - `avg_response_time` - Average response time (assistant only)

#### cURL Example
```bash
curl -X GET http://localhost:8080/api/stats/1
```

#### Python Example
```python
import requests

response = requests.get('http://localhost:8080/api/stats/1')
stats = response.json()

print(f"Total messages: {stats['summary']['total_messages']}")
print(f"Average response time: {stats['summary']['avg_response_time']:.1f}ms")
print(f"Total tokens used: {stats['summary']['total_tokens']}")

for role_stats in stats['by_role']:
    role = role_stats['role']
    count = role_stats['count']
    tokens = role_stats['total_tokens']
    print(f"{role.title()}: {count} messages, {tokens} tokens")
```

#### Use Cases:
- **Performance monitoring** - Track AI response times
- **Usage analytics** - Monitor token consumption and costs
- **Conversation insights** - Understand chat patterns
- **Optimization** - Identify performance bottlenecks

---

## Search

### GET /api/search ⭐ *Enhanced*
Search conversations and messages with performance metrics.

#### Request
```http
GET /api/search?q=machine%20learning HTTP/1.1
Host: localhost:8080
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `limit` | integer | No | Max results (default: 50) |

#### Response ⭐ *Enhanced with metrics*
```json
{
  "results": [
    {
      "id": 1,
      "title": "AI Development Discussion",
      "model": "qwen2.5:0.5b",
      "updated_at": "2025-06-08T11:45:30Z",
      "content": "Machine learning is a subset of artificial intelligence...",
      "role": "assistant",
      "timestamp": "2025-06-08T11:30:00Z",
      "response_time_ms": 1890,
      "estimated_tokens": 156
    },
    {
      "id": 2,
      "title": "Python ML Libraries",
      "model": "llama3.2:1b",
      "updated_at": "2025-06-08T10:20:00Z",
      "content": "What are the best machine learning libraries for Python?",
      "role": "user",
      "timestamp": "2025-06-08T10:15:00Z",
      "response_time_ms": null,
      "estimated_tokens": 12
    }
  ],
  "query": "machine learning",
  "count": 2
}
```

#### New Fields in Results ⭐:
- **`response_time_ms`** - Response time for assistant messages (null for user messages)
- **`estimated_tokens`** - Token count for messages

#### Empty Response
```json
{
  "results": [],
  "query": "nonexistent term",
  "count": 0
}
```

#### cURL Example
```bash
curl -X GET "http://localhost:8080/api/search?q=machine%20learning"
```

#### JavaScript Example
```javascript
const searchResults = await fetch('/api/search?q=' + encodeURIComponent('machine learning'));
const data = await searchResults.json();

console.log(`Found ${data.count} results:`);
data.results.forEach(result => {
  console.log(`- ${result.title}: ${result.content.substring(0, 50)}...`);
  if (result.response_time_ms) {
    console.log(`  Performance: ${result.response_time_ms}ms, ~${result.estimated_tokens} tokens`);
  }
});
```

---

## WebSocket Support

*Note: WebSocket support is planned for future releases to enable real-time streaming responses.*

### Planned WebSocket Endpoints

#### /ws/chat
Real-time chat with streaming responses.

```javascript
// Planned implementation
const ws = new WebSocket('ws://localhost:8080/ws/chat');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'token') {
    // Append token to response
    console.log('Token:', data.content);
  } else if (data.type === 'metrics') {
    // Performance metrics
    console.log('Response time:', data.response_time_ms);
  }
};

ws.send(JSON.stringify({
  conversation_id: 1,
  message: 'Tell me a story',
  model: 'qwen2.5:0.5b'
}));
```

---

## SDK Examples

### Python SDK Example ⭐ *Updated with metrics*

```python
import requests
from typing import List, Dict, Optional

class ChatOLlamaAPI:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"

    def get_models(self) -> List[str]:
        """Get available Ollama models."""
        response = requests.get(f"{self.api_url}/models")
        response.raise_for_status()
        return response.json()["models"]

    def create_conversation(self, title: str, model: str) -> int:
        """Create a new conversation."""
        response = requests.post(f"{self.api_url}/conversations", json={
            "title": title,
            "model": model
        })
        response.raise_for_status()
        return response.json()["conversation_id"]

    def send_message(self, conversation_id: int, message: str, model: str) -> Dict:
        """Send a message and get AI response with metrics."""
        response = requests.post(f"{self.api_url}/chat", json={
            "conversation_id": conversation_id,
            "message": message,
            "model": model
        })
        response.raise_for_status()
        return response.json()

    def get_conversation_stats(self, conversation_id: int) -> Dict:
        """Get detailed conversation statistics."""
        response = requests.get(f"{self.api_url}/stats/{conversation_id}")
        response.raise_for_status()
        return response.json()

    def search(self, query: str, limit: int = 50) -> List[Dict]:
        """Search conversations and messages."""
        response = requests.get(f"{self.api_url}/search", params={
            "q": query,
            "limit": limit
        })
        response.raise_for_status()
        return response.json()["results"]

# Usage example with metrics
api = ChatOLlamaAPI()

# Get available models
models = api.get_models()
print(f"Available models: {models}")

# Create a conversation
conv_id = api.create_conversation("Python Help", "qwen2.5:0.5b")
print(f"Created conversation: {conv_id}")

# Send a message and get performance metrics
result = api.send_message(conv_id, "What is Python?", "qwen2.5:0.5b")
print(f"AI Response: {result['response']}")
print(f"Performance: {result['response_time_ms']}ms, ~{result['estimated_tokens']} tokens")
print(f"Speed: {result['estimated_tokens'] / (result['response_time_ms'] / 1000):.1f} tok/s")

# Get conversation statistics
stats = api.get_conversation_stats(conv_id)
print(f"Conversation stats: {stats['summary']}")

# Search conversations with metrics
results = api.search("Python")
print(f"Found {len(results)} search results")
for result in results:
    if result['response_time_ms']:
        print(f"- Response time: {result['response_time_ms']}ms")
```

### Node.js SDK Example ⭐ *Updated with metrics*

```javascript
class ChatOLlamaAPI {
    constructor(baseUrl = 'http://localhost:8080') {
        this.baseUrl = baseUrl;
        this.apiUrl = `${baseUrl}/api`;
    }

    async getModels() {
        const response = await fetch(`${this.apiUrl}/models`);
        const data = await response.json();
        return data.models;
    }

    async createConversation(title, model) {
        const response = await fetch(`${this.apiUrl}/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, model })
        });
        const data = await response.json();
        return data.conversation_id;
    }

    async sendMessage(conversationId, message, model) {
        const response = await fetch(`${this.apiUrl}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                conversation_id: conversationId,
                message,
                model
            })
        });
        const data = await response.json();
        return data; // Returns full response with metrics
    }

    async getConversationStats(conversationId) {
        const response = await fetch(`${this.apiUrl}/stats/${conversationId}`);
        const data = await response.json();
        return data;
    }

    async search(query, limit = 50) {
        const response = await fetch(`${this.apiUrl}/search?q=${encodeURIComponent(query)}&limit=${limit}`);
        const data = await response.json();
        return data.results;
    }
}

// Usage example with metrics
const api = new ChatOLlamaAPI();

(async () => {
    // Get available models
    const models = await api.getModels();
    console.log('Available models:', models);

    // Create a conversation
    const convId = await api.createConversation('JavaScript Help', 'qwen2.5:0.5b');
    console.log('Created conversation:', convId);

    // Send a message and get performance metrics
    const result = await api.sendMessage(convId, 'Explain async/await', 'qwen2.5:0.5b');
    console.log('AI Response:', result.response);
    console.log(`Performance: ${result.response_time_ms}ms, ~${result.estimated_tokens} tokens`);
    console.log(`Speed: ${(result.estimated_tokens / (result.response_time_ms / 1000)).toFixed(1)} tok/s`);

    // Get conversation statistics
    const stats = await api.getConversationStats(convId);
    console.log('Conversation stats:', stats.summary);

    // Search conversations with metrics
    const results = await api.search('JavaScript');
    console.log('Found results:', results.length);
    results.forEach(result => {
        if (result.response_time_ms) {
            console.log(`- Performance: ${result.response_time_ms}ms, ~${result.estimated_tokens} tokens`);
        }
    });
})();
```

---

## Postman Collection ⭐ *Updated*

### Import Collection

Create a Postman collection with these requests:

```json
{
  "info": {
    "name": "chat-o-llama API v1.1",
    "description": "Complete API collection for chat-o-llama with metrics",
    "version": "1.1.0"
  },
  "variable": [
    {
      "key": "baseUrl",
      "value": "http://localhost:8080/api"
    }
  ],
  "item": [
    {
      "name": "Get Models",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/models"
      }
    },
    {
      "name": "Get Configuration",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/config"
      }
    },
    {
      "name": "Create Conversation",
      "request": {
        "method": "POST",
        "url": "{{baseUrl}}/conversations",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"title\": \"Test Conversation\",\n  \"model\": \"qwen2.5:0.5b\"\n}"
        }
      }
    },
    {
      "name": "Send Message (Enhanced)",
      "request": {
        "method": "POST",
        "url": "{{baseUrl}}/chat",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"conversation_id\": 1,\n  \"message\": \"Hello, how are you?\",\n  \"model\": \"qwen2.5:0.5b\"\n}"
        }
      },
      "test": "pm.test('Response includes metrics', function () {\n    const responseJson = pm.response.json();\n    pm.expect(responseJson).to.have.property('response_time_ms');\n    pm.expect(responseJson).to.have.property('estimated_tokens');\n    pm.expect(responseJson).to.have.property('metrics');\n});"
    },
    {
      "name": "Get Conversation Stats",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/stats/1"
      }
    },
    {
      "name": "Get Conversation with Stats",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/conversations/1"
      },
      "test": "pm.test('Response includes stats', function () {\n    const responseJson = pm.response.json();\n    pm.expect(responseJson).to.have.property('stats');\n    pm.expect(responseJson.messages[0]).to.have.property('estimated_tokens');\n});"
    },
    {
      "name": "Search with Metrics",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/search",
        "params": [
          {
            "key": "q",
            "value": "hello"
          }
        ]
      },
      "test": "pm.test('Search results include metrics', function () {\n    const responseJson = pm.response.json();\n    if (responseJson.results.length > 0) {\n        pm.expect(responseJson.results[0]).to.have.property('estimated_tokens');\n    }\n});"
    }
  ]
}
```

---

## Testing and Development ⭐ *Enhanced*

### API Testing Script

```bash
#!/bin/bash
# test-api.sh - Test all API endpoints including new metrics features

BASE_URL="http://localhost:8080/api"

echo "Testing chat-o-llama API v1.1 with metrics..."

# Test models endpoint
echo "1. Testing /api/models"
curl -s "$BASE_URL/models" | jq .

# Test config endpoint
echo -e "\n2. Testing /api/config"
curl -s "$BASE_URL/config" | jq .

# Create a test conversation
echo -e "\n3. Creating test conversation"
CONV_RESPONSE=$(curl -s -X POST "$BASE_URL/conversations" \
  -H "Content-Type: application/json" \
  -d '{"title": "API Test with Metrics", "model": "qwen2.5:0.5b"}')

CONV_ID=$(echo "$CONV_RESPONSE" | jq -r .conversation_id)
echo "Created conversation ID: $CONV_ID"

# Send a test message and check metrics
echo -e "\n4. Sending test message (checking metrics)"
CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\": $CONV_ID, \"message\": \"Hello, this is a test\", \"model\": \"qwen2.5:0.5b\"}")

echo "$CHAT_RESPONSE" | jq .
echo "Response Time: $(echo "$CHAT_RESPONSE" | jq -r .response_time_ms)ms"
echo "Estimated Tokens: $(echo "$CHAT_RESPONSE" | jq -r .estimated_tokens)"

# Test conversation stats
echo -e "\n5. Testing conversation statistics"
curl -s "$BASE_URL/stats/$CONV_ID" | jq .

# Test enhanced conversation endpoint
echo -e "\n6. Testing enhanced conversation endpoint"
curl -s "$BASE_URL/conversations/$CONV_ID" | jq '.stats'

# Test search with metrics
echo -e "\n7. Testing search with metrics"
curl -s "$BASE_URL/search?q=test" | jq '.results[0] | {estimated_tokens, response_time_ms}'

echo -e "\nAPI testing complete!"
```

### Performance Testing ⭐ *Enhanced*

```python
import time
import requests
import concurrent.futures
from statistics import mean, median
import json

def test_chat_performance_with_metrics(num_requests=10):
    """Test chat endpoint performance with detailed metrics analysis."""

    # Create test conversation
    conv_response = requests.post('http://localhost:8080/api/conversations', json={
        'title': 'Performance Test with Metrics',
        'model': 'qwen2.5:0.5b'
    })
    conv_id = conv_response.json()['conversation_id']

    def send_message(i):
        start_time = time.time()
        response = requests.post('http://localhost:8080/api/chat', json={
            'conversation_id': conv_id,
            'message': f'Test message {i} - please respond with a short answer',
            'model': 'qwen2.5:0.5b'
        })
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            return {
                'request_time': end_time - start_time,
                'api_response_time': data.get('response_time_ms', 0) / 1000,
                'estimated_tokens': data.get('estimated_tokens', 0),
                'status_code': response.status_code,
                'tokens_per_second': data.get('estimated_tokens', 0) / (data.get('response_time_ms', 1) / 1000)
            }
        else:
            return {
                'request_time': end_time - start_time,
                'api_response_time': 0,
                'estimated_tokens': 0,
                'status_code': response.status_code,
                'tokens_per_second': 0
            }

    # Test sequential requests
    print("Testing sequential requests with metrics...")
    results = []
    for i in range(num_requests):
        result = send_message(i)
        results.append(result)
        print(f"Request {i+1}: {result['request_time']:.2f}s total, "
              f"{result['api_response_time']:.2f}s API, "
              f"~{result['estimated_tokens']} tokens, "
              f"{result['tokens_per_second']:.1f} tok/s "
              f"(HTTP {result['status_code']})")

    # Calculate statistics
    request_times = [r['request_time'] for r in results if r['status_code'] == 200]
    api_times = [r['api_response_time'] for r in results if r['status_code'] == 200]
    token_counts = [r['estimated_tokens'] for r in results if r['status_code'] == 200]
    token_speeds = [r['tokens_per_second'] for r in results if r['status_code'] == 200]

    print(f"\n📊 Performance Analysis:")
    print(f"Successful requests: {len(request_times)}/{num_requests}")
    
    if request_times:
        print(f"\n⏱️  Request Times (total including network):")
        print(f"  Mean: {mean(request_times):.2f}s")
        print(f"  Median: {median(request_times):.2f}s")
        print(f"  Min: {min(request_times):.2f}s")
        print(f"  Max: {max(request_times):.2f}s")
        
        print(f"\n🚀 API Response Times (server-side only):")
        print(f"  Mean: {mean(api_times):.2f}s")
        print(f"  Median: {median(api_times):.2f}s")
        print(f"  Min: {min(api_times):.2f}s")
        print(f"  Max: {max(api_times):.2f}s")
        
        print(f"\n🔤 Token Statistics:")
        print(f"  Mean tokens per response: {mean(token_counts):.1f}")
        print(f"  Total tokens generated: {sum(token_counts)}")
        print(f"  Mean speed: {mean(token_speeds):.1f} tokens/sec")
        print(f"  Best speed: {max(token_speeds):.1f} tokens/sec")

    # Get final conversation stats
    stats_response = requests.get(f'http://localhost:8080/api/stats/{conv_id}')
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"\n📈 Final Conversation Stats:")
        print(f"  Total messages: {stats['summary']['total_messages']}")
        print(f"  Average response time: {stats['summary']['avg_response_time']:.1f}ms")
        print(f"  Total tokens: {stats['summary']['total_tokens']}")

def test_concurrent_performance(num_concurrent=5, num_requests_each=3):
    """Test concurrent request performance."""
    
    print(f"\n🔀 Testing {num_concurrent} concurrent clients, {num_requests_each} requests each...")
    
    # Create test conversation
    conv_response = requests.post('http://localhost:8080/api/conversations', json={
        'title': 'Concurrent Performance Test',
        'model': 'qwen2.5:0.5b'
    })
    conv_id = conv_response.json()['conversation_id']
    
    def worker(worker_id):
        results = []
        for i in range(num_requests_each):
            start_time = time.time()
            response = requests.post('http://localhost:8080/api/chat', json={
                'conversation_id': conv_id,
                'message': f'Concurrent test from worker {worker_id}, request {i}',
                'model': 'qwen2.5:0.5b'
            })
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                results.append({
                    'worker_id': worker_id,
                    'request_id': i,
                    'total_time': end_time - start_time,
                    'api_time': data.get('response_time_ms', 0) / 1000,
                    'tokens': data.get('estimated_tokens', 0)
                })
            else:
                print(f"Worker {worker_id} request {i} failed: HTTP {response.status_code}")
        
        return results
    
    # Run concurrent requests
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(worker, i) for i in range(num_concurrent)]
        all_results = []
        for future in concurrent.futures.as_completed(futures):
            all_results.extend(future.result())
    
    total_time = time.time() - start_time
    
    # Analyze results
    if all_results:
        total_times = [r['total_time'] for r in all_results]
        api_times = [r['api_time'] for r in all_results]
        total_tokens = sum(r['tokens'] for r in all_results)
        
        print(f"Completed {len(all_results)} concurrent requests in {total_time:.2f}s")
        print(f"Average total time: {mean(total_times):.2f}s")
        print(f"Average API time: {mean(api_times):.2f}s")
        print(f"Total tokens generated: {total_tokens}")
        print(f"Throughput: {len(all_results) / total_time:.2f} requests/sec")

if __name__ == "__main__":
    print("🧪 chat-o-llama API Performance Testing with Metrics")
    test_chat_performance_with_metrics(5)
    test_concurrent_performance(3, 2)
```

### Metrics Dashboard Example ⭐ *New*

```html
<!DOCTYPE html>
<html>
<head>
    <title>chat-o-llama Metrics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .metric-card { 
            display: inline-block; 
            margin: 10px; 
            padding: 20px; 
            border: 1px solid #ddd; 
            border-radius: 8px; 
            min-width: 200px;
        }
        .metric-value { font-size: 2em; font-weight: bold; color: #0066cc; }
        .metric-label { color: #666; }
        .chart-container { width: 400px; height: 300px; margin: 20px; }
    </style>
</head>
<body>
    <h1>chat-o-llama Metrics Dashboard</h1>
    
    <div id="metrics-cards"></div>
    
    <div class="chart-container">
        <canvas id="responseTimeChart"></canvas>
    </div>
    
    <div class="chart-container">
        <canvas id="tokenUsageChart"></canvas>
    </div>

    <script>
        async function loadMetrics() {
            try {
                // Get all conversations
                const conversationsResponse = await fetch('/api/conversations');
                const conversations = await conversationsResponse.json();
                
                let totalMessages = 0;
                let totalTokens = 0;
                let totalResponseTime = 0;
                let responseCount = 0;
                
                const responseTimeData = [];
                const tokenUsageData = [];
                
                // Collect stats from each conversation
                for (const conv of conversations.conversations) {
                    const statsResponse = await fetch(`/api/stats/${conv.id}`);
                    if (statsResponse.ok) {
                        const stats = await statsResponse.json();
                        
                        totalMessages += stats.summary.total_messages;
                        totalTokens += stats.summary.total_tokens || 0;
                        
                        if (stats.summary.avg_response_time) {
                            totalResponseTime += stats.summary.avg_response_time;
                            responseCount++;
                            
                            responseTimeData.push({
                                conversation: conv.title,
                                responseTime: stats.summary.avg_response_time
                            });
                        }
                        
                        if (stats.summary.total_tokens) {
                            tokenUsageData.push({
                                conversation: conv.title,
                                tokens: stats.summary.total_tokens
                            });
                        }
                    }
                }
                
                // Display metric cards
                const avgResponseTime = responseCount > 0 ? (totalResponseTime / responseCount) : 0;
                const metricsHtml = `
                    <div class="metric-card">
                        <div class="metric-value">${totalMessages}</div>
                        <div class="metric-label">Total Messages</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${totalTokens.toLocaleString()}</div>
                        <div class="metric-label">Total Tokens</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${avgResponseTime.toFixed(0)}ms</div>
                        <div class="metric-label">Avg Response Time</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${conversations.conversations.length}</div>
                        <div class="metric-label">Total Conversations</div>
                    </div>
                `;
                
                document.getElementById('metrics-cards').innerHTML = metricsHtml;
                
                // Create response time chart
                if (responseTimeData.length > 0) {
                    new Chart(document.getElementById('responseTimeChart'), {
                        type: 'bar',
                        data: {
                            labels: responseTimeData.map(d => d.conversation.substring(0, 20) + '...'),
                            datasets: [{
                                label: 'Average Response Time (ms)',
                                data: responseTimeData.map(d => d.responseTime),
                                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                                borderColor: 'rgba(54, 162, 235, 1)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                title: {
                                    display: true,
                                    text: 'Response Time by Conversation'
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    title: {
                                        display: true,
                                        text: 'Response Time (ms)'
                                    }
                                }
                            }
                        }
                    });
                }
                
                // Create token usage chart
                if (tokenUsageData.length > 0) {
                    new Chart(document.getElementById('tokenUsageChart'), {
                        type: 'doughnut',
                        data: {
                            labels: tokenUsageData.map(d => d.conversation.substring(0, 20) + '...'),
                            datasets: [{
                                label: 'Token Usage',
                                data: tokenUsageData.map(d => d.tokens),
                                backgroundColor: [
                                    'rgba(255, 99, 132, 0.6)',
                                    'rgba(54, 162, 235, 0.6)',
                                    'rgba(255, 205, 86, 0.6)',
                                    'rgba(75, 192, 192, 0.6)',
                                    'rgba(153, 102, 255, 0.6)',
                                ]
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                title: {
                                    display: true,
                                    text: 'Token Usage by Conversation'
                                },
                                legend: {
                                    position: 'bottom'
                                }
                            }
                        }
                    });
                }
                
            } catch (error) {
                console.error('Error loading metrics:', error);
            }
        }
        
        // Load metrics on page load
        loadMetrics();
        
        // Refresh every 30 seconds
        setInterval(loadMetrics, 30000);
    </script>
</body>
</html>
```

---

## API Changelog ⭐ *Updated*

### Version 1.1.0 (Current)
- ✅ **Performance Metrics** - Response times and token tracking
- ✅ **Enhanced `/api/chat`** - Returns metrics with AI responses
- ✅ **Enhanced `/api/conversations/{id}`** - Includes conversation statistics
- ✅ **Enhanced `/api/search`** - Results include performance metrics
- ✅ **New `/api/stats/{id}`** - Detailed conversation analytics
- ✅ **Database Schema Updates** - Added metrics columns
- ✅ **Backwards Compatibility** - All existing endpoints still work
- ✅ **SDK Updates** - Python and Node.js examples with metrics

### Version 1.0.0 (Previous)
- ✅ Basic CRUD operations for conversations
- ✅ Chat messaging with Ollama integration
- ✅ Full-text search functionality
- ✅ Configuration access endpoint
- ✅ Model listing and selection

### Planned Features (v1.2.0)
- 🔄 WebSocket support for streaming responses with real-time metrics
- 🔐 Authentication and authorization
- 📊 Advanced analytics dashboard
- 📁 File upload and processing with size/processing metrics
- 🎛️ Runtime configuration updates
- 📈 Historical performance trends
- 🚨 Performance alerting and monitoring
- 💾 Metrics export (CSV, JSON)

---

## Migration Guide ⭐ *New*

### Upgrading from v1.0.0 to v1.1.0

#### ✅ **Backwards Compatible Changes**
All existing API calls continue to work without modification. New metrics fields are additive.

#### 🔄 **Enhanced Responses**
Update your code to handle new metrics fields:

**Before (v1.0.0):**
```javascript
const response = await fetch('/api/chat', { /* ... */ });
const data = await response.json();
console.log(data.response); // Just the AI response text
```

**After (v1.1.0):**
```javascript
const response = await fetch('/api/chat', { /* ... */ });
const data = await response.json();
console.log(data.response); // Still works!
console.log(`Performance: ${data.response_time_ms}ms, ~${data.estimated_tokens} tokens`);
```

#### 📊 **New Analytics Endpoints**
Take advantage of new statistics:

```javascript
// Get detailed conversation analytics
const stats = await fetch('/api/stats/1');
const data = await stats.json();
console.log(`Average response time: ${data.summary.avg_response_time}ms`);
console.log(`Total tokens used: ${data.summary.total_tokens}`);
```

#### 🗄️ **Database Migration**
The database schema is automatically updated when you run the enhanced version. No manual migration required.

---

## Support and Contributing ⭐ *Updated*

**API Issues:** Report API bugs and feature requests on [GitHub Issues](https://github.com/ukkit/chat-o-llama/issues)

**Performance Issues:** Use the new metrics endpoints to gather performance data when reporting issues

**API Contributions:** Submit pull requests for API improvements

**Documentation:** Help improve this API documentation

**Testing:** Share your API integration examples and test cases

**Metrics & Analytics:** Contribute dashboard templates and monitoring tools

---

*This API documentation is for chat-o-llama v1.1.0 with enhanced metrics features. For the latest updates, check the [GitHub repository](https://github.com/ukkit/chat-o-llama).*
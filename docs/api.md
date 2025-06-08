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

---

## Base URL

```
http://localhost:3000/api
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
Host: localhost:3000
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
curl -X GET http://localhost:3000/api/models
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
Host: localhost:3000
```

#### Response
```json
{
  "timeouts": {
    "ollama_timeout": 600,
    "ollama_connect_timeout": 45
  },
  "model_options": {
    "temperature": 0.1,
    "top_p": 0.95,
    "top_k": 50,
    "num_predict": 4096,
    "num_ctx": 8192,
    "repeat_penalty": 1.15
  },
  "performance": {
    "context_history_limit": 15,
    "num_thread": -1,
    "num_gpu": 0,
    "num_batch": 1
  },
  "response_optimization": {
    "stream": false,
    "keep_alive": "10m",
    "low_vram": false,
    "f16_kv": false
  }
}
```

#### cURL Example
```bash
curl -X GET http://localhost:3000/api/config
```

#### Python Example
```python
import requests

response = requests.get('http://localhost:3000/api/config')
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
Host: localhost:3000
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
curl -X GET http://localhost:3000/api/conversations
```

### POST /api/conversations
Create a new conversation.

#### Request
```http
POST /api/conversations HTTP/1.1
Host: localhost:3000
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
  "conversation_id": 3,
  "title": "New Project Discussion",
  "model": "qwen2.5:0.5b",
  "created_at": "2025-06-08T12:00:00Z"
}
```

#### cURL Example
```bash
curl -X POST http://localhost:3000/api/conversations \
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

### GET /api/conversations/{id}
Get specific conversation with all messages.

#### Request
```http
GET /api/conversations/1 HTTP/1.1
Host: localhost:3000
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
      "timestamp": "2025-06-08T10:30:15Z"
    },
    {
      "id": 2,
      "conversation_id": 1,
      "role": "assistant",
      "content": "To create a virtual environment in Python, you can use...",
      "model": "qwen2.5:0.5b",
      "timestamp": "2025-06-08T10:30:45Z"
    }
  ]
}
```

#### Error Response (404)
```json
{
  "error": "Conversation not found"
}
```

#### cURL Example
```bash
curl -X GET http://localhost:3000/api/conversations/1
```

### PUT /api/conversations/{id}
Update conversation (rename).

#### Request
```http
PUT /api/conversations/1 HTTP/1.1
Host: localhost:3000
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
curl -X PUT http://localhost:3000/api/conversations/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Conversation Title"}'
```

### DELETE /api/conversations/{id}
Delete conversation and all its messages.

#### Request
```http
DELETE /api/conversations/1 HTTP/1.1
Host: localhost:3000
```

#### Response
```json
{
  "success": true
}
```

#### cURL Example
```bash
curl -X DELETE http://localhost:3000/api/conversations/1
```

---

## Messages

### POST /api/chat
Send a message and get AI response.

#### Request
```http
POST /api/chat HTTP/1.1
Host: localhost:3000
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

#### Response
```json
{
  "response": "Machine learning is a type of artificial intelligence where computers learn patterns from data to make predictions or decisions without being explicitly programmed for each task...",
  "model": "qwen2.5:0.5b",
  "timestamp": "2025-06-08T12:15:30Z",
  "processing_time": 2.34
}
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
curl -X POST http://localhost:3000/api/chat \
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

response = requests.post('http://localhost:3000/api/chat', json={
    'conversation_id': 1,
    'message': 'Explain machine learning in simple terms',
    'model': 'qwen2.5:0.5b'
})

data = response.json()
print(f"AI Response: {data['response']}")
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
```

---

## Search

### GET /api/search
Search conversations and messages.

#### Request
```http
GET /api/search?q=machine%20learning HTTP/1.1
Host: localhost:3000
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `limit` | integer | No | Max results (default: 50) |

#### Response
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
      "timestamp": "2025-06-08T11:30:00Z"
    },
    {
      "id": 2,
      "title": "Python ML Libraries",
      "model": "llama3.2:1b",
      "updated_at": "2025-06-08T10:20:00Z",
      "content": "What are the best machine learning libraries for Python?",
      "role": "user",
      "timestamp": "2025-06-08T10:15:00Z"
    }
  ],
  "query": "machine learning",
  "count": 2
}
```

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
curl -X GET "http://localhost:3000/api/search?q=machine%20learning"
```

#### JavaScript Example
```javascript
const searchResults = await fetch('/api/search?q=' + encodeURIComponent('machine learning'));
const data = await searchResults.json();
console.log(`Found ${data.count} results:`, data.results);
```

---

## WebSocket Support

*Note: WebSocket support is planned for future releases to enable real-time streaming responses.*

### Planned WebSocket Endpoints

#### /ws/chat
Real-time chat with streaming responses.

```javascript
// Planned implementation
const ws = new WebSocket('ws://localhost:3000/ws/chat');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'token') {
    // Append token to response
    console.log('Token:', data.content);
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

### Python SDK Example

```python
import requests
from typing import List, Dict, Optional

class ChatOLlamaAPI:
    def __init__(self, base_url: str = "http://localhost:3000"):
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

    def send_message(self, conversation_id: int, message: str, model: str) -> str:
        """Send a message and get AI response."""
        response = requests.post(f"{self.api_url}/chat", json={
            "conversation_id": conversation_id,
            "message": message,
            "model": model
        })
        response.raise_for_status()
        return response.json()["response"]

    def search(self, query: str, limit: int = 50) -> List[Dict]:
        """Search conversations and messages."""
        response = requests.get(f"{self.api_url}/search", params={
            "q": query,
            "limit": limit
        })
        response.raise_for_status()
        return response.json()["results"]

# Usage example
api = ChatOLlamaAPI()

# Get available models
models = api.get_models()
print(f"Available models: {models}")

# Create a conversation
conv_id = api.create_conversation("Python Help", "qwen2.5:0.5b")
print(f"Created conversation: {conv_id}")

# Send a message
response = api.send_message(conv_id, "What is Python?", "qwen2.5:0.5b")
print(f"AI Response: {response}")

# Search conversations
results = api.search("Python")
print(f"Found {len(results)} search results")
```

### Node.js SDK Example

```javascript
class ChatOLlamaAPI {
    constructor(baseUrl = 'http://localhost:3000') {
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
        return data.response;
    }

    async search(query, limit = 50) {
        const response = await fetch(`${this.apiUrl}/search?q=${encodeURIComponent(query)}&limit=${limit}`);
        const data = await response.json();
        return data.results;
    }
}

// Usage example
const api = new ChatOLlamaAPI();

(async () => {
    // Get available models
    const models = await api.getModels();
    console.log('Available models:', models);

    // Create a conversation
    const convId = await api.createConversation('JavaScript Help', 'qwen2.5:0.5b');
    console.log('Created conversation:', convId);

    // Send a message
    const response = await api.sendMessage(convId, 'Explain async/await', 'qwen2.5:0.5b');
    console.log('AI Response:', response);

    // Search conversations
    const results = await api.search('JavaScript');
    console.log('Found results:', results.length);
})();
```

---

## Postman Collection

### Import Collection

Create a Postman collection with these requests:

```json
{
  "info": {
    "name": "chat-o-llama API",
    "description": "Complete API collection for chat-o-llama",
    "version": "1.0.0"
  },
  "variable": [
    {
      "key": "baseUrl",
      "value": "http://localhost:3000/api"
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
      "name": "Send Message",
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
      }
    },
    {
      "name": "Search",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/search",
        "params": [
          {
            "key": "q",
            "value": "hello"
          }
        ]
      }
    }
  ]
}
```

---

## Testing and Development

### API Testing Script

```bash
#!/bin/bash
# test-api.sh - Test all API endpoints

BASE_URL="http://localhost:3000/api"

echo "Testing chat-o-llama API..."

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
  -d '{"title": "API Test", "model": "qwen2.5:0.5b"}')

CONV_ID=$(echo "$CONV_RESPONSE" | jq -r .conversation_id)
echo "Created conversation ID: $CONV_ID"

# Send a test message
echo -e "\n4. Sending test message"
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\": $CONV_ID, \"message\": \"Hello, this is a test\", \"model\": \"qwen2.5:0.5b\"}" | jq .

# Test search
echo -e "\n5. Testing search"
curl -s "$BASE_URL/search?q=test" | jq .

echo -e "\nAPI testing complete!"
```

### Performance Testing

```python
import time
import requests
import concurrent.futures
from statistics import mean, median

def test_chat_performance(num_requests=10):
    """Test chat endpoint performance."""

    # Create test conversation
    conv_response = requests.post('http://localhost:3000/api/conversations', json={
        'title': 'Performance Test',
        'model': 'qwen2.5:0.5b'
    })
    conv_id = conv_response.json()['conversation_id']

    def send_message(i):
        start_time = time.time()
        response = requests.post('http://localhost:3000/api/chat', json={
            'conversation_id': conv_id,
            'message': f'Test message {i}',
            'model': 'qwen2.5:0.5b'
        })
        end_time = time.time()
        return end_time - start_time, response.status_code

    # Test sequential requests
    print("Testing sequential requests...")
    times = []
    for i in range(num_requests):
        duration, status = send_message(i)
        times.append(duration)
        print(f"Request {i+1}: {duration:.2f}s (HTTP {status})")

    print(f"\nSequential Results:")
    print(f"Mean response time: {mean(times):.2f}s")
    print(f"Median response time: {median(times):.2f}s")
    print(f"Min response time: {min(times):.2f}s")
    print(f"Max response time: {max(times):.2f}s")

if __name__ == "__main__":
    test_chat_performance()
```

---

## API Changelog

### Version 1.0.0 (Current)
- ✅ Basic CRUD operations for conversations
- ✅ Chat messaging with Ollama integration
- ✅ Full-text search functionality
- ✅ Configuration access endpoint
- ✅ Model listing and selection

### Planned Features (v1.1.0)
- 🔄 WebSocket support for streaming responses
- 🔐 Authentication and authorization
- 📊 Usage analytics and metrics
- 📁 File upload and processing
- 🎛️ Runtime configuration updates

---

## Support and Contributing

**API Issues:** Report API bugs and feature requests on [GitHub Issues](https://github.com/ukkit/chat-o-llama/issues)

**API Contributions:** Submit pull requests for API improvements

**Documentation:** Help improve this API documentation

**Testing:** Share your API integration examples and test cases

---

*This API documentation is for chat-o-llama v1.0.0. For the latest updates, check the [GitHub repository](https://github.com/ukkit/chat-o-llama).*
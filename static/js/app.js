/**
 * Enhanced Chat Application with Markdown Support
 * Ollama Chat Frontend with History Storage
 */

// Global variables
let currentConversationId = null;
let availableModels = [];
let isLoading = false;
let messageStartTime = null;

// Initialize marked with options
function initializeMarked() {
    marked.setOptions({
        highlight: function(code, lang) {
            if (lang && hljs.getLanguage(lang)) {
                try {
                    return hljs.highlight(code, { language: lang }).value;
                } catch (err) {}
            }
            try {
                return hljs.highlightAuto(code).value;
            } catch (err) {
                return code;
            }
        },
        breaks: true,
        gfm: true
    });

    // Custom renderer for code blocks with copy buttons
    const renderer = new marked.Renderer();
    renderer.code = function(code, infostring, escaped) {
		const lang = (infostring || '').match(/\S*/)[0];
		const highlightedCode = this.options.highlight ?
			this.options.highlight(code, lang) :
			escapeHtml(code);

		const langDisplay = lang ? lang : 'text';
		const codeId = 'code-' + Math.random().toString(36).substr(2, 9);

		// Remove all unnecessary whitespace and newlines from the template
		return `<pre><div class="code-block-header"><span class="code-language">${langDisplay}</span><button class="code-copy-btn" onclick="copyCodeBlock('${codeId}')" title="Copy code">📋 Copy</button></div><code id="${codeId}" class="hljs ${lang || ''}">${highlightedCode}</code></pre>`;
	};

    marked.use({ renderer });
}

// Initialize the app
async function init() {
    console.log('Initializing chat-o-llama...');

    // Initialize markdown parser
    initializeMarked();

    // Show loading state
    const modelSelect = document.getElementById('modelSelect');
    modelSelect.innerHTML = '<option value="">Loading models...</option>';

    await loadModels();
    await loadConversations();

    console.log('Initialization complete');
}

// Load available models
async function loadModels() {
    try {
        const response = await fetch('/api/models');

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        availableModels = data.models || [];

        const modelSelect = document.getElementById('modelSelect');
        modelSelect.innerHTML = '';

        if (availableModels.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No models available';
            option.disabled = true;
            modelSelect.appendChild(option);

            console.warn('No Ollama models found. Make sure Ollama is running and has models installed.');
        } else {
            // Add default option
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = 'Select a model...';
            defaultOption.disabled = true;
            modelSelect.appendChild(defaultOption);

            // Add available models
            availableModels.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelect.appendChild(option);
            });

            // Auto-select first model if available
            if (availableModels.length > 0) {
                modelSelect.selectedIndex = 1; // Skip the "Select a model..." option
            }

            console.log(`Loaded ${availableModels.length} models:`, availableModels);
        }
    } catch (error) {
        console.error('Error loading models:', error);

        const modelSelect = document.getElementById('modelSelect');
        modelSelect.innerHTML = '';

        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Error loading models';
        option.disabled = true;
        modelSelect.appendChild(option);

        // Show user-friendly error
        setTimeout(() => {
            showErrorNotification(
                'Cannot load models',
                'Make sure Ollama is running and has models installed.'
            );
        }, 100);
    }
}

// Show error notification
function showErrorNotification(title, message) {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed; top: 20px; right: 20px;
        background: #da3633; color: white;
        padding: 12px 16px; border-radius: 6px;
        font-family: inherit; font-size: 13px;
        z-index: 1000; max-width: 300px;
    `;
    errorDiv.innerHTML = `
        <strong>${title}</strong><br>
        ${message}<br>
        <small>Check console for details.</small>
    `;
    document.body.appendChild(errorDiv);

    setTimeout(() => errorDiv.remove(), 5000);
}

// Load conversations
async function loadConversations() {
    try {
        const response = await fetch('/api/conversations');
        const data = await response.json();

        const conversationsList = document.getElementById('conversationsList');
        conversationsList.innerHTML = '';

        data.conversations.forEach(conv => {
            const div = document.createElement('div');
            div.className = 'conversation-item';
            div.onclick = () => loadConversation(conv.id);

            const date = new Date(conv.updated_at).toLocaleDateString();

            div.innerHTML = `
                <div class="conversation-title" data-conv-id="${conv.id}" onclick="event.stopPropagation();" ondblclick="startRename(${conv.id})">${escapeHtml(conv.title)}</div>
                <div class="conversation-meta">${conv.model} • ${date}</div>
                <div class="conversation-actions">
                    <button class="conversation-edit" onclick="event.stopPropagation(); startRename(${conv.id})" title="Rename">✏</button>
                    <button class="conversation-delete" onclick="event.stopPropagation(); deleteConversation(${conv.id})" title="Delete">×</button>
                </div>
            `;

            conversationsList.appendChild(div);
        });
    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}

// Create new chat
async function createNewChat() {
    const selectedModel = document.getElementById('modelSelect').value;
    if (!selectedModel) {
        alert('Please select a model first');
        return;
    }

    try {
        const response = await fetch('/api/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: 'New Chat',
                model: selectedModel
            })
        });

        const data = await response.json();
        await loadConversations();
        loadConversation(data.conversation_id);
    } catch (error) {
        console.error('Error creating conversation:', error);
    }
}

// Load conversation
async function loadConversation(conversationId) {
    try {
        const response = await fetch(`/api/conversations/${conversationId}`);
        const data = await response.json();

        currentConversationId = conversationId;

        // Update UI
        document.getElementById('chatTitle').textContent = data.conversation.title;
        document.getElementById('inputContainer').style.display = 'flex';

        // Restore the model selection for this conversation
        const modelSelect = document.getElementById('modelSelect');
        if (data.conversation.model && modelSelect) {
            modelSelect.value = data.conversation.model;
        }

        // Update active conversation
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[onclick*="${conversationId}"]`)?.classList.add('active');

        // Load messages
        const chatContainer = document.getElementById('chatContainer');
        chatContainer.innerHTML = '';

        data.messages.forEach(message => {
            addMessageToChat(message.role, message.content, message.model, message.timestamp,
                message.response_time_ms, message.estimated_tokens);
        });

        // Focus input
        document.getElementById('messageInput').focus();

    } catch (error) {
        console.error('Error loading conversation:', error);
    }
}

// Start renaming a conversation
function startRename(conversationId) {
    const titleElement = document.querySelector(`[data-conv-id="${conversationId}"]`);
    if (!titleElement || titleElement.querySelector('input')) return; // Already editing

    const currentTitle = titleElement.textContent;

    // Create input element
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'conversation-title-input';
    input.value = currentTitle;
    input.maxLength = 100;

    // Handle save/cancel
    const saveRename = async () => {
        const newTitle = input.value.trim();
        if (!newTitle) {
            cancelRename();
            return;
        }

        if (newTitle === currentTitle) {
            cancelRename();
            return;
        }

        try {
            const response = await fetch(`/api/conversations/${conversationId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            });

            if (response.ok) {
                // Remove input first, then set text content
                if (input.parentNode === titleElement) {
                    titleElement.removeChild(input);
                }
                titleElement.textContent = newTitle;

                // Update chat title if this is the current conversation
                if (currentConversationId === conversationId) {
                    document.getElementById('chatTitle').textContent = newTitle;
                }

                // Reload conversations to update order
                await loadConversations();
            } else {
                const error = await response.json();
                alert(error.error || 'Failed to rename conversation');
                cancelRename();
            }
        } catch (error) {
            console.error('Error renaming conversation:', error);
            alert('Failed to rename conversation');
            cancelRename();
        }
    };

    const cancelRename = () => {
        // Remove input first, then set text content
        if (input.parentNode === titleElement) {
            titleElement.removeChild(input);
        }
        titleElement.textContent = currentTitle;
    };

    // Event handlers
    input.onblur = saveRename;
    input.onkeydown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveRename();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelRename();
        }
    };

    // Replace title with input
    titleElement.textContent = '';
    titleElement.appendChild(input);
    input.focus();
    input.select();
}

// Copy code block content
async function copyCodeBlock(codeId) {
    try {
        const codeElement = document.getElementById(codeId);
        if (!codeElement) return;

        // Get the raw text content without HTML formatting
        let codeText = codeElement.textContent || codeElement.innerText || '';

        // Clean up any extra whitespace that might have been added during highlighting
        codeText = codeText.trim();

        if (!codeText) {
            throw new Error('No code content found to copy');
        }

        // Copy to clipboard
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(codeText);
            showCodeCopySuccess(codeId);
        } else {
            // Fallback for older browsers
            const success = copyTextFallback(codeText);
            if (success) {
                showCodeCopySuccess(codeId);
            } else {
                showCodeCopyError(codeId);
            }
        }

    } catch (err) {
        console.error('Code copy failed:', err);
        showCodeCopyError(codeId);
    }
}

// Show code copy success
function showCodeCopySuccess(codeId) {
    const button = document.querySelector(`button[onclick*="${codeId}"]`);
    if (button) {
        const originalText = button.textContent;
        button.textContent = '✓ Copied';
        button.classList.add('copied');
        showCopyNotification();

        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('copied');
        }, 2000);
    }
}

// Show code copy error
function showCodeCopyError(codeId) {
    const button = document.querySelector(`button[onclick*="${codeId}"]`);
    if (button) {
        const originalText = button.textContent;
        button.textContent = '❌ Failed';
        button.style.color = '#da3633';

        setTimeout(() => {
            button.textContent = originalText;
            button.style.color = '';
        }, 2000);
    }
}

// Copy message content to clipboard
async function copyMessage(button) {
    try {
        // Get the message content from the parent message div
        const messageContent = button.closest('.message-content');

        // Create a temporary div to extract text without markdown formatting
        const tempDiv = document.createElement('div');

        // Clone the message content but exclude meta, stats, and copy button
        const clonedContent = messageContent.cloneNode(true);

        // Remove meta, stats, and copy button
        const metaDiv = clonedContent.querySelector('.message-meta');
        const statsDiv = clonedContent.querySelector('.message-stats');
        const copyBtn = clonedContent.querySelector('.copy-btn');
        const codeHeaders = clonedContent.querySelectorAll('.code-block-header');

        if (metaDiv) metaDiv.remove();
        if (statsDiv) statsDiv.remove();
        if (copyBtn) copyBtn.remove();
        // Remove code block headers to get clean code
        codeHeaders.forEach(header => header.remove());

        tempDiv.appendChild(clonedContent);

        // Get text content
        let textContent = tempDiv.textContent || tempDiv.innerText || '';
        textContent = textContent.trim();

        if (!textContent) {
            throw new Error('No text content found to copy');
        }

        // Copy to clipboard
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(textContent);
            showCopySuccess(button);
        } else {
            // Fallback for older browsers
            const success = copyTextFallback(textContent);
            if (success) {
                showCopySuccess(button);
            } else {
                showCopyError(button);
            }
        }

    } catch (err) {
        console.error('Copy failed:', err);
        showCopyError(button);
    }
}

// Fallback copy method for older browsers or non-HTTPS
function copyTextFallback(text) {
    try {
        const textArea = document.createElement('textarea');
        textArea.value = text;

        // Style the textarea to be invisible but functional
        textArea.style.position = 'fixed';
        textArea.style.top = '0';
        textArea.style.left = '0';
        textArea.style.width = '2em';
        textArea.style.height = '2em';
        textArea.style.padding = '0';
        textArea.style.border = 'none';
        textArea.style.outline = 'none';
        textArea.style.boxShadow = 'none';
        textArea.style.background = 'transparent';
        textArea.style.opacity = '0';
        textArea.setAttribute('readonly', '');

        document.body.appendChild(textArea);

        // Focus and select
        textArea.focus();
        textArea.setSelectionRange(0, textArea.value.length);
        textArea.select();

        // Try to copy
        const successful = document.execCommand('copy');

        // Clean up
        document.body.removeChild(textArea);

        return successful;

    } catch (err) {
        console.error('Fallback copy error:', err);
        return false;
    }
}

// Show copy success feedback
function showCopySuccess(button) {
    button.textContent = '✓';
    button.classList.add('copied');
    showCopyNotification();

    setTimeout(() => {
        button.textContent = '📋';
        button.classList.remove('copied');
    }, 2000);
}

// Show copy error feedback
function showCopyError(button) {
    button.textContent = '❌';
    button.style.color = '#da3633';

    // Show error notification instead of success
    const notification = document.getElementById('copyNotification');
    notification.textContent = 'Copy failed!';
    notification.style.backgroundColor = '#da3633';
    notification.classList.add('show');

    setTimeout(() => {
        button.textContent = '📋';
        button.style.color = '';
        notification.classList.remove('show');
        // Reset notification
        setTimeout(() => {
            notification.textContent = 'Copied to clipboard!';
            notification.style.backgroundColor = '#238636';
        }, 300);
    }, 2000);
}

// Show copy notification
function showCopyNotification() {
    const notification = document.getElementById('copyNotification');
    notification.classList.add('show');
    setTimeout(() => {
        notification.classList.remove('show');
    }, 2000);
}

// Calculate tokens (rough estimation)
function estimateTokens(text) {
    // Rough estimation: ~4 characters per token for English text
    return Math.ceil(text.length / 4);
}

// Send message
async function sendMessage() {
    if (isLoading || !currentConversationId) return;

    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    const selectedModel = document.getElementById('modelSelect').value;

    if (!message) return;

    // Record start time for performance measurement
    messageStartTime = Date.now();

    // Add user message to chat
    addMessageToChat('user', message);
    messageInput.value = '';
    autoResize(messageInput);

    // Show loading
    isLoading = true;
    document.getElementById('sendBtn').disabled = true;
    document.getElementById('sendBtn').textContent = 'Thinking...';

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading';
    loadingDiv.textContent = 'Thinking...';
    document.getElementById('chatContainer').appendChild(loadingDiv);
    scrollToBottom();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                conversation_id: currentConversationId,
                message: message,
                model: selectedModel
            })
        });

        const data = await response.json();

        // Calculate response time
        const responseTime = messageStartTime ? Date.now() - messageStartTime : 0;
        const estimatedTokens = estimateTokens(data.response);

        // Remove loading
        loadingDiv.remove();

        // Add assistant response with stats
        addMessageToChat('assistant', data.response, data.model, null, responseTime, estimatedTokens);

        // Reload conversations to update timestamp
        await loadConversations();

    } catch (error) {
        loadingDiv.remove();
        addMessageToChat('assistant', 'Error: Could not get response from Ollama');
    } finally {
        isLoading = false;
        document.getElementById('sendBtn').disabled = false;
        document.getElementById('sendBtn').textContent = 'Send';
        messageInput.focus();
        messageStartTime = null;
    }
}

// Add message to chat with markdown support
function addMessageToChat(role, content, model = null, timestamp = null, responseTime = null, tokens = null) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const time = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    const modelInfo = model && role === 'assistant' ? ` • ${model}` : '';

    // Build stats string
    let statsString = '';
    if (role === 'assistant' && (responseTime || tokens)) {
        const stats = [];
        if (responseTime) {
            stats.push(`${(responseTime / 1000).toFixed(1)}s`);
        }
        if (tokens) {
            stats.push(`~${tokens} tokens`);
            if (responseTime) {
                const tokensPerSecond = (tokens / (responseTime / 1000)).toFixed(1);
                stats.push(`${tokensPerSecond} tok/s`);
            }
        }
        if (stats.length > 0) {
            statsString = `<div class="message-stats">${stats.join(' • ')}</div>`;
        }
    }

    // Parse markdown for assistant messages, escape HTML for user messages
    let contentHtml;
    if (role === 'assistant') {
        try {
            contentHtml = marked.parse(content);
        } catch (error) {
            console.error('Markdown parsing error:', error);
            contentHtml = escapeHtml(content).replace(/\n/g, '<br>');
        }
    } else {
        contentHtml = escapeHtml(content).replace(/\n/g, '<br>');
    }

    messageDiv.innerHTML = `
        <div class="message-content">
            ${contentHtml}
            <div class="message-meta">${time}${modelInfo}</div>
            ${statsString}
            <button class="copy-btn" onclick="copyMessage(this)" title="Copy message">📋</button>
        </div>
    `;

    chatContainer.appendChild(messageDiv);

    // Apply syntax highlighting to any new code blocks
    messageDiv.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });

    scrollToBottom();
}

// Delete conversation
async function deleteConversation(conversationId) {
    if (!confirm('Delete this conversation?')) return;

    try {
        await fetch(`/api/conversations/${conversationId}`, {
            method: 'DELETE'
        });

        if (currentConversationId === conversationId) {
            currentConversationId = null;
            document.getElementById('chatContainer').innerHTML = `
                <div class="no-conversation">
                    <h2>Welcome to chat-o-llama</h2>
                    <p>Create a new chat to get started</p>
                </div>
            `;
            document.getElementById('inputContainer').style.display = 'none';
            document.getElementById('chatTitle').textContent = 'Select a conversation';
        }

        await loadConversations();
    } catch (error) {
        console.error('Error deleting conversation:', error);
    }
}

// Search conversations
async function searchConversations(event) {
    const query = event.target.value.trim();
    const resultsDiv = document.getElementById('searchResults');

    if (query.length < 2) {
        resultsDiv.style.display = 'none';
        return;
    }

    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        resultsDiv.innerHTML = '';

        if (data.results.length === 0) {
            resultsDiv.innerHTML = '<div class="search-result">No results found</div>';
        } else {
            data.results.forEach(result => {
                const div = document.createElement('div');
                div.className = 'search-result';
                div.onclick = () => {
                    loadConversation(result.id);
                    resultsDiv.style.display = 'none';
                    event.target.value = '';
                };

                const preview = result.content.length > 100 ?
                    result.content.substring(0, 100) + '...' : result.content;

                div.innerHTML = `
                    <div class="search-result-title">${escapeHtml(result.title)}</div>
                    <div class="search-result-content">${escapeHtml(preview)}</div>
                `;

                resultsDiv.appendChild(div);
            });
        }

        resultsDiv.style.display = 'block';
    } catch (error) {
        console.error('Error searching:', error);
    }
}

// Handle key events
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Auto-resize textarea
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

// Scroll to bottom
function scrollToBottom() {
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Hide search results when clicking outside
    document.addEventListener('click', function(event) {
        const searchBox = document.getElementById('searchBox');
        const searchResults = document.getElementById('searchResults');

        if (!searchBox.contains(event.target) && !searchResults.contains(event.target)) {
            searchResults.style.display = 'none';
        }
    });
});

// Initialize app when page loads
window.addEventListener('load', init);
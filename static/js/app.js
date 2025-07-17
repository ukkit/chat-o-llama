/**
 * Enhanced Chat Application with Markdown Support
 * Ollama Chat Frontend with History Storage
 */

// Global variables
let currentConversationId = null;
let availableModels = [];
let isLoading = false;
let messageStartTime = null;
let mcpStatus = null;
let mcpServers = {};
let mcpTools = [];
let loadingTextInterval = null;
let backendStatus = null;
let availableBackends = [];
let currentAbortController = null;
let lastRequestTime = 0;
let requestCooldown = 500; // 500ms cooldown between requests

// User preferences for cancellation behavior
let cancellationPreferences = {
    timeoutDuration: 30000, // 30 seconds default (will be overridden by config)
    showTimeoutWarning: true,
    autoCancel: false,
    confirmNavigation: true
};

// Load timeout from server config based on active backend
async function loadTimeoutFromConfig() {
    try {
        // Get the active backend type first
        const backendResponse = await fetch('/api/backend/status');
        const configResponse = await fetch('/api/config');
        
        if (backendResponse.ok && configResponse.ok) {
            const backendStatus = await backendResponse.json();
            const config = await configResponse.json();
            
            const activeBackend = backendStatus.active_backend;
            
            // Use appropriate timeout based on active backend
            let timeoutSeconds = 600; // Default 10 minutes
            
            if (activeBackend === 'ollama' && config.timeouts && config.timeouts.ollama_timeout) {
                timeoutSeconds = config.timeouts.ollama_timeout;
            } else if (activeBackend === 'llamacpp' && config.timeouts && config.timeouts.ollama_timeout) {
                // For now, llama.cpp uses the same timeout config as Ollama
                timeoutSeconds = config.timeouts.ollama_timeout;
            }
            
            // Convert seconds to milliseconds
            cancellationPreferences.timeoutDuration = timeoutSeconds * 1000;
        }
    } catch (error) {
        console.warn('Error loading timeout from config:', error);
    }
}

// Load user preferences from localStorage
function loadCancellationPreferences() {
    try {
        const saved = localStorage.getItem('chatollama_cancellation_preferences');
        if (saved) {
            const parsed = JSON.parse(saved);
            cancellationPreferences = { ...cancellationPreferences, ...parsed };
        }
    } catch (error) {
        console.warn('Error loading cancellation preferences:', error);
    }
}

// Save user preferences to localStorage
function saveCancellationPreferences() {
    try {
        localStorage.setItem('chatollama_cancellation_preferences', JSON.stringify(cancellationPreferences));
    } catch (error) {
        console.warn('Error saving cancellation preferences:', error);
    }
}

// Update specific preference
function updateCancellationPreference(key, value) {
    cancellationPreferences[key] = value;
    saveCancellationPreferences();
}

// Thinking synonyms for variety in loading messages
const thinkingSynonyms = [
    "Thinking", "Processing", "Analyzing", "Computing",
    "Pondering", "Reflecting", "Reasoning", "Generating",
    "Contemplating", "Considering", "Working", "Calculating",
    "Reasoning", "Analyzing", "Evaluating", "Deliberating",
    "Ruminating", "Brainstorming", "Introspecting"
];

// Get random thinking synonym
function getRandomThinkingText() {
    return thinkingSynonyms[Math.floor(Math.random() * thinkingSynonyms.length)];
}

// Generate interesting chat names
const chatNamePrefixes = [
    "Creative", "Brilliant", "Curious", "Insightful", "Clever", "Wise", "Deep", "Quick",
    "Smart", "Sharp", "Bright", "Epic", "Dynamic", "Fresh", "Bold", "Witty", "Eager",
    "Confident", "Courageous", "Determined", "Fearless", "Ambitious", "Driven", "Resilient",
    "Tenacious", "Proactive", "Energetic", "Enterprising", "Wise", "Curious", "Insightful",
    "Gracious", "Visionary", "Influential", "Skilled", "Talented", "Magnetic", "Legendary", "Limitless"
];

const chatNameSuffixes = [
    "Discussion", "Conversation", "Chat", "Dialogue", "Exchange", "Talk", "Session",
    "Brainstorm", "Journey", "Quest", "Adventure", "Exploration", "Discovery"
];

function generateChatName() {
    const prefix = chatNamePrefixes[Math.floor(Math.random() * chatNamePrefixes.length)];
    const suffix = chatNameSuffixes[Math.floor(Math.random() * chatNameSuffixes.length)];
    return `${prefix} ${suffix}`;
}

// Get backend indicator badge
function getBackendIndicator(backendType) {
    switch (backendType) {
        case 'ollama':
            return '<span class="backend-badge backend-ollama" title="Ollama Backend">O</span>';
        case 'llamacpp':
            return '<span class="backend-badge backend-llamacpp" title="Llama.cpp Backend">L</span>';
        default:
            return '<span class="backend-badge backend-unknown" title="Unknown Backend">?</span>';
    }
}

// Create animated loading element
function createAnimatedLoading() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading';

    const spinner = document.createElement('span');
    spinner.className = 'loading-spinner';

    const textSpan = document.createElement('span');
    textSpan.className = 'loading-text';
    textSpan.textContent = getRandomThinkingText() + '...';

    loadingDiv.appendChild(spinner);
    loadingDiv.appendChild(textSpan);

    return { loadingDiv, textSpan };
}

// Update loading text with synonyms
function startLoadingTextRotation(textElement) {
    // Clear any existing interval
    if (loadingTextInterval) {
        clearInterval(loadingTextInterval);
    }

    // Update text every 3 seconds
    loadingTextInterval = setInterval(() => {
        if (textElement && textElement.parentNode) {
            textElement.textContent = getRandomThinkingText() + '...';
        } else {
            // Element no longer exists, clear interval
            clearInterval(loadingTextInterval);
            loadingTextInterval = null;
        }
    }, 3000);
}

// Stop loading text rotation
function stopLoadingTextRotation() {
    if (loadingTextInterval) {
        clearInterval(loadingTextInterval);
        loadingTextInterval = null;
    }
}

// Update send button text with synonyms
function startSendButtonRotation() {
    const sendBtn = document.getElementById('sendBtn');
    const updateButtonText = () => {
        if (isLoading && sendBtn) {
            sendBtn.textContent = getRandomThinkingText() + '...';
        }
    };

    // Update button text every 3 seconds
    const buttonInterval = setInterval(() => {
        if (isLoading) {
            updateButtonText();
        } else {
            clearInterval(buttonInterval);
        }
    }, 3000);
}

// Initialize marked with options
function initializeMarked() {
    // Configure marked with new v5+ syntax (no deprecated options)
    marked.setOptions({
        breaks: true,
        gfm: true,
        mangle: false,     // Disable deprecated mangle option
        headerIds: false   // Disable deprecated headerIds option
    });

    // Custom renderer for code blocks with copy buttons
    const renderer = new marked.Renderer();
    renderer.code = function(code, infostring, escaped) {
        const lang = (infostring || '').match(/\S*/)[0];

        // Handle syntax highlighting manually since highlight option is deprecated
        let highlightedCode;
        if (lang && hljs.getLanguage(lang)) {
            try {
                highlightedCode = hljs.highlight(code, { language: lang }).value;
            } catch (err) {
                highlightedCode = escapeHtml(code);
            }
        } else {
            try {
                highlightedCode = hljs.highlightAuto(code).value;
            } catch (err) {
                highlightedCode = escapeHtml(code);
            }
        }

        const langDisplay = lang ? lang : 'text';
        const codeId = 'code-' + Math.random().toString(36).substr(2, 9);

        return `<pre><div class="code-block-header"><span class="code-language">${langDisplay}</span><button class="code-copy-btn" onclick="copyCodeBlock('${codeId}')" title="Copy code">📋 Copy</button></div><code id="${codeId}" class="hljs ${lang || ''}">${highlightedCode}</code></pre>`;
    };

    marked.use({ renderer });
}

// Process thinking tags in content
function processThinkingTags(content) {
    // Handle both single-line and multi-line thinking tags
    const thinkRegex = /<think>([\s\S]*?)<\/think>/gi;

    return content.replace(thinkRegex, function(match, thinkingContent) {
        // Clean up the thinking content - remove extra whitespace but preserve line breaks
        const cleanedContent = thinkingContent.trim();

        // Convert the thinking content to HTML with proper styling
        // Process any markdown within the thinking content
        let processedThinking;
        try {
            processedThinking = marked.parseInline(cleanedContent);
        } catch (error) {
            // Fallback to escaped HTML if markdown processing fails
            processedThinking = escapeHtml(cleanedContent).replace(/\n/g, '<br>');
        }

        return `<div class="thinking-content" data-thinking="true">${processedThinking}</div>`;
    });
}

// Initialize the app
async function init() {
    console.log('Initializing chat-o-llama...');

    // Load user preferences
    loadCancellationPreferences();

    // Initialize markdown parser
    initializeMarked();

    // Show loading state
    const modelSelect = document.getElementById('modelSelect');
    modelSelect.innerHTML = '<option value="">Loading models...</option>';

    await loadBackendStatus();
    await loadTimeoutFromConfig(); // Load timeout from config based on active backend
    await loadModels();
    await loadConversations();
    await loadMCPStatus();

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

            console.warn('No models found for the current backend. Make sure the backend is properly configured and has models available.');
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

// Load backend status and available backends
async function loadBackendStatus() {
    try {
        const response = await fetch('/api/backend/status');

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        backendStatus = data;

        // Extract available backends
        availableBackends = Object.keys(data.backends || {});

        updateBackendUI();
        console.log('Backend status loaded:', data);

    } catch (error) {
        console.error('Error loading backend status:', error);
        updateBackendUI(true);
    }
}

// Update backend UI elements
function updateBackendUI(hasError = false) {
    const backendIndicator = document.getElementById('backendIndicator');
    const backendText = document.getElementById('backendText');
    const backendOptions = document.getElementById('backendOptions');

    if (hasError || !backendStatus) {
        backendIndicator.textContent = '❌';
        backendIndicator.className = 'backend-indicator unhealthy';
        backendText.textContent = 'Backend Error';

        backendOptions.innerHTML = '<div class="backend-option disabled">Error loading backends</div>';
        return;
    }

    // Update current backend display
    const activeBackend = backendStatus.active_backend;
    const backends = backendStatus.backends || {};

    if (activeBackend && backends[activeBackend]) {
        const backend = backends[activeBackend];
        const backendInfo = backend.backend_info || {};

        if (backend.status === 'healthy' || backendInfo.status === 'available') {
            backendIndicator.textContent = '✅';
            backendIndicator.className = 'backend-indicator healthy';
            const modelsAvailable = backendInfo.models_available ? 'available' : 'no models';
            backendText.textContent = `${activeBackend} (${modelsAvailable})`;
        } else {
            backendIndicator.textContent = '⚠️';
            backendIndicator.className = 'backend-indicator unhealthy';
            backendText.textContent = `${activeBackend} (${backend.status})`;
        }
    } else {
        backendIndicator.textContent = '❓';
        backendIndicator.className = 'backend-indicator unhealthy';
        backendText.textContent = 'No active backend';
    }

    // Update backend options dropdown
    backendOptions.innerHTML = '';

    if (availableBackends.length === 0) {
        backendOptions.innerHTML = '<div class="backend-option disabled">No backends available</div>';
    } else {
        // Add available backends
        availableBackends.forEach(backendType => {
            const backend = backends[backendType];
            const backendInfo = backend ? backend.backend_info || {} : {};

            const optionDiv = document.createElement('div');
            optionDiv.className = `backend-option ${backendType === activeBackend ? 'current' : ''}`;
            optionDiv.onclick = () => selectBackend(backendType);

            let statusIndicator = '❓';
            let statusText = backend ? backend.status : 'unknown';
            let modelsText = backendInfo.models_available ? 'models available' : 'no models';

            if (backend) {
                if (backend.status === 'healthy' || backendInfo.status === 'available') {
                    statusIndicator = '✅';
                } else {
                    statusIndicator = '⚠️';
                }
            }

            optionDiv.innerHTML = `
                <span class="backend-indicator">${statusIndicator}</span>
                <div class="backend-details">
                    <div class="backend-name">${backendType}</div>
                    <div class="backend-status-text">${statusText}, ${modelsText}</div>
                </div>
            `;

            backendOptions.appendChild(optionDiv);
        });
    }
}

// Toggle backend dropdown visibility
function toggleBackendDropdown() {
    const container = document.querySelector('.backend-dropdown-container');
    container.classList.toggle('open');

    // Close dropdown when clicking outside
    if (container.classList.contains('open')) {
        document.addEventListener('click', closeBackendDropdownOutside);
    } else {
        document.removeEventListener('click', closeBackendDropdownOutside);
    }
}

// Close dropdown when clicking outside
function closeBackendDropdownOutside(event) {
    const container = document.querySelector('.backend-dropdown-container');
    if (!container.contains(event.target)) {
        container.classList.remove('open');
        document.removeEventListener('click', closeBackendDropdownOutside);
    }
}

// Select a backend from the dropdown
async function selectBackend(selectedBackend) {
    if (!selectedBackend || selectedBackend === backendStatus?.active_backend) {
        toggleBackendDropdown();
        return;
    }

    // Handle cancellation if request is in progress
    if (isLoading && currentAbortController) {
        showCancellationNotification('Cancelling current request before switching backend...', 'warning');
        try {
            currentAbortController.abort();
            cleanup();
        } catch (error) {
            console.error('Error cancelling request during backend switch:', error);
        }
    }

    // Close dropdown immediately
    const container = document.querySelector('.backend-dropdown-container');
    container.classList.remove('open');
    document.removeEventListener('click', closeBackendDropdownOutside);

    try {
        // Show loading state
        const backendIndicator = document.getElementById('backendIndicator');
        const backendText = document.getElementById('backendText');

        backendIndicator.textContent = '🔄';
        backendIndicator.className = 'backend-indicator loading';
        backendText.textContent = 'Switching backend...';

        const response = await fetch('/api/backend/switch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ backend_type: selectedBackend })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Backend switched successfully:', data);

        // Refresh backend status, timeout, and models
        await loadBackendStatus();
        await loadTimeoutFromConfig(); // Refresh timeout for the new backend
        await loadModels();

        // Show success notification with model count info
        const modelCount = availableModels.length;
        let message = `Switched to ${selectedBackend} backend`;
        if (modelCount === 0) {
            message += ` (No models available)`;
        } else {
            message += ` (${modelCount} model${modelCount === 1 ? '' : 's'} available)`;
        }
        showBackendSwitchNotification(message);

    } catch (error) {
        console.error('Error switching backend:', error);

        // Restore previous backend display
        updateBackendUI();

        showErrorNotification(
            'Backend Switch Failed',
            error.message || 'Could not switch to the selected backend'
        );
    }
}

// Refresh backend status
async function refreshBackendStatus() {
    const refreshButton = document.getElementById('backendRefresh');

    // Add rotation animation
    refreshButton.style.animation = 'spin 1s linear';
    refreshButton.disabled = true;

    try {
        await loadBackendStatus();
        await loadModels(); // Refresh models as well

        console.log('Backend status refreshed');

        // Close dropdown after refresh
        const container = document.querySelector('.backend-dropdown-container');
        container.classList.remove('open');
        document.removeEventListener('click', closeBackendDropdownOutside);

    } catch (error) {
        console.error('Error refreshing backend status:', error);
    } finally {
        // Remove animation and re-enable button
        setTimeout(() => {
            refreshButton.style.animation = '';
            refreshButton.disabled = false;
        }, 1000);
    }
}

// Show backend switch notification
function showBackendSwitchNotification(message, type = 'success') {
    const notification = document.createElement('div');
    
    // Determine notification color based on type or message content
    let backgroundColor;
    if (type === 'warning' || message.includes('⚠️') || message.includes('No models available')) {
        backgroundColor = '#d1a827'; // Warning yellow
    } else if (type === 'error' || message.includes('❌') || message.includes('failed')) {
        backgroundColor = '#da3633'; // Error red
    } else {
        backgroundColor = '#238636'; // Success green
    }

    notification.style.cssText = `
        position: fixed; top: 20px; right: 20px;
        background: ${backgroundColor}; color: white;
        padding: 12px 16px; border-radius: 6px;
        font-family: inherit; font-size: 13px;
        z-index: 1000; max-width: 350px;
        opacity: 0; transition: opacity 0.3s ease;
        word-wrap: break-word;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    // Show notification
    setTimeout(() => notification.style.opacity = '1', 100);

    // Remove after 4 seconds for warnings/errors, 3 seconds for success
    const duration = (type === 'warning' || type === 'error') ? 4000 : 3000;
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, duration);
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
            div.id = `conversation-${conv.id}`;
            div.onclick = () => loadConversation(conv.id);

            const date = new Date(conv.updated_at).toLocaleDateString();
            const backendType = conv.backend_type || 'ollama';
            
            // Create backend indicator
            const backendIndicator = getBackendIndicator(backendType);
            
            // Add backend-specific class for styling
            div.classList.add(`backend-${backendType}`);

            div.innerHTML = `
                <div class="conversation-title" data-conv-id="${conv.id}" onclick="event.stopPropagation();" ondblclick="startRename(${conv.id})">${escapeHtml(conv.title)}</div>
                <div class="conversation-meta">${backendIndicator} ${conv.model} • ${date}</div>
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

// MCP Related Functions
async function loadMCPStatus() {
    try {
        const response = await fetch('/api/mcp/status');
        if (response.ok) {
            mcpStatus = await response.json();
            await loadMCPServers();
            await loadMCPTools();
            updateMCPUI();
        } else {
            console.log('MCP not available or error loading status');
            mcpStatus = { enabled: false, mcp_available: false };
        }
    } catch (error) {
        console.error('Error loading MCP status:', error);
        mcpStatus = { enabled: false, mcp_available: false };
    }
}

async function loadMCPServers() {
    try {
        const response = await fetch('/api/mcp/servers');
        if (response.ok) {
            const data = await response.json();
            mcpServers = data.servers || {};
        }
    } catch (error) {
        console.error('Error loading MCP servers:', error);
    }
}

async function loadMCPTools() {
    try {
        const response = await fetch('/api/mcp/tools');
        if (response.ok) {
            const data = await response.json();
            mcpTools = data.tools || [];
        }
    } catch (error) {
        console.error('Error loading MCP tools:', error);
    }
}

function updateMCPUI() {
    // Add MCP status indicator to the sidebar
    const sidebar = document.querySelector('.sidebar-header');

    // Remove existing MCP status if present
    const existingStatus = document.getElementById('mcpStatus');
    if (existingStatus) {
        existingStatus.remove();
    }

    if (mcpStatus && mcpStatus.mcp_available && mcpStatus.enabled) {
        const mcpStatusDiv = document.createElement('div');
        mcpStatusDiv.id = 'mcpStatus';
        mcpStatusDiv.className = 'mcp-status';

        const enabledServers = Object.values(mcpServers).filter(server => server.status === 'connected').length;
        const totalServers = Object.keys(mcpServers).length;

        mcpStatusDiv.innerHTML = `
            <div class="mcp-indicator ${mcpStatus.enabled ? 'mcp-enabled' : 'mcp-disabled'}">
                <span class="mcp-icon">🔧</span>
                <span class="mcp-text">MCP: ${enabledServers}/${totalServers} servers</span>
                <button class="mcp-toggle" onclick="toggleMCPPanel()" title="Show MCP tools">⚙️</button>
            </div>
        `;

        sidebar.appendChild(mcpStatusDiv);

        // Add MCP tools panel (initially hidden)
        addMCPToolsPanel();
    }
}

function addMCPToolsPanel() {
    // Remove existing panel if present
    const existingPanel = document.getElementById('mcpToolsPanel');
    if (existingPanel) {
        existingPanel.remove();
    }

    const mcpPanel = document.createElement('div');
    mcpPanel.id = 'mcpToolsPanel';
    mcpPanel.className = 'mcp-tools-panel hidden';

    let toolsHTML = '<div class="mcp-panel-header"><h3>Available Tools</h3><button onclick="toggleMCPPanel()">×</button></div>';

    if (mcpTools.length > 0) {
        toolsHTML += '<div class="mcp-tools-list">';
        mcpTools.forEach(tool => {
            toolsHTML += `
                <div class="mcp-tool-item" onclick="insertToolUsage('${tool.name}', '${tool.server_id}')">
                    <div class="mcp-tool-name">${tool.name}</div>
                    <div class="mcp-tool-description">${tool.description || 'No description'}</div>
                    <div class="mcp-tool-server">Server: ${tool.server_name}</div>
                </div>
            `;
        });
        toolsHTML += '</div>';
    } else {
        toolsHTML += '<div class="mcp-no-tools">No tools available</div>';
    }

    mcpPanel.innerHTML = toolsHTML;
    document.body.appendChild(mcpPanel);
}

function toggleMCPPanel() {
    const panel = document.getElementById('mcpToolsPanel');
    if (panel) {
        panel.classList.toggle('hidden');
    }
}

function insertToolUsage(toolName, serverId) {
    const messageInput = document.getElementById('messageInput');
    const currentValue = messageInput.value;
    const toolUsage = `Please use the ${toolName} tool to help with this request.`;

    if (currentValue.trim()) {
        messageInput.value = currentValue + '\n\n' + toolUsage;
    } else {
        messageInput.value = toolUsage;
    }

    messageInput.focus();
    toggleMCPPanel();
}

// Create new chat
async function createNewChat() {
    const selectedModel = document.getElementById('modelSelect').value;
    if (!selectedModel || availableModels.length === 0) {
        alert('Please select a model first. Make sure the current backend has models available.');
        return;
    }

    try {
        const response = await fetch('/api/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: generateChatName(),
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

        // Check if conversation backend matches current active backend
        const conversationBackend = data.conversation.backend_type || 'ollama';
        const currentActiveBackend = backendStatus?.active_backend;
        
        if (conversationBackend !== currentActiveBackend) {
            console.log(`Conversation created with ${conversationBackend}, switching from ${currentActiveBackend}`);
            
            // Try to switch to the conversation's backend
            try {
                await selectBackend(conversationBackend);
                // Wait a moment for backend switch to complete and models to reload
                await new Promise(resolve => setTimeout(resolve, 1000));
            } catch (switchError) {
                console.error('Failed to switch backend for conversation:', switchError);
                // Show warning but continue loading
                showBackendSwitchNotification(
                    `⚠️ Conversation was created with ${conversationBackend} backend, but switching failed. Using ${currentActiveBackend} instead.`
                );
            }
        }

        // Restore the model selection for this conversation
        const modelSelect = document.getElementById('modelSelect');
        if (data.conversation.model && modelSelect) {
            // Check if the model is available in the current model list
            const modelExists = Array.from(modelSelect.options).some(option => option.value === data.conversation.model);
            if (modelExists) {
                modelSelect.value = data.conversation.model;
            } else {
                console.warn(`Model ${data.conversation.model} not available in current backend, keeping current selection`);
                // Show notification about model unavailability
                setTimeout(() => {
                    showBackendSwitchNotification(
                        `⚠️ Model "${data.conversation.model}" not available. Please select an available model.`,
                        'warning'
                    );
                }, 1500);
            }
        }

        // Update active conversation
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
        document.getElementById(`conversation-${conversationId}`)?.classList.add('active');

        // Load messages
        const chatContainer = document.getElementById('chatContainer');
        chatContainer.innerHTML = '';

        data.messages.forEach(message => {
            addMessageToChat(message.role, message.content, message.model, message.timestamp,
                message.response_time_ms, message.estimated_tokens, message.backend_type);
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

// Copy message content to clipboard (excluding thinking content)
async function copyMessage(button) {
    try {
        // Get the message content from the parent message div
        const messageContent = button.closest('.message-content');

        // Create a temporary div to extract text without markdown formatting
        const tempDiv = document.createElement('div');

        // Clone the message content but exclude meta, stats, copy button, and thinking content
        const clonedContent = messageContent.cloneNode(true);

        // Remove meta, stats, copy button, and thinking content
        const metaDiv = clonedContent.querySelector('.message-meta');
        const statsDiv = clonedContent.querySelector('.message-stats');
        const copyBtn = clonedContent.querySelector('.copy-btn');
        const codeHeaders = clonedContent.querySelectorAll('.code-block-header');
        const thinkingContent = clonedContent.querySelectorAll('.thinking-content');

        if (metaDiv) metaDiv.remove();
        if (statsDiv) statsDiv.remove();
        if (copyBtn) copyBtn.remove();
        // Remove code block headers to get clean code
        codeHeaders.forEach(header => header.remove());
        // Remove thinking content from copy
        thinkingContent.forEach(thinking => thinking.remove());

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

// Show cancellation status indicator
function showCancellationStatus(message) {
    // Remove existing status indicator
    const existingStatus = document.getElementById('cancellationStatus');
    if (existingStatus) {
        existingStatus.remove();
    }
    
    const statusDiv = document.createElement('div');
    statusDiv.id = 'cancellationStatus';
    statusDiv.className = 'cancellation-status';
    statusDiv.innerHTML = `
        <span>⏳</span>
        <span>${message}</span>
    `;
    
    // Insert before the input container
    const inputContainer = document.getElementById('inputContainer');
    inputContainer.parentNode.insertBefore(statusDiv, inputContainer);
    
    // Auto-remove after 2 seconds
    setTimeout(() => {
        if (statusDiv.parentNode) {
            statusDiv.remove();
        }
    }, 2000);
}

// Show cancellation notification
function showCancellationNotification(message, type = 'success') {
    const notification = document.createElement('div');
    
    let backgroundColor;
    let icon;
    if (type === 'error') {
        backgroundColor = '#da3633';
        icon = '❌';
    } else {
        backgroundColor = '#238636';
        icon = '✅';
    }
    
    notification.style.cssText = `
        position: fixed; top: 20px; right: 20px;
        background: ${backgroundColor}; color: white;
        padding: 12px 16px; border-radius: 6px;
        font-family: inherit; font-size: 13px;
        z-index: 1000; max-width: 300px;
        opacity: 0; transition: opacity 0.3s ease;
        display: flex; align-items: center; gap: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    `;
    notification.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => notification.style.opacity = '1', 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Calculate tokens (rough estimation)
function estimateTokens(text) {
    // Rough estimation: ~4 characters per token for English text
    return Math.ceil(text.length / 4);
}

// Cancel current request
function cancelMessage() {
    if (!isLoading || !currentAbortController) {
        console.warn('No active request to cancel');
        return;
    }

    try {
        // Show immediate cancellation feedback
        showCancellationStatus('Cancelling request...');
        
        // Abort the current request
        currentAbortController.abort();
        
        // Clean up UI state
        cleanup();
        
        // Show cancellation feedback
        addMessageToChat('system', '🚫 Request cancelled by user', null, null, null, null, null, true);
        
        // Show success notification
        showCancellationNotification('Request cancelled successfully');
        
        console.log('Message request cancelled by user');
    } catch (error) {
        console.error('Error during message cancellation:', error);
        // Force cleanup even if abort fails
        cleanup();
        showCancellationNotification('Cancellation failed - forcing cleanup', 'error');
    }
}

// Clean up request state and UI
function cleanup(isAborted = false) {
    try {
        // Stop loading animations
        stopLoadingTextRotation();
        
        // Remove loading element with smooth animation
        const loadingDiv = document.querySelector('.loading');
        if (loadingDiv && loadingDiv.parentNode) {
            loadingDiv.style.opacity = '0';
            loadingDiv.style.transform = 'translateY(-10px)';
            setTimeout(() => {
                if (loadingDiv.parentNode) {
                    loadingDiv.remove();
                }
            }, 300);
        }
        
        // Reset UI state with smooth transition
        isLoading = false;
        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) {
            // Add a brief transition effect
            sendBtn.style.transform = 'scale(0.95)';
            setTimeout(() => {
                sendBtn.style.transform = 'scale(1)';
                sendBtn.disabled = false;
                sendBtn.textContent = 'Send';
                sendBtn.classList.remove('cancel');
                sendBtn.onclick = sendMessage;
            }, 150);
        }
        
        // Clear abort controller
        currentAbortController = null;
        
        // Reset message start time
        messageStartTime = null;
        
        // Remove cancellation status if present
        const cancellationStatus = document.getElementById('cancellationStatus');
        if (cancellationStatus) {
            cancellationStatus.style.opacity = '0';
            setTimeout(() => {
                if (cancellationStatus.parentNode) {
                    cancellationStatus.remove();
                }
            }, 300);
        }
        
        // Focus input (only if it exists and is visible)
        const messageInput = document.getElementById('messageInput');
        if (messageInput && messageInput.offsetParent !== null) {
            try {
                // Small delay to ensure smooth transition
                setTimeout(() => {
                    messageInput.focus();
                }, 200);
            } catch (focusError) {
                console.warn('Could not focus input:', focusError);
            }
        }
    } catch (error) {
        console.error('Error during cleanup:', error);
        // Force reset critical state even if cleanup fails
        isLoading = false;
        currentAbortController = null;
        messageStartTime = null;
    }
}

// Send message
async function sendMessage() {
    // Check if already loading
    if (isLoading) {
        console.warn('Request already in progress');
        return;
    }
    
    // Check if conversation is selected
    if (!currentConversationId) {
        console.warn('No conversation selected');
        return;
    }
    
    // Check for rapid requests (cooldown)
    const now = Date.now();
    if (now - lastRequestTime < requestCooldown) {
        console.warn('Request too soon after previous request');
        return;
    }
    lastRequestTime = now;

    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    const selectedModel = document.getElementById('modelSelect').value;

    if (!message) {
        console.warn('Empty message');
        return;
    }
    
    // Validate model selection
    if (!selectedModel) {
        console.warn('No model selected');
        alert('Please select a model first.');
        return;
    }

    // Create new AbortController for this request
    currentAbortController = new AbortController();

    // Record start time for performance measurement
    messageStartTime = Date.now();

    // Add user message to chat
    addMessageToChat('user', message);
    messageInput.value = '';
    autoResize(messageInput);

    // Show loading and update button to cancel with smooth transition
    isLoading = true;
    const sendBtn = document.getElementById('sendBtn');
    
    // Add transition animation
    sendBtn.style.transform = 'scale(0.95)';
    setTimeout(() => {
        sendBtn.style.transform = 'scale(1)';
        sendBtn.disabled = false; // Keep enabled so it can be clicked to cancel
        sendBtn.textContent = 'Cancel';
        sendBtn.classList.add('cancel');
        sendBtn.onclick = cancelMessage;
    }, 150);

    const { loadingDiv, textSpan } = createAnimatedLoading();
    document.getElementById('chatContainer').appendChild(loadingDiv);
    startLoadingTextRotation(textSpan);
    scrollToBottom();

    try {
        // Add timeout handling for better user experience
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => {
                reject(new Error('Request timeout - taking longer than expected'));
            }, cancellationPreferences.timeoutDuration);
        });
        
        const fetchPromise = fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                conversation_id: currentConversationId,
                message: message,
                model: selectedModel
            }),
            signal: currentAbortController.signal
        });
        
        const response = await Promise.race([fetchPromise, timeoutPromise]);

        // Check if request was aborted
        if (currentAbortController.signal.aborted) {
            return;
        }

        const data = await response.json();

        // Calculate response time
        const responseTime = messageStartTime ? Date.now() - messageStartTime : 0;
        const estimatedTokens = estimateTokens(data.response);

        // Remove loading
        stopLoadingTextRotation();
        loadingDiv.remove();

        // Add assistant response with stats, including backend info
        const backendType = data.backend_type || null;
        const model = data.model || selectedModel;
        addMessageToChat('assistant', data.response, model, null, responseTime, estimatedTokens, backendType);

        // Reload conversations to update timestamp
        await loadConversations();

    } catch (error) {
        if (error.name === 'AbortError') {
            // Request was cancelled - cleanup is already handled by cancelMessage()
            console.log('Request was aborted');
            return;
        }
        
        // Handle other errors
        console.error('Send message error:', error);
        
        try {
            stopLoadingTextRotation();
            const loadingDiv = document.querySelector('.loading');
            if (loadingDiv && loadingDiv.parentNode) {
                loadingDiv.remove();
            }
            
            // Show appropriate error message with icons
            let errorMessage = '❌ Error: Could not get response from backend';
            let notificationType = 'error';
            
            if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
                errorMessage = '🌐 Network Error: Connection failed. Check your internet connection.';
                showCancellationNotification('Network connection failed', 'error');
            } else if (error.message.includes('timeout')) {
                errorMessage = '⏱️ Timeout Error: Request took too long. Please try again.';
                showCancellationNotification('Request timed out after 30 seconds', 'error');
            } else if (error.message.includes('backend')) {
                errorMessage = '🔧 Backend Error: The AI service is temporarily unavailable.';
                showCancellationNotification('Backend service unavailable', 'error');
            } else {
                showCancellationNotification('Unexpected error occurred', 'error');
            }
            
            addMessageToChat('assistant', errorMessage);
        } catch (errorHandlingError) {
            console.error('Error while handling error:', errorHandlingError);
        }
    } finally {
        // Only cleanup if request wasn't aborted (avoid double cleanup)
        if (!currentAbortController?.signal.aborted) {
            cleanup();
        }
    }
}

// Add message to chat with markdown support and thinking tag processing
function addMessageToChat(role, content, model = null, timestamp = null, responseTime = null, tokens = null, backendType = null, isSystemMessage = false) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    // Add system message class for special styling
    if (isSystemMessage) {
        messageDiv.classList.add('system-message');
    }

    const time = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    
    // Create model info with backend indicator
    let modelInfo = '';
    if (model && role === 'assistant') {
        const backendIndicator = backendType ? getBackendIndicator(backendType) : '';
        modelInfo = ` • ${backendIndicator} ${model}`;
    }

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
            // First process thinking tags, then apply markdown
            const processedContent = processThinkingTags(content);
            contentHtml = marked.parse(processedContent);
        } catch (error) {
            console.error('Markdown parsing error:', error);
            // Fallback: process thinking tags then escape HTML
            const processedContent = processThinkingTags(content);
            contentHtml = escapeHtml(processedContent).replace(/\n/g, '<br>');
        }
    } else {
        contentHtml = escapeHtml(content).replace(/\n/g, '<br>');
    }

    messageDiv.innerHTML = `
        <div class="message-content">
            ${contentHtml}
            <div class="message-footer">
                <div class="message-meta">${time}${modelInfo}</div>
                ${statsString ? `<div class="message-stats">${statsString.replace('<div class="message-stats">', '').replace('</div>', '')}</div>` : ''}
            </div>
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

// Handle global key events
function handleGlobalKeyDown(event) {
    // Handle Escape key for cancellation
    if (event.key === 'Escape' && isLoading) {
        event.preventDefault();
        cancelMessage();
        return;
    }
}

// Handle page unload/navigation during active requests
function handleBeforeUnload(event) {
    if (isLoading && currentAbortController) {
        // Cancel the request before leaving
        try {
            currentAbortController.abort();
        } catch (error) {
            console.error('Error cancelling request during page unload:', error);
        }
        
        // Show warning to user only if preference is enabled
        if (cancellationPreferences.confirmNavigation) {
            event.preventDefault();
            event.returnValue = 'A request is currently in progress. Are you sure you want to leave?';
            return event.returnValue;
        }
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
    
    // Add global keyboard event listener
    document.addEventListener('keydown', handleGlobalKeyDown);
    
    // Add beforeunload event listener for handling page navigation during requests
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    // Add mobile-specific touch event handling for better cancellation experience
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        // Add touch feedback for mobile devices
        sendBtn.addEventListener('touchstart', function(e) {
            if (this.classList.contains('cancel')) {
                this.style.transform = 'scale(0.95)';
            }
        });
        
        sendBtn.addEventListener('touchend', function(e) {
            if (this.classList.contains('cancel')) {
                this.style.transform = 'scale(1)';
            }
        });
        
        // Handle double-tap to cancel on mobile
        let lastTap = 0;
        sendBtn.addEventListener('touchend', function(e) {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTap;
            
            if (tapLength < 500 && tapLength > 0 && this.classList.contains('cancel')) {
                e.preventDefault();
                cancelMessage();
                showCancellationNotification('Double-tap detected - cancelling request');
            }
            lastTap = currentTime;
        });
    }
});

// Initialize app when page loads
window.addEventListener('load', init);
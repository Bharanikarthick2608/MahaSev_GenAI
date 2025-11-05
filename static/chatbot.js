// Chatbot JavaScript for AI Admin Assistant

// Global state
let conversationHistory = [];
let districts = [];
let currentDistrict = "All Districts";

// DOM elements
const chatContainer = document.getElementById('chatContainer');
const queryInput = document.getElementById('queryInput');
const sendBtn = document.getElementById('sendBtn');
const districtSelect = document.getElementById('districtSelect');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');
const metricsSection = document.getElementById('metricsSection');
const metricsGrid = document.getElementById('metricsGrid');
const metricsDistrictName = document.getElementById('metricsDistrictName');
const metricsRecommendations = document.getElementById('metricsRecommendations');
const recommendationsList = document.getElementById('recommendationsList');
const xaiLogSection = document.getElementById('xaiLogSection');
const xaiLogToggle = document.getElementById('xaiLogToggle');
const xaiLogContent = document.getElementById('xaiLogContent');
const xaiLogCount = document.getElementById('xaiLogCount');

// Initialize on page load (only if chatbot view is active)
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're in the unified dashboard
    const chatbotView = document.getElementById('chatbotView');
    if (chatbotView && !chatbotView.classList.contains('hidden')) {
        initializeChatbot();
    } else if (!chatbotView) {
        // Standalone chatbot page (legacy)
        initializeChatbot();
    }
});

// Initialize chatbot
async function initializeChatbot() {
    // Check if chatbot elements exist
    if (!chatContainer || !queryInput || !sendBtn) {
        console.warn('Chatbot elements not found, skipping initialization');
        return;
    }
    
    // Prevent double initialization
    if (window.chatbotInitialized) {
        return;
    }
    window.chatbotInitialized = true;
    
    // Load districts
    await loadDistricts();
    
    // Setup event listeners
    setupEventListeners();
    
    // Auto-resize textarea
    setupTextareaAutoResize();
}

// Load districts from API
async function loadDistricts() {
    try {
        const response = await fetch('/api/chatbot/districts');
        const data = await response.json();
        
        if (data.success && data.districts) {
            districts = data.districts;
            
            // Populate district select
            districts.forEach(district => {
                const option = document.createElement('option');
                option.value = district;
                option.textContent = district;
                districtSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading districts:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Send button
    sendBtn.addEventListener('click', handleSendMessage);
    
    // Enter key to send (Shift+Enter for new line)
    queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    
    // Clear history
    clearHistoryBtn.addEventListener('click', clearHistory);
    
    // District selection
    districtSelect.addEventListener('change', (e) => {
        currentDistrict = e.target.value;
    });
    
    // Suggested questions - prevent multiple clicks
    document.querySelectorAll('.suggested-question-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            // Disable button to prevent multiple clicks
            if (btn.disabled) return;
            btn.disabled = true;
            
            const question = btn.getAttribute('data-question');
            if (question && queryInput && !queryInput.disabled) {
                queryInput.value = question;
                queryInput.focus();
                
                // Re-enable button after a short delay
                setTimeout(() => {
                    btn.disabled = false;
                }, 2000);
                
                handleSendMessage();
            } else {
                btn.disabled = false;
            }
        });
    });
    
    // XAI log toggle
    xaiLogToggle.addEventListener('click', toggleXaiLog);
}

// Setup textarea auto-resize
function setupTextareaAutoResize() {
    queryInput.addEventListener('input', () => {
        queryInput.style.height = 'auto';
        queryInput.style.height = Math.min(queryInput.scrollHeight, 120) + 'px';
    });
}

// Handle send message
async function handleSendMessage() {
    const query = queryInput.value.trim();
    
    if (!query) {
        return;
    }
    
    // Prevent multiple submissions
    if (queryInput.disabled || sendBtn.disabled) {
        return;
    }
    
    // Disable input and button during processing
    queryInput.disabled = true;
    sendBtn.disabled = true;
    
    // Get selected district
    const selectedDistrict = districtSelect.value;
    
    // Clear input
    queryInput.value = '';
    queryInput.style.height = 'auto';
    
    // Remove welcome message if first query
    const welcomeMessage = chatContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    // Add user message
    addMessage('user', query);
    
    // Add loading indicator
    const loadingId = addLoadingMessage();
    
    try {
        // Send query to API
        const response = await fetch('/api/chatbot/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                district: selectedDistrict !== 'All Districts' ? selectedDistrict : null
            })
        });
        
        const data = await response.json();
        
        // Remove loading indicator
        removeLoadingMessage(loadingId);
        
        // Add assistant response - always show the response, even if success is false
        // The chatbot service may return an error message in the response field
        if (data.response) {
            addMessage('assistant', data.response);
        } else if (!data.success) {
            // Fallback if no response field
            const errorMsg = data.error || 'Sorry, I encountered an error processing your query. Please try again.';
            addMessage('assistant', errorMsg);
        }
        
        // Handle XAI log (always show if available, even for errors)
        if (data.xai_log && data.xai_log.length > 0) {
            displayXaiLog(data.xai_log);
        }
        
        // Handle metrics if district-specific and successful
        if (data.success && data.is_district_specific && data.detected_district) {
            await loadAndDisplayMetrics(data.detected_district);
        } else {
            hideMetrics();
        }
    } catch (error) {
        console.error('Error sending message:', error);
        removeLoadingMessage(loadingId);
        addMessage('assistant', 'Sorry, I encountered an error. Please check your connection and try again.');
    } finally {
        // Re-enable input and button
        queryInput.disabled = false;
        sendBtn.disabled = false;
    }
}

// Add message to chat
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = new Date().toLocaleTimeString();
    
    bubble.appendChild(contentDiv);
    bubble.appendChild(timeDiv);
    messageDiv.appendChild(bubble);
    
    chatContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    // Add to history
    conversationHistory.push({ role, content, timestamp: new Date() });
}

// Add loading message
function addLoadingMessage() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.id = 'loading-message';
    
    const bubble = document.createElement('div');
    bubble.className = 'loading-message';
    
    bubble.innerHTML = `
        <span>Processing your query</span>
        <div class="loading-dots">
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
        </div>
    `;
    
    loadingDiv.appendChild(bubble);
    chatContainer.appendChild(loadingDiv);
    
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    return 'loading-message';
}

// Remove loading message
function removeLoadingMessage(loadingId) {
    const loadingElement = document.getElementById(loadingId);
    if (loadingElement) {
        loadingElement.remove();
    }
}

// Load and display metrics
async function loadAndDisplayMetrics(district) {
    try {
        const response = await fetch(`/api/chatbot/metrics/${encodeURIComponent(district)}`);
        const data = await response.json();
        
        if (data.success && data.metrics) {
            displayMetrics(district, data.metrics);
        }
    } catch (error) {
        console.error('Error loading metrics:', error);
    }
}

// Display metrics
function displayMetrics(district, metrics) {
    // Update district name
    metricsDistrictName.textContent = district;
    
    // Clear previous metrics
    metricsGrid.innerHTML = '';
    
    // Define metric cards
    const metricCards = [
        {
            name: 'P-Score',
            value: metrics.p_score.toFixed(2),
            description: 'Cross-Sectoral Prioritization Score',
            priority: getPriorityLevel(metrics.p_score)
        },
        {
            name: 'HVI',
            value: metrics.hvi_score.toFixed(2),
            description: 'Health Vulnerability Index',
            priority: getPriorityLevel(metrics.hvi_score)
        },
        {
            name: 'ISS',
            value: metrics.iss_score.toFixed(2),
            description: 'Infrastructure Strain Score',
            priority: getPriorityLevel(metrics.iss_score)
        },
        {
            name: 'RCS',
            value: metrics.rcs_score.toFixed(2),
            description: 'Resource Contention Score',
            priority: getPriorityLevel(metrics.rcs_score)
        },
        {
            name: 'SEL Index',
            value: metrics.sel_index.toFixed(2),
            description: 'Service Equity Lag Index',
            priority: getSELPriority(metrics.sel_index)
        }
    ];
    
    // Create metric cards
    metricCards.forEach(metric => {
        const card = createMetricCard(metric);
        metricsGrid.appendChild(card);
    });
    
    // Display recommendations
    if (metrics.recommendations && metrics.recommendations.length > 0) {
        recommendationsList.innerHTML = '';
        metrics.recommendations.forEach(rec => {
            const li = document.createElement('li');
            li.textContent = rec;
            recommendationsList.appendChild(li);
        });
        metricsRecommendations.style.display = 'block';
    } else {
        metricsRecommendations.style.display = 'none';
    }
    
    // Show metrics section
    metricsSection.style.display = 'block';
    
    // Smooth scroll to metrics
    setTimeout(() => {
        metricsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
}

// Create metric card element
function createMetricCard(metric) {
    const card = document.createElement('div');
    card.className = `metric-card-chat ${metric.priority}`;
    
    card.innerHTML = `
        <div class="metric-name">${metric.name}</div>
        <div class="metric-value-chat">${metric.value}</div>
        <div class="metric-description">${metric.description}</div>
    `;
    
    return card;
}

// Get priority level for metric value
function getPriorityLevel(score) {
    if (score >= 8.0) return 'critical';
    if (score >= 6.0) return 'high';
    if (score >= 4.0) return 'medium';
    return 'low';
}

// Get priority level for SEL index
function getSELPriority(selIndex) {
    if (selIndex >= 1.3) return 'critical';
    if (selIndex >= 1.2) return 'high';
    return 'low';
}

// Hide metrics
function hideMetrics() {
    metricsSection.style.display = 'none';
}

// Display XAI log
function displayXaiLog(xaiLog) {
    if (!xaiLog || xaiLog.length === 0) {
        xaiLogSection.style.display = 'none';
        return;
    }
    
    // Update count
    xaiLogCount.textContent = xaiLog.length;
    
    // Clear previous log
    xaiLogContent.innerHTML = '';
    
    // Add log entries
    xaiLog.forEach(entry => {
        const logEntry = document.createElement('div');
        logEntry.className = 'xai-log-entry';
        
        const step = document.createElement('div');
        step.className = 'xai-log-step';
        step.textContent = entry.step || 'Step';
        
        const action = document.createElement('div');
        action.className = 'xai-log-action';
        action.textContent = entry.decision || entry.action || entry.reasoning || 'No details';
        
        logEntry.appendChild(step);
        logEntry.appendChild(action);
        xaiLogContent.appendChild(logEntry);
    });
    
    // Show XAI log section
    xaiLogSection.style.display = 'block';
    
    // Expand by default
    xaiLogContent.style.display = 'block';
    xaiLogToggle.classList.remove('collapsed');
}

// Toggle XAI log
function toggleXaiLog() {
    const isCollapsed = xaiLogContent.style.display === 'none';
    
    if (isCollapsed) {
        xaiLogContent.style.display = 'block';
        xaiLogToggle.classList.remove('collapsed');
    } else {
        xaiLogContent.style.display = 'none';
        xaiLogToggle.classList.add('collapsed');
    }
}

// Clear history
function clearHistory() {
    if (confirm('Are you sure you want to clear the conversation history?')) {
        conversationHistory = [];
        
        // Remove all messages except welcome
        const messages = chatContainer.querySelectorAll('.message');
        messages.forEach(msg => msg.remove());
        
        // Show welcome message again
        const welcomeMessage = document.createElement('div');
        welcomeMessage.className = 'welcome-message';
        welcomeMessage.innerHTML = `
            <div class="welcome-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
            </div>
            <h2>Welcome to AI Admin Assistant</h2>
            <p>Ask me anything about districts, health infrastructure, resources, or service metrics. I can help you:</p>
            <ul>
                <li>Analyze district-specific data and metrics</li>
                <li>Compare multiple districts</li>
                <li>Get health vulnerability assessments</li>
                <li>Check infrastructure strain scores</li>
                <li>Review resource allocation and worker utilization</li>
            </ul>
            <p class="example-queries">Try asking: "What is the health vulnerability in Ahmednagar?" or "Show me districts with high P-Scores"</p>
        `;
        chatContainer.appendChild(welcomeMessage);
        
        // Hide metrics and XAI log
        hideMetrics();
        xaiLogSection.style.display = 'none';
        
        // Reset district selection
        districtSelect.value = 'All Districts';
        currentDistrict = 'All Districts';
    }
}


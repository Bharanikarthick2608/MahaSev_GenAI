// Global state
let currentTab = 'alerts';
let currentSeverity = 'All';
let currentStatus = 'Resolved';
let sentimentChart1 = null;
let sentimentChart2 = null;
let sentimentChart3 = null;

// Initialize
function init() {
    try {
        console.log('Initializing dashboard...');
        loadMetrics();
        setupEventListeners();
        loadContent();
    } catch (error) {
        console.error('Error initializing dashboard:', error);
    }
}

// Test if script is loading
console.log('Script.js loaded');

// Wait for DOM to be ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    // DOM is already ready
    init();
}

// Load dashboard metrics
async function loadMetrics() {
    try {
        const response = await fetch('/api/metrics');
        const data = await response.json();
        
        document.getElementById('activeAlerts').textContent = data.active_alerts;
        document.getElementById('criticalIssues').textContent = data.critical_issues;
        document.getElementById('totalFeedback').textContent = data.total_feedback;
        document.getElementById('positiveSentiment').textContent = data.positive_sentiment;
        
        // Update tab counts dynamically based on actual data counts
        const alertsCountEl = document.getElementById('alertsCount');
        const feedbackCountEl = document.getElementById('feedbackCount');
        const sentimentCountEl = document.getElementById('sentimentCount');
        
        if (alertsCountEl) alertsCountEl.textContent = `(${data.alerts_count || 0})`;
        if (feedbackCountEl) feedbackCountEl.textContent = `(${data.feedback_count || 0})`;
        if (sentimentCountEl) sentimentCountEl.textContent = `(${data.sentiment_count || 0})`;
    } catch (error) {
        console.error('Error loading metrics:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Use event delegation on tabs section for tab buttons - this should work even if elements aren't ready yet
    const tabsSection = document.querySelector('.tabs-section');
    if (tabsSection) {
        console.log('Tabs section found, adding delegation listener');
        tabsSection.addEventListener('click', function(e) {
            // Find the closest button element (might be clicked on child elements)
            let target = e.target;
            
            // Walk up the DOM tree to find the tab button
            while (target && target !== tabsSection) {
                if (target.classList && target.classList.contains('tab-btn')) {
                    e.preventDefault();
                    e.stopPropagation();
                    const tabId = target.getAttribute('data-tab');
                    console.log('Tab button clicked via delegation, tabId:', tabId, 'target:', target);
                    if (tabId) {
                        console.log('Switching to tab via delegation:', tabId);
                        switchTab(tabId);
                        return false;
                    }
                    break;
                }
                target = target.parentElement;
            }
        }, true); // Use capture phase to catch events earlier
    } else {
        console.error('Tabs section not found!');
    }
    
    // Also add direct listeners as backup
    function addDirectListeners() {
        const alertsTab = document.getElementById('alertsTab');
        const feedbackTab = document.getElementById('feedbackTab');
        const sentimentTab = document.getElementById('sentimentTab');
        
        console.log('Setting up direct listeners', { 
            alertsTab: !!alertsTab, 
            feedbackTab: !!feedbackTab, 
            sentimentTab: !!sentimentTab 
        });
        
        if (alertsTab) {
            alertsTab.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Alerts tab clicked directly');
                switchTab('alerts');
                return false;
            };
        }
        if (feedbackTab) {
            feedbackTab.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Feedback tab clicked directly');
                switchTab('feedback');
                return false;
            };
        }
        if (sentimentTab) {
            sentimentTab.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Sentiment tab clicked directly via onclick');
                switchTab('sentiment');
                return false;
            };
            // Also add event listener as additional handler
            sentimentTab.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Sentiment tab clicked directly via addEventListener');
                switchTab('sentiment');
                return false;
            });
        }
    }
    
    // Try immediately
    addDirectListeners();
    
    // Also try after a short delay
    setTimeout(addDirectListeners, 100);
    
    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const filterType = this.getAttribute('data-filter-type');
            const value = this.getAttribute('data-value');
            
            // Update active state
            document.querySelectorAll(`[data-filter-type="${filterType}"]`).forEach(b => {
                b.classList.remove('active');
            });
            this.classList.add('active');
            
            // Update filters
            if (filterType === 'severity') {
                currentSeverity = value;
            } else if (filterType === 'status') {
                currentStatus = value;
            }
            
            loadContent();
        });
    });
}

// Switch tabs - make globally accessible
window.switchTab = function switchTab(tab) {
    console.log('switchTab called with:', tab);
    if (!tab) {
        console.error('switchTab called without tab parameter!');
        return;
    }
    
    // Normalize tab name to lowercase
    tab = tab.toLowerCase();
    currentTab = tab;
    console.log('Current tab set to:', currentTab);
    
    // Update tab buttons
    const alertsTab = document.getElementById('alertsTab');
    const feedbackTab = document.getElementById('feedbackTab');
    const sentimentTab = document.getElementById('sentimentTab');
    
    // Remove active class from all tabs
    if (alertsTab) alertsTab.classList.remove('active');
    if (feedbackTab) feedbackTab.classList.remove('active');
    if (sentimentTab) sentimentTab.classList.remove('active');
    
    // Add active class to selected tab
    if (tab === 'alerts' && alertsTab) {
        alertsTab.classList.add('active');
        console.log('Alerts tab activated');
    }
    if (tab === 'feedback' && feedbackTab) {
        feedbackTab.classList.add('active');
        console.log('Feedback tab activated');
    }
    if (tab === 'sentiment' && sentimentTab) {
        sentimentTab.classList.add('active');
        console.log('Sentiment tab activated');
    }
    
    // Show/hide filters based on tab
    const filtersSection = document.querySelector('.filters-section');
    if (filtersSection) {
        if (tab === 'sentiment') {
            filtersSection.style.display = 'none';
        } else {
            filtersSection.style.display = 'flex';
        }
    }
    
    // Load content
    console.log('About to load content for tab:', currentTab);
    loadContent();
}

// Load content based on current tab and filters
async function loadContent() {
    console.log('loadContent called, currentTab:', currentTab, 'type:', typeof currentTab);
    const contentList = document.getElementById('contentList');
    
    if (!contentList) {
        console.error('Content list element not found!');
        return;
    }
    
    // Check if sentiment tab is active - must check first before other content loading
    // Normalize comparison to handle any case variations
    const normalizedTab = String(currentTab).toLowerCase();
    if (normalizedTab === 'sentiment') {
        console.log('Detected sentiment tab - loading sentiment content...');
        await loadSentimentContent();
        return;
    }
    
    console.log('Loading regular content for tab:', currentTab);
    contentList.innerHTML = '<div class="empty-state">Loading...</div>';
    
    try {
        let endpoint = currentTab === 'alerts' ? '/api/alerts' : '/api/feedback';
        console.log('Fetching from endpoint:', endpoint);
        const params = new URLSearchParams({
            severity: currentSeverity,
            status: currentStatus
        });
        
        const response = await fetch(`${endpoint}?${params}`);
        const data = await response.json();
        
        const items = currentTab === 'alerts' ? data.alerts : data.feedback;
        console.log('Loaded items:', items.length);
        
        if (items.length === 0) {
            contentList.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <p>No ${currentTab === 'alerts' ? 'alerts' : 'feedback'} found with the selected filters.</p>
                </div>
            `;
            return;
        }
        
        contentList.innerHTML = items.map(item => createItemCard(item)).join('');
        
    } catch (error) {
        console.error('Error loading content:', error);
        contentList.innerHTML = '<div class="empty-state">Error loading content. Please try again.</div>';
    }
}

// Create item card HTML
function createItemCard(item) {
    const severityClass = `severity-${item.severity.toLowerCase()}`;
    const actionableInfo = item.actionable_intelligence || item.insight;
    
    return `
        <div class="alert-card">
            <div class="alert-header">
                <div class="alert-title-row">
                    <div class="alert-title">${escapeHtml(item.title)}</div>
                    <span class="alert-severity ${severityClass}">${item.severity}</span>
                </div>
                <div class="alert-timestamp">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    ${item.timestamp}
                </div>
            </div>
            <div class="alert-description">${escapeHtml(item.description)}</div>
            ${actionableInfo ? `<div class="alert-intelligence">${escapeHtml(actionableInfo)}</div>` : ''}
        </div>
    `;
}

// Load sentiment content with charts and word cloud
async function loadSentimentContent() {
    const contentList = document.getElementById('contentList');
    contentList.innerHTML = '<div class="empty-state">Loading...</div>';
    
    try {
        const response = await fetch('/api/sentiment');
        const data = await response.json();
        
        contentList.innerHTML = `
            <div class="sentiment-container">
                <div class="sentiment-section">
                    <h2 class="section-title">Sentiment Distribution</h2>
                    <div class="chart-container">
                        <canvas id="sentimentPieChart"></canvas>
                    </div>
                </div>
                
                <div class="sentiment-section">
                    <h2 class="section-title">Sentiment by Topic</h2>
                    <div class="chart-container">
                        <canvas id="topicSentimentChart"></canvas>
                    </div>
                </div>
                
                <div class="sentiment-section full-width">
                    <h2 class="section-title">Word Cloud</h2>
                    <div class="wordcloud-container">
                        <canvas id="wordCloudCanvas"></canvas>
                    </div>
                </div>
                
                <div class="sentiment-section full-width">
                    <h2 class="section-title">Sentiment Trends Over Time</h2>
                    <div class="chart-container">
                        <canvas id="sentimentTrendChart"></canvas>
                    </div>
                </div>
            </div>
        `;
        
        // Render charts after HTML is updated
        // Give extra time for wordcloud library to load if needed
        setTimeout(() => {
            renderSentimentPieChart(data.sentiment_distribution);
            renderTopicSentimentChart(data.topic_sentiment);
            renderSentimentTrendChart(data.sentiment_trends);
            // Render word cloud last to ensure library is loaded
            renderWordCloud(data.word_frequency);
        }, 150);
        
    } catch (error) {
        console.error('Error loading sentiment content:', error);
        contentList.innerHTML = '<div class="empty-state">Error loading sentiment data. Please try again.</div>';
    }
}

// Render sentiment distribution pie chart
function renderSentimentPieChart(distribution) {
    try {
        const ctx = document.getElementById('sentimentPieChart');
        if (!ctx) {
            console.warn('Sentiment pie chart canvas not found');
            return;
        }
        
        if (typeof Chart === 'undefined') {
            console.error('Chart.js library not loaded');
            return;
        }
        
        if (sentimentChart1) {
            sentimentChart1.destroy();
        }
        
        sentimentChart1 = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Positive', 'Neutral', 'Negative'],
                datasets: [{
                    data: [distribution.positive, distribution.neutral, distribution.negative],
                    backgroundColor: ['#28a745', '#ffc107', '#dc3545'],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            font: {
                                size: 14
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ': ' + context.parsed + '%';
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error rendering sentiment pie chart:', error);
    }
}

// Render word cloud
function renderWordCloud(wordFrequency) {
    try {
        const canvas = document.getElementById('wordCloudCanvas');
        if (!canvas) {
            console.warn('Word cloud canvas not found');
            return;
        }
        
        // Check if WordCloud library is loaded
        // wordcloud2.js library exposes itself as WordCloud2 (capital W, capital C, 2)
        // Check multiple possible global variable names
        let WordCloudLib = null;
        
        // Try different possible global names
        if (typeof window.WordCloud2 !== 'undefined') {
            WordCloudLib = window.WordCloud2;
        } else if (typeof window.wordcloud !== 'undefined') {
            WordCloudLib = window.wordcloud;
        } else if (typeof window.WordCloud !== 'undefined') {
            WordCloudLib = window.WordCloud;
        } else if (window.wordcloud2 && typeof window.wordcloud2.default !== 'undefined') {
            WordCloudLib = window.wordcloud2.default;
        } else if (typeof window.wordcloud2 !== 'undefined') {
            WordCloudLib = window.wordcloud2;
        }
        
        if (!WordCloudLib || typeof WordCloudLib !== 'function') {
            console.error('WordCloud library not loaded. Available window properties:', 
                Object.keys(window).filter(k => k.toLowerCase().includes('word')));
            console.log('Trying to load library again...');
            
            // Set canvas size and show error message
            const ctx = canvas.getContext('2d');
            canvas.width = canvas.parentElement.offsetWidth || 800;
            canvas.height = 400;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.font = '16px Arial';
            ctx.fillStyle = '#666';
            ctx.textAlign = 'center';
            ctx.fillText('Word Cloud library not loaded', canvas.width / 2, canvas.height / 2);
            ctx.font = '12px Arial';
            ctx.fillText('Please refresh the page', canvas.width / 2, canvas.height / 2 + 30);
            
            // Try again after a delay
            setTimeout(() => {
                renderWordCloud(wordFrequency);
            }, 500);
            return;
        }
        
        console.log('WordCloud library loaded successfully');
        
        // Prepare word list for wordcloud
        const wordList = wordFrequency.map(item => [item.word, item.frequency]);
        
        // Clear previous word cloud
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width || 800, canvas.height || 400);
        
        // Set canvas size
        canvas.width = canvas.parentElement.offsetWidth || 800;
        canvas.height = 400;
        
        // Generate word cloud
        WordCloudLib(canvas, {
            list: wordList,
            gridSize: 8,
            weightFactor: 3,
            fontFamily: 'Arial, sans-serif',
            color: function(word, weight, fontSize, distance, theta) {
                // Color words based on frequency
                if (weight > 80) return '#0056b3';
                if (weight > 50) return '#28a745';
                if (weight > 30) return '#ffc107';
                return '#6c757d';
            },
            rotateRatio: 0.3,
            rotationSteps: 2,
            backgroundColor: 'transparent',
            shrinkToFit: true
        });
    } catch (error) {
        console.error('Error rendering word cloud:', error);
    }
}

// Render sentiment trend chart
function renderSentimentTrendChart(trends) {
    const ctx = document.getElementById('sentimentTrendChart');
    if (!ctx) return;
    
    if (sentimentChart2) {
        sentimentChart2.destroy();
    }
    
    const dates = trends.map(t => {
        const date = new Date(t.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    sentimentChart2 = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Positive',
                    data: trends.map(t => t.positive),
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Neutral',
                    data: trends.map(t => t.neutral),
                    borderColor: '#ffc107',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Negative',
                    data: trends.map(t => t.negative),
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 14
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

// Render topic sentiment chart
function renderTopicSentimentChart(topics) {
    const ctx = document.getElementById('topicSentimentChart');
    if (!ctx) return;
    
    if (sentimentChart3) {
        sentimentChart3.destroy();
    }
    
    sentimentChart3 = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: topics.map(t => t.topic),
            datasets: [
                {
                    label: 'Positive',
                    data: topics.map(t => t.positive),
                    backgroundColor: '#28a745'
                },
                {
                    label: 'Neutral',
                    data: topics.map(t => t.neutral),
                    backgroundColor: '#ffc107'
                },
                {
                    label: 'Negative',
                    data: topics.map(t => t.negative),
                    backgroundColor: '#dc3545'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 14
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    stacked: true
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// Global state
let currentTab = 'alerts';
let currentSeverity = 'All';
let currentStatus = 'Resolved';

// Initialize (only if alerts view is active)
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're in the unified dashboard
    const alertsView = document.getElementById('alertsView');
    if (alertsView && !alertsView.classList.contains('hidden')) {
        loadMetrics();
        setupEventListeners();
        loadContent();
    } else if (!alertsView) {
        // Standalone alerts page (legacy)
        loadMetrics();
        setupEventListeners();
        loadContent();
    }
});

// Load dashboard metrics
async function loadMetrics() {
    try {
        const response = await fetch('/api/metrics');
        const data = await response.json();
        
        const activeAlertsEl = document.getElementById('activeAlerts');
        const criticalIssuesEl = document.getElementById('criticalIssues');
        const totalFeedbackEl = document.getElementById('totalFeedback');
        const positiveSentimentEl = document.getElementById('positiveSentiment');
        const alertsCountEl = document.getElementById('alertsCount');
        const feedbackCountEl = document.getElementById('feedbackCount');
        const navAlertsBadgeEl = document.getElementById('navAlertsBadge');
        
        if (activeAlertsEl) activeAlertsEl.textContent = data.active_alerts;
        if (criticalIssuesEl) criticalIssuesEl.textContent = data.critical_issues;
        if (totalFeedbackEl) totalFeedbackEl.textContent = data.total_feedback;
        if (positiveSentimentEl) positiveSentimentEl.textContent = data.positive_sentiment;
        
        // Update tab counts dynamically based on actual data counts
        if (alertsCountEl) alertsCountEl.textContent = `(${data.alerts_count || 0})`;
        if (feedbackCountEl) feedbackCountEl.textContent = `(${data.feedback_count || 0})`;
        
        // Update sidebar navigation badge
        if (navAlertsBadgeEl) navAlertsBadgeEl.textContent = data.active_alerts || 0;
    } catch (error) {
        console.error('Error loading metrics:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Tab buttons
    document.getElementById('alertsTab').addEventListener('click', () => switchTab('alerts'));
    document.getElementById('feedbackTab').addEventListener('click', () => switchTab('feedback'));
    
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

// Switch tabs
function switchTab(tab) {
    currentTab = tab;
    
    // Update tab buttons
    document.getElementById('alertsTab').classList.toggle('active', tab === 'alerts');
    document.getElementById('feedbackTab').classList.toggle('active', tab === 'feedback');
    
    // Load content
    loadContent();
}

// Load content based on current tab and filters
async function loadContent() {
    const contentList = document.getElementById('contentList');
    contentList.innerHTML = '<div class="empty-state">Loading...</div>';
    
    try {
        let endpoint = currentTab === 'alerts' ? '/api/alerts' : '/api/feedback';
        const params = new URLSearchParams({
            severity: currentSeverity,
            status: currentStatus
        });
        
        const response = await fetch(`${endpoint}?${params}`);
        const data = await response.json();
        
        const items = currentTab === 'alerts' ? data.alerts : data.feedback;
        
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

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


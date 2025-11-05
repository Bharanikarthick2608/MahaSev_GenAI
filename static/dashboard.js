// Unified Dashboard Navigation and Sidebar Control

// Global state
let currentView = 'chatbot';
let sidebarCollapsed = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeDashboard();
});

// Initialize dashboard
function initializeDashboard() {
    setupSidebar();
    setupNavigation();
    setupFeedbackForm();
    
    // Determine default view based on user type
    // Check if multilingual bot nav exists (citizen view)
    const multilingualNav = document.getElementById('navMultilingualBot');
    const chatbotNav = document.getElementById('navChatbot');
    
    if (multilingualNav && multilingualNav.classList.contains('active')) {
        // Citizen view - show multilingual bot
        showView('multilingual-bot');
    } else if (chatbotNav) {
        // Admin view - show AI Assistant
        showView('chatbot');
    } else {
        // Fallback
        showView('multilingual-bot');
    }
}

// Setup sidebar toggle
function setupSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebarToggle');
    const mainContent = document.getElementById('mainContent');
    
    // Toggle sidebar
    toggleBtn.addEventListener('click', () => {
        sidebarCollapsed = !sidebarCollapsed;
        sidebar.classList.toggle('collapsed', sidebarCollapsed);
        
        // Update toggle icon
        const icon = toggleBtn.querySelector('svg');
        if (sidebarCollapsed) {
            icon.innerHTML = `
                <line x1="12" y1="12" x2="19" y2="12"></line>
                <line x1="12" y1="6" x2="19" y2="6"></line>
                <line x1="12" y1="18" x2="19" y2="18"></line>
            `;
        } else {
            icon.innerHTML = `
                <line x1="3" y1="12" x2="21" y2="12"></line>
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <line x1="3" y1="18" x2="21" y2="18"></line>
            `;
        }
    });
    
    // Mobile menu toggle
    let menuOverlay = document.querySelector('.menu-overlay');
    if (!menuOverlay) {
        menuOverlay = document.createElement('div');
        menuOverlay.className = 'menu-overlay';
        document.body.appendChild(menuOverlay);
    }
    
    menuOverlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        menuOverlay.style.display = 'none';
    });
    
    // Update toggle button behavior for mobile
    toggleBtn.addEventListener('click', () => {
        if (window.innerWidth <= 768) {
            sidebar.classList.toggle('open');
            menuOverlay.style.display = sidebar.classList.contains('open') ? 'block' : 'none';
        }
    });
}

// Setup navigation
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const view = item.getAttribute('data-view');
            const href = item.getAttribute('href');
            
            // If item has data-view, use internal navigation
            if (view) {
                e.preventDefault();
            showView(view);
            }
            // If item has href and target="_blank", let it open in new tab
            else if (href && item.getAttribute('target') === '_blank') {
                // Let the default behavior happen (open in new tab)
                return;
            }
            // Otherwise prevent default
            else if (href && href !== '#') {
                // For other href links, allow navigation
                return;
            } else {
                e.preventDefault();
            }
        });
    });
}

// Show specific view
function showView(view) {
    currentView = view;
    
    // Hide all views
    document.querySelectorAll('.view-container').forEach(v => {
        v.classList.add('hidden');
    });
    
    // Show selected view
    const viewMap = {
        'alerts': 'alertsView',
        'metrics': 'metricsView',
        'chatbot': 'chatbotView',
        'policy-sandbox': 'policySandboxView',
        'workforce': 'workforceView',
        'forecast': 'forecastView',
        'multilingual-bot': 'multilingual-botView',
        'feedback-portal': 'feedback-portalView',
        'tickets': 'ticketsView'
    };
    
    const viewId = viewMap[view] || `${view}View`;
    const targetView = document.getElementById(viewId);
    if (targetView) {
        targetView.classList.remove('hidden');
    } else {
        console.error('View not found:', viewId);
    }
    
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.getAttribute('data-view') === view);
    });
    
    // Initialize view-specific functionality
    if (view === 'alerts') {
        // Initialize alerts view
        setTimeout(() => {
            if (typeof loadMetrics === 'function') {
                loadMetrics();
                if (typeof setupEventListeners === 'function') {
                    setupEventListeners();
                }
                if (typeof loadContent === 'function') {
                    loadContent();
                }
            }
        }, 100);
    } else if (view === 'chatbot') {
        // Initialize chatbot when view is shown
        setTimeout(() => {
            // Reset initialization flag to allow re-initialization
            window.chatbotInitialized = false;
            if (typeof initializeChatbot === 'function') {
                initializeChatbot();
            }
        }, 100);
    } else if (view === 'metrics') {
        // Initialize metrics dashboard when view is shown
        setTimeout(() => {
            if (typeof window.initializeMetrics === 'function') {
                window.initializeMetrics();
            } else if (typeof initializeMetrics === 'function') {
                initializeMetrics();
            }
        }, 200);
    } else if (view === 'policy-sandbox') {
        // Initialize policy sandbox when view is shown
        setTimeout(() => {
            if (typeof window.initializePolicySandbox === 'function') {
                window.initializePolicySandbox();
            }
        }, 200);
    } else if (view === 'workforce') {
        // Initialize workforce allocation when view is shown
        setTimeout(() => {
            if (typeof window.initializeWorkforce === 'function') {
                window.initializeWorkforce();
            }
        }, 200);
    } else if (view === 'tickets') {
        // Initialize ticket monitoring when view is shown
        setTimeout(() => {
            if (typeof window.initializeTickets === 'function') {
                window.initializeTickets();
            }
        }, 200);
    }
}

// Handle window resize
window.addEventListener('resize', () => {
    const sidebar = document.getElementById('sidebar');
    if (window.innerWidth > 768) {
        sidebar.classList.remove('open');
    }
});

// Setup feedback form handler
function setupFeedbackForm() {
    const feedbackForm = document.getElementById('feedbackForm');
    if (feedbackForm) {
        feedbackForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            // Get form data
            const formData = {
                name: document.getElementById('feedbackName').value,
                email: document.getElementById('feedbackEmail').value,
                category: document.getElementById('feedbackCategory').value,
                message: document.getElementById('feedbackMessage').value,
                timestamp: new Date().toISOString()
            };
            
            // Log feedback (in production, send to server)
            console.log('Feedback submitted:', formData);
            
            // Show success message
            const successMsg = document.getElementById('feedbackSuccess');
            if (successMsg) {
                feedbackForm.style.display = 'none';
                successMsg.style.display = 'block';
                
                // Reset form and hide success message after 3 seconds
                setTimeout(() => {
                    feedbackForm.reset();
                    feedbackForm.style.display = 'flex';
                    successMsg.style.display = 'none';
                }, 3000);
            }
        });
    }
}

// ==================== TICKET MONITORING FUNCTIONS ====================

let ticketsInitialized = false;
let currentFilters = {
    service_category: null,
    status: null,
    priority: null,
    district: null
};

// Initialize ticket monitoring
window.initializeTickets = function() {
    if (!ticketsInitialized) {
        setupTicketFilters();
        ticketsInitialized = true;
    }
    loadTicketStats();
    loadTicketFilters();
    loadTickets();
};

// Setup ticket filter event listeners
function setupTicketFilters() {
    const applyBtn = document.getElementById('applyFiltersBtn');
    const resetBtn = document.getElementById('resetFiltersBtn');
    
    if (applyBtn) {
        applyBtn.addEventListener('click', () => {
            currentFilters.service_category = document.getElementById('filterCategory').value;
            currentFilters.status = document.getElementById('filterStatus').value;
            currentFilters.priority = document.getElementById('filterPriority').value;
            currentFilters.district = document.getElementById('filterDistrict').value;
            loadTickets();
        });
    }
    
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            document.getElementById('filterCategory').value = 'All';
            document.getElementById('filterStatus').value = 'All';
            document.getElementById('filterPriority').value = 'All';
            document.getElementById('filterDistrict').value = 'All';
            currentFilters = {
                service_category: null,
                status: null,
                priority: null,
                district: null
            };
            loadTickets();
        });
    }
}

// Load ticket statistics
async function loadTicketStats() {
    try {
        const response = await fetch('/api/tickets/stats');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('totalTicketsCount').textContent = data.stats.total_tickets;
            document.getElementById('openTicketsCount').textContent = data.stats.open_tickets;
            document.getElementById('highPriorityCount').textContent = data.stats.high_priority_tickets;
            document.getElementById('avgResolutionTime').textContent = data.stats.average_resolution_hours;
            document.getElementById('escalatedCount').textContent = data.stats.escalated_tickets;
        }
    } catch (error) {
        console.error('Error loading ticket stats:', error);
    }
}

// Load filter options
async function loadTicketFilters() {
    try {
        const response = await fetch('/api/tickets/filters');
        const data = await response.json();
        
        if (data.success) {
            const filters = data.filters;
            
            // Populate category filter
            const categorySelect = document.getElementById('filterCategory');
            categorySelect.innerHTML = '<option value="All">All Categories</option>';
            filters.service_categories.forEach(cat => {
                categorySelect.innerHTML += `<option value="${cat}">${cat}</option>`;
            });
            
            // Populate status filter
            const statusSelect = document.getElementById('filterStatus');
            statusSelect.innerHTML = '<option value="All">All Statuses</option>';
            filters.statuses.forEach(status => {
                statusSelect.innerHTML += `<option value="${status}">${status}</option>`;
            });
            
            // Populate priority filter
            const prioritySelect = document.getElementById('filterPriority');
            prioritySelect.innerHTML = '<option value="All">All Priorities</option>';
            filters.priorities.forEach(priority => {
                prioritySelect.innerHTML += `<option value="${priority}">${priority}</option>`;
            });
            
            // Populate district filter
            const districtSelect = document.getElementById('filterDistrict');
            districtSelect.innerHTML = '<option value="All">All Districts</option>';
            filters.districts.forEach(district => {
                districtSelect.innerHTML += `<option value="${district}">${district}</option>`;
            });
        }
    } catch (error) {
        console.error('Error loading ticket filters:', error);
    }
}

// Load tickets with current filters
async function loadTickets() {
    const tbody = document.getElementById('ticketsTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="11" style="padding: 40px; text-align: center; color: #999;">
                <div class="loading-spinner" style="margin: 0 auto 16px;"></div>
                <p>Loading tickets...</p>
            </td>
        </tr>
    `;
    
    try {
        const params = new URLSearchParams();
        if (currentFilters.service_category && currentFilters.service_category !== 'All') {
            params.append('service_category', currentFilters.service_category);
        }
        if (currentFilters.status && currentFilters.status !== 'All') {
            params.append('status', currentFilters.status);
        }
        if (currentFilters.priority && currentFilters.priority !== 'All') {
            params.append('priority', currentFilters.priority);
        }
        if (currentFilters.district && currentFilters.district !== 'All') {
            params.append('district', currentFilters.district);
        }
        params.append('limit', '100');
        
        const response = await fetch(`/api/tickets?${params.toString()}`);
        const data = await response.json();
        
        if (data.success && data.tickets.length > 0) {
            tbody.innerHTML = data.tickets.map(ticket => {
                const priorityColor = ticket.Priority === 'High' ? '#dc3545' : ticket.Priority === 'Normal' ? '#ffc107' : '#28a745';
                const statusColor = ticket.Status === 'Open' || ticket.Status === 'Pending' ? '#fd7e14' : ticket.Status === 'In Progress' ? '#007bff' : '#28a745';
                
                return `
                    <tr style="border-bottom: 1px solid #dee2e6;">
                        <td style="padding: 12px; font-size: 13px; font-weight: 600; color: #667eea;">${ticket.Request_ID || 'N/A'}</td>
                        <td style="padding: 12px; font-size: 13px; color: #495057;">${ticket.Created_Timestamp || 'N/A'}</td>
                        <td style="padding: 12px; font-size: 13px; color: #495057;">${ticket.Service_Category || 'N/A'}</td>
                        <td style="padding: 12px; font-size: 13px; color: #495057;">${ticket.Sub_Category || 'N/A'}</td>
                        <td style="padding: 12px;">
                            <span style="padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; background: ${priorityColor}22; color: ${priorityColor};">
                                ${ticket.Priority || 'N/A'}
                            </span>
                        </td>
                        <td style="padding: 12px;">
                            <span style="padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; background: ${statusColor}22; color: ${statusColor};">
                                ${ticket.Status || 'N/A'}
                            </span>
                        </td>
                        <td style="padding: 12px; font-size: 13px; color: #495057;">${ticket.District || 'N/A'}</td>
                        <td style="padding: 12px; font-size: 13px; color: #495057;">${ticket.Area || 'N/A'}</td>
                        <td style="padding: 12px; font-size: 13px; color: #495057;">${ticket.Channel || 'N/A'}</td>
                        <td style="padding: 12px; font-size: 13px; color: #495057;">${ticket.Worker_Assigned || 'Not Assigned'}</td>
                        <td style="padding: 12px; font-size: 13px; color: #495057;">${ticket.Resolution_Time_Hours !== null ? ticket.Resolution_Time_Hours.toFixed(2) : 'N/A'}</td>
                    </tr>
                `;
            }).join('');
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="11" style="padding: 40px; text-align: center; color: #999;">
                        <p>No tickets found</p>
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading tickets:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="11" style="padding: 40px; text-align: center; color: #dc3545;">
                    <p>Error loading tickets. Please try again.</p>
                </td>
            </tr>
        `;
    }
}


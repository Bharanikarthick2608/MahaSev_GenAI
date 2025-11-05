// Workforce Allocation Dashboard JavaScript

const WORKFORCE_API_BASE = '/api/workforce';
let currentWorkforceDistrict = 'all';
let allWorkforceDistricts = [];
let allWorkforceRoleData = [];

// Initialize workforce dashboard
window.initializeWorkforce = function() {
    console.log('Initializing workforce dashboard...');
    
    loadWorkforceDistricts();
    loadWorkforceMetrics();
    loadWorkforceCapacitySummary();
    loadWorkforceDistrictSummary();
    
    // Setup district filter
    const districtFilter = document.getElementById('workforceDistrictFilter');
    if (districtFilter) {
        districtFilter.addEventListener('change', function(e) {
            currentWorkforceDistrict = e.target.value;
            loadWorkforceCapacitySummary();
            loadWorkforceDistrictSummary();
        });
    }

    // Setup table search
    const searchTable = document.getElementById('workforceSearchTable');
    if (searchTable) {
        searchTable.addEventListener('input', function(e) {
            filterWorkforceTable(e.target.value);
        });
    }
};

// Load list of districts
async function loadWorkforceDistricts() {
    try {
        const response = await fetch(`${WORKFORCE_API_BASE}/capacity/districts`);
        const data = await response.json();
        allWorkforceDistricts = data.districts;
        
        const select = document.getElementById('workforceDistrictFilter');
        if (select) {
            select.innerHTML = '<option value="all">All Districts</option>';
            allWorkforceDistricts.forEach(district => {
                const option = document.createElement('option');
                option.value = district;
                option.textContent = district;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading workforce districts:', error);
    }
}

// Load main metrics
async function loadWorkforceMetrics() {
    try {
        const response = await fetch(`${WORKFORCE_API_BASE}/capacity/metrics`);
        const data = await response.json();
        
        const totalDeployed = document.getElementById('workforceTotalDeployed');
        if (totalDeployed) {
            totalDeployed.textContent = formatNumber(data.total_deployed);
        }
        
        const criticalShortfall = document.getElementById('workforceCriticalShortfall');
        if (criticalShortfall) {
            criticalShortfall.textContent = data.critical_shortfall_alerts;
        }
        
        // Show badge if shortfall exists
        const badge = document.getElementById('workforceShortfallBadge');
        if (badge) {
            if (data.critical_shortfall_alerts > 0) {
                badge.style.display = 'flex';
                badge.textContent = data.critical_shortfall_alerts;
            } else {
                badge.style.display = 'none';
            }
        }
        
        const highestAvailability = document.getElementById('workforceHighestAvailability');
        if (highestAvailability) {
            highestAvailability.textContent = data.highest_availability_role;
        }
        
        // Format deployment time
        const avgDeploymentTime = document.getElementById('workforceAvgDeploymentTime');
        if (avgDeploymentTime) {
            const hours = Math.floor(data.average_deployment_time_hours);
            const minutes = Math.round((data.average_deployment_time_hours - hours) * 60);
            avgDeploymentTime.textContent = `${hours} hr ${minutes} min`;
        }
    } catch (error) {
        console.error('Error loading workforce metrics:', error);
    }
}

// Load capacity summary
async function loadWorkforceCapacitySummary() {
    try {
        const response = await fetch(`${WORKFORCE_API_BASE}/capacity/summary`);
        const data = await response.json();
        
        allWorkforceRoleData = data.Top_Categories;
        renderWorkforceRoleBreakdown(data.Top_Categories);
    } catch (error) {
        console.error('Error loading workforce capacity summary:', error);
        const container = document.getElementById('workforceRoleBreakdown');
        if (container) {
            container.innerHTML = '<div class="error-message">Error loading capacity data</div>';
        }
    }
}

// Render role breakdown
function renderWorkforceRoleBreakdown(categories) {
    const container = document.getElementById('workforceRoleBreakdown');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (currentWorkforceDistrict !== 'all') {
        // Filter by district
        loadWorkforceDistrictDetails(currentWorkforceDistrict).then(districtData => {
            renderWorkforceDistrictRoles(container, districtData);
        });
    } else {
        // Show all categories
        categories.forEach(category => {
            const roleDiv = document.createElement('div');
            roleDiv.className = 'workforce-role-item';
            
            const availablePct = category.total > 0 ? 
                Math.round((category.available / category.total) * 100) : 0;
            const deployedPct = category.total > 0 ? 
                Math.round((category.deployed / category.total) * 100) : 0;
            
            roleDiv.innerHTML = `
                <div class="role-name">${category.role}</div>
                <div class="role-stats">
                    <span>Available: <strong>${formatNumber(category.available)}</strong> / ${formatNumber(category.total)}</span>
                    <span>Deployed: <strong>${formatNumber(category.deployed)}</strong></span>
                </div>
                <div class="workforce-progress-bar">
                    <div class="workforce-progress-fill" style="width: ${availablePct}%">
                        ${availablePct}%
                    </div>
                </div>
                <small class="availability-rate">Availability Rate: ${availablePct}%</small>
            `;
            container.appendChild(roleDiv);
        });
    }
}

// Load district details
async function loadWorkforceDistrictDetails(districtName) {
    try {
        const response = await fetch(`${WORKFORCE_API_BASE}/capacity/district/${encodeURIComponent(districtName)}`);
        return await response.json();
    } catch (error) {
        console.error('Error loading workforce district details:', error);
        return [];
    }
}

// Render district-specific roles
function renderWorkforceDistrictRoles(container, districtData) {
    districtData.forEach(role => {
        const roleDiv = document.createElement('div');
        roleDiv.className = 'workforce-role-item';
        
        const availablePct = role.total > 0 ? 
            Math.round((role.available / role.total) * 100) : 0;
        
        roleDiv.innerHTML = `
            <div class="role-name">${role.role}</div>
            <div class="role-stats">
                <span>Available: <strong>${formatNumber(role.available)}</strong> / ${formatNumber(role.total)}</span>
                <span>Deployed: <strong>${formatNumber(role.deployed)}</strong></span>
            </div>
            <div class="workforce-progress-bar">
                <div class="workforce-progress-fill" style="width: ${availablePct}%">
                    ${availablePct}%
                </div>
            </div>
            <small class="availability-rate">Availability Rate: ${availablePct}%</small>
        `;
        container.appendChild(roleDiv);
    });
}

// Load district summary table
async function loadWorkforceDistrictSummary() {
    try {
        const response = await fetch(`${WORKFORCE_API_BASE}/capacity/district-summary`);
        const data = await response.json();
        
        renderWorkforceDistrictTable(data);
    } catch (error) {
        console.error('Error loading workforce district summary:', error);
        const tbody = document.getElementById('workforceDistrictTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6" class="error-cell">Error loading district data</td></tr>';
        }
    }
}

// Render district table
function renderWorkforceDistrictTable(districts) {
    const tbody = document.getElementById('workforceDistrictTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    districts.forEach(district => {
        const row = document.createElement('tr');
        row.setAttribute('data-district', district.district.toLowerCase());
        
        const shortfallBadge = district.police_safety_shortfall ? 
            '<span class="workforce-badge badge-yes">Yes</span>' : 
            '<span class="workforce-badge badge-no">No</span>';
        
        row.innerHTML = `
            <td><strong>${district.district}</strong></td>
            <td><span class="workforce-badge badge-warning">${district.active_alerts}</span></td>
            <td>${formatNumber(district.total_available_workforce)}</td>
            <td>
                <div class="workforce-progress-inline">
                    <div class="workforce-progress-bar-small">
                        <div class="workforce-progress-fill-small" style="width: ${district.health_staff_used_pct}%"></div>
                    </div>
                    <span>${district.health_staff_used_pct}%</span>
                </div>
            </td>
            <td>${shortfallBadge}</td>
            <td>
                <button class="workforce-btn-view" onclick="viewWorkforceDistrictDetails('${district.district}')">
                    View Deployment
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Filter table
function filterWorkforceTable(searchTerm) {
    const rows = document.querySelectorAll('#workforceDistrictTableBody tr');
    const term = searchTerm.toLowerCase();
    
    rows.forEach(row => {
        const district = row.getAttribute('data-district');
        if (district && district.includes(term)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// View district details
function viewWorkforceDistrictDetails(districtName) {
    // Set filter to this district
    const districtFilter = document.getElementById('workforceDistrictFilter');
    if (districtFilter) {
        districtFilter.value = districtName;
        currentWorkforceDistrict = districtName;
        loadWorkforceCapacitySummary();
        
        // Scroll to role breakdown
        const roleBreakdown = document.getElementById('workforceRoleBreakdown');
        if (roleBreakdown) {
            roleBreakdown.scrollIntoView({ behavior: 'smooth' });
        }
    }
}

// Format numbers with commas
function formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
}

// Auto-refresh every 30 seconds
setInterval(() => {
    const workforceView = document.getElementById('workforceView');
    if (workforceView && !workforceView.classList.contains('hidden')) {
        loadWorkforceMetrics();
        if (currentWorkforceDistrict === 'all') {
            loadWorkforceCapacitySummary();
        }
        loadWorkforceDistrictSummary();
    }
}, 30000);

// Initialize on page load if view is visible
document.addEventListener('DOMContentLoaded', () => {
    const workforceView = document.getElementById('workforceView');
    if (workforceView && !workforceView.classList.contains('hidden')) {
        window.initializeWorkforce();
    }
});


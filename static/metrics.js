// Metrics Dashboard JavaScript

let allDistrictsData = [];
let currentMode = 'all';

// Make initializeMetrics available globally
window.initializeMetrics = async function() {
    console.log('Initializing metrics dashboard...');
    try {
        await loadDistrictsForNewMetrics();
        setupNewMetricsEventListeners();
        console.log('Metrics dashboard initialized successfully');
    } catch (error) {
        console.error('Error initializing metrics dashboard:', error);
    }
};

// Initialize on page load (if metrics view is already visible)
document.addEventListener('DOMContentLoaded', () => {
    const metricsView = document.getElementById('metricsView');
    if (metricsView && !metricsView.classList.contains('hidden')) {
        window.initializeMetrics();
    }
});

// Load districts for new metrics page
async function loadDistrictsForNewMetrics() {
    try {
        const response = await fetch('/api/chatbot/districts');
        const data = await response.json();
        
        if (data.success && data.districts) {
            const districtSelect = document.getElementById('metricsDistrictSelect');
            
            if (districtSelect) {
                data.districts.forEach(district => {
                    const option = document.createElement('option');
                    option.value = district;
                    option.textContent = district;
                    districtSelect.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('Error loading districts:', error);
    }
}

// Setup event listeners for new metrics page
function setupNewMetricsEventListeners() {
    const districtSelect = document.getElementById('metricsDistrictSelect');
    const calculateBtn = document.getElementById('calculateMetricsBtn');
    
    if (districtSelect) {
        districtSelect.addEventListener('change', (e) => {
            if (calculateBtn) {
                calculateBtn.disabled = !e.target.value;
            }
        });
    }
    
    if (calculateBtn) {
        calculateBtn.addEventListener('click', async () => {
            const district = districtSelect?.value;
            if (district) {
                await calculateAndDisplayMetrics(district);
            }
        });
    }
}

// Calculate and display metrics for selected district
async function calculateAndDisplayMetrics(district) {
    // Show loading overlay
    showCalculatingOverlay();
    
    try {
        const response = await fetch(`/api/chatbot/metrics/${encodeURIComponent(district)}`);
        const data = await response.json();
        
        hideCalculatingOverlay();
        
        if (data.success && data.metrics) {
            displayMetricsResults(district, data.metrics);
        } else {
            alert('Failed to calculate metrics. Please try again.');
        }
    } catch (error) {
        hideCalculatingOverlay();
        console.error('Error calculating metrics:', error);
        alert('Error calculating metrics. Please try again.');
    }
}

// Display metrics results
function displayMetricsResults(district, metrics) {
    // Show results section
    const resultsSection = document.getElementById('metricsResultsSection');
    const resultsGrid = document.getElementById('metricsResultsGrid');
    const resultsDistrictName = document.getElementById('resultsDistrictName');
    
    if (!resultsSection || !resultsGrid || !resultsDistrictName) return;
    
    resultsDistrictName.textContent = district;
    resultsSection.style.display = 'block';
    
    // Create result cards
    resultsGrid.innerHTML = `
        <div class="result-card">
            <h4>P-Score</h4>
            <div class="result-value">${formatScore(metrics.p_score)}</div>
            <div class="result-label">${metrics.priority_level || 'N/A'} Priority</div>
        </div>
        <div class="result-card" style="background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);">
            <h4>HVI</h4>
            <div class="result-value">${formatScore(metrics.hvi_score)}</div>
            <div class="result-label">Health Vulnerability</div>
        </div>
        <div class="result-card" style="background: linear-gradient(135deg, #f57c00 0%, #e65100 100%);">
            <h4>ISS</h4>
            <div class="result-value">${formatScore(metrics.iss_score)}</div>
            <div class="result-label">Infrastructure Strain</div>
        </div>
        <div class="result-card" style="background: linear-gradient(135deg, #7b1fa2 0%, #6a1b9a 100%);">
            <h4>RCS</h4>
            <div class="result-value">${formatScore(metrics.rcs_score)}</div>
            <div class="result-label">Resource Contention</div>
        </div>
        <div class="result-card" style="background: linear-gradient(135deg, #388e3c 0%, #2e7d32 100%);">
            <h4>SEL</h4>
            <div class="result-value">${formatScore(metrics.sel_index, 2)}</div>
            <div class="result-label">Service Equity Lag</div>
        </div>
        <div class="result-card" style="background: linear-gradient(135deg, #c62828 0%, #b71c1c 100%);">
            <h4>Health-Worker Gap</h4>
            <div class="result-value">${formatScore(metrics.health_worker_capacity_gap)}</div>
            <div class="result-label">Capacity Gap Score</div>
        </div>
    `;
    
    // Display recommendations
    const recommendationsSection = document.getElementById('recommendationsSection');
    const recommendationsList = document.getElementById('recommendationsListNew');
    
    if (metrics.recommendations && metrics.recommendations.length > 0) {
        recommendationsSection.style.display = 'block';
        recommendationsList.innerHTML = metrics.recommendations.map(rec => 
            `<li>${escapeHtml(rec)}</li>`
        ).join('');
    } else {
        recommendationsSection.style.display = 'none';
    }
    
    // Display issues
    const issuesSection = document.getElementById('issuesSection');
    const issuesList = document.getElementById('issuesList');
    
    if (metrics.all_issues && metrics.all_issues.length > 0) {
        issuesSection.style.display = 'block';
        issuesList.innerHTML = metrics.all_issues.slice(0, 10).map(issue => 
            `<li>${escapeHtml(issue)}</li>`
        ).join('');
    } else {
        issuesSection.style.display = 'none';
    }
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Show calculating overlay
function showCalculatingOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'calculatingOverlay';
    overlay.className = 'calculating-overlay';
    overlay.innerHTML = `
        <div class="calculating-spinner">
            <div class="spinner-icon"></div>
            <div class="calculating-text">Calculating Metrics...</div>
        </div>
    `;
    document.body.appendChild(overlay);
}

// Hide calculating overlay
function hideCalculatingOverlay() {
    const overlay = document.getElementById('calculatingOverlay');
    if (overlay) {
        overlay.remove();
    }
}

// Setup event listeners
function setupMetricsEventListeners() {
    // Mode buttons
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.getAttribute('data-mode');
            switchMode(mode);
        });
    });
    
    // Single district select
    const singleSelect = document.getElementById('singleDistrictSelect');
    if (singleSelect) {
        singleSelect.addEventListener('change', (e) => {
            if (e.target.value) {
                loadSingleDistrictMetrics(e.target.value);
            }
        });
    }
    
    // Compare district selects
    const compareSelect1 = document.getElementById('compareDistrict1');
    const compareSelect2 = document.getElementById('compareDistrict2');
    
    if (compareSelect1 && compareSelect2) {
        const compareHandler = () => {
            const dist1 = compareSelect1.value;
            const dist2 = compareSelect2.value;
            if (dist1 && dist2) {
                loadCompareMetrics(dist1, dist2);
            }
        };
        
        compareSelect1.addEventListener('change', compareHandler);
        compareSelect2.addEventListener('change', compareHandler);
    }
}

// Switch view mode
function switchMode(mode) {
    currentMode = mode;
    
    // Update mode buttons
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-mode') === mode);
    });
    
    // Show/hide controls
    const singleControl = document.getElementById('singleDistrictControl');
    const compareControl = document.getElementById('compareDistrictsControl');
    
    if (singleControl) singleControl.style.display = mode === 'single' ? 'block' : 'none';
    if (compareControl) compareControl.style.display = mode === 'compare' ? 'block' : 'none';
    
    // Show/hide views
    const allView = document.getElementById('allDistrictsView');
    const singleView = document.getElementById('singleDistrictView');
    const compareView = document.getElementById('compareDistrictsView');
    
    if (allView) allView.classList.toggle('hidden', mode !== 'all');
    if (singleView) singleView.classList.toggle('hidden', mode !== 'single');
    if (compareView) compareView.classList.toggle('hidden', mode !== 'compare');
    
    // Reset selections
    const singleSelect = document.getElementById('singleDistrictSelect');
    const compareSelect1 = document.getElementById('compareDistrict1');
    const compareSelect2 = document.getElementById('compareDistrict2');
    
    if (mode === 'all') {
        if (singleSelect) singleSelect.value = '';
        if (compareSelect1) compareSelect1.value = '';
        if (compareSelect2) compareSelect2.value = '';
    }
}

// Load all metrics
async function loadAllMetrics() {
    const tableBody = document.getElementById('metricsTableBody');
    if (!tableBody) {
        console.error('Metrics table body not found');
        return;
    }
    
    tableBody.innerHTML = '<tr><td colspan="8" class="loading-state">Loading metrics...</td></tr>';
    
    try {
        console.log('Fetching metrics from /api/metrics/all...');
        const response = await fetch('/api/metrics/all');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Metrics data received:', data);
        
        if (data.success && data.districts && data.districts.length > 0) {
            allDistrictsData = data.districts;
            console.log(`Rendering ${data.districts.length} districts`);
            renderAllMetricsTable(data.districts);
        } else {
            console.warn('No districts data in response:', data);
            tableBody.innerHTML = '<tr><td colspan="8" class="loading-state">No metrics data available. Please check if districts exist in the database.</td></tr>';
        }
    } catch (error) {
        console.error('Error loading metrics:', error);
        tableBody.innerHTML = `<tr><td colspan="8" class="loading-state">Error loading metrics: ${error.message}. Please check the console for details.</td></tr>`;
    }
}

// Render all metrics table
function renderAllMetricsTable(districts) {
    const tableBody = document.getElementById('metricsTableBody');
    if (!tableBody) return;
    
    if (districts.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="8" class="loading-state">No districts found</td></tr>';
        return;
    }
    
    // Sort by P-Score descending
    const sortedDistricts = [...districts].sort((a, b) => b.p_score - a.p_score);
    
    tableBody.innerHTML = sortedDistricts.map(district => {
        const priorityClass = district.priority_level.toLowerCase();
        const pScoreClass = getScoreClass(district.p_score);
        const hviClass = getScoreClass(district.hvi_score);
        const issClass = getScoreClass(district.iss_score);
        const rcsClass = getScoreClass(district.rcs_score);
        
        return `
            <tr>
                <td><strong>${escapeHtml(district.district)}</strong></td>
                <td class="score-cell ${pScoreClass}">${formatScore(district.p_score)}</td>
                <td class="score-cell ${hviClass}">${formatScore(district.hvi_score)}</td>
                <td class="score-cell ${issClass}">${formatScore(district.iss_score)}</td>
                <td class="score-cell ${rcsClass}">${formatScore(district.rcs_score)}</td>
                <td>${formatScore(district.sel_index, 2)}</td>
                <td><span class="priority-badge ${priorityClass}">${district.priority_level}</span></td>
                <td>
                    <button class="action-btn" onclick="viewDistrictDetails('${escapeHtml(district.district)}')">View Details</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Load single district metrics
async function loadSingleDistrictMetrics(district) {
    const container = document.getElementById('singleDistrictMetrics');
    if (!container) return;
    
    container.innerHTML = '<div class="loading-state">Loading district metrics...</div>';
    
    try {
        const response = await fetch(`/api/chatbot/metrics/${encodeURIComponent(district)}`);
        const data = await response.json();
        
        if (data.success && data.metrics) {
            renderSingleDistrict(data.district, data.metrics);
        } else {
            container.innerHTML = '<div class="loading-state">No metrics found for this district</div>';
        }
    } catch (error) {
        console.error('Error loading district metrics:', error);
        container.innerHTML = '<div class="loading-state">Error loading metrics. Please try again.</div>';
    }
}

// Render single district view
function renderSingleDistrict(district, metrics) {
    const container = document.getElementById('singleDistrictMetrics');
    if (!container) return;
    
    const recommendations = metrics.recommendations || [];
    
    container.innerHTML = `
        <div class="district-metric-card">
            <h3>P-Score</h3>
            <div class="district-metric-value">${formatScore(metrics.p_score)}</div>
            <div class="district-metric-label">Priority Level: ${metrics.priority_level}</div>
            ${recommendations.length > 0 ? `
                <div class="recommendations-section">
                    <h4>Recommendations</h4>
                    <ul class="recommendations-list">
                        ${recommendations.map(rec => `<li>${escapeHtml(rec)}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        </div>
        
        <div class="district-metric-card" style="background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);">
            <h3>HVI - Health Vulnerability Index</h3>
            <div class="district-metric-value">${formatScore(metrics.hvi_score)}</div>
            <div class="district-metric-label">Health Vulnerability Score</div>
        </div>
        
        <div class="district-metric-card" style="background: linear-gradient(135deg, #f57c00 0%, #e65100 100%);">
            <h3>ISS - Infrastructure Strain Score</h3>
            <div class="district-metric-value">${formatScore(metrics.iss_score)}</div>
            <div class="district-metric-label">Infrastructure Strain Score</div>
        </div>
        
        <div class="district-metric-card" style="background: linear-gradient(135deg, #7b1fa2 0%, #6a1b9a 100%);">
            <h3>RCS - Resource Contention Score</h3>
            <div class="district-metric-value">${formatScore(metrics.rcs_score)}</div>
            <div class="district-metric-label">Resource Contention Score</div>
        </div>
        
        <div class="district-metric-card" style="background: linear-gradient(135deg, #388e3c 0%, #2e7d32 100%);">
            <h3>SEL - Service Equity Lag Index</h3>
            <div class="district-metric-value">${formatScore(metrics.sel_index, 2)}</div>
            <div class="district-metric-label">Service Equity Lag Index</div>
        </div>
        
        <div class="district-metric-card" style="background: linear-gradient(135deg, #c62828 0%, #b71c1c 100%);">
            <h3>Health-Worker Capacity Gap</h3>
            <div class="district-metric-value">${formatScore(metrics.health_worker_capacity_gap)}</div>
            <div class="district-metric-label">Cross-Sectoral Gap Indicator</div>
        </div>
    `;
}

// Load compare metrics
async function loadCompareMetrics(district1, district2) {
    const container = document.getElementById('compareDistrictsMetrics');
    if (!container) return;
    
    container.innerHTML = '<div class="loading-state">Loading comparison...</div>';
    
    try {
        const [resp1, resp2] = await Promise.all([
            fetch(`/api/chatbot/metrics/${encodeURIComponent(district1)}`),
            fetch(`/api/chatbot/metrics/${encodeURIComponent(district2)}`)
        ]);
        
        const data1 = await resp1.json();
        const data2 = await resp2.json();
        
        if (data1.success && data2.success) {
            renderCompareView(district1, data1.metrics, district2, data2.metrics);
        } else {
            container.innerHTML = '<div class="loading-state">Error loading comparison data</div>';
        }
    } catch (error) {
        console.error('Error loading comparison:', error);
        container.innerHTML = '<div class="loading-state">Error loading comparison. Please try again.</div>';
    }
}

// Render compare view
function renderCompareView(district1, metrics1, district2, metrics2) {
    const container = document.getElementById('compareDistrictsMetrics');
    if (!container) return;
    
    const metrics = ['p_score', 'hvi_score', 'iss_score', 'rcs_score', 'sel_index', 'health_worker_capacity_gap'];
    const metricLabels = {
        'p_score': 'P-Score',
        'hvi_score': 'HVI',
        'iss_score': 'ISS',
        'rcs_score': 'RCS',
        'sel_index': 'SEL',
        'health_worker_capacity_gap': 'Health-Worker Gap'
    };
    
    let comparisonSummary = '';
    const differences = [];
    
    metrics.forEach(metric => {
        const val1 = metrics1[metric] || 0;
        const val2 = metrics2[metric] || 0;
        const diff = val1 - val2;
        
        if (Math.abs(diff) > 0.1) {
            const higher = diff > 0 ? district1 : district2;
            differences.push(`${metricLabels[metric]}: ${higher} has ${Math.abs(diff).toFixed(2)} higher score`);
        }
    });
    
    if (differences.length > 0) {
        comparisonSummary = `
            <div class="comparison-summary">
                <h4>Key Differences</h4>
                <p>${differences.join('; ')}</p>
            </div>
        `;
    }
    
    container.innerHTML = `
        <div class="compare-card">
            <h3>${escapeHtml(district1)}</h3>
            <div class="compare-metrics-grid">
                ${metrics.map(metric => `
                    <div class="compare-metric-item">
                        <span class="compare-metric-label">${metricLabels[metric]}</span>
                        <span class="compare-metric-value">${formatScore(metrics1[metric] || 0, metric === 'sel_index' ? 2 : 1)}</span>
                    </div>
                `).join('')}
            </div>
            <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #e9ecef;">
                <div class="compare-metric-item">
                    <span class="compare-metric-label">Priority Level</span>
                    <span class="priority-badge ${(metrics1.priority_level || 'LOW').toLowerCase()}">${metrics1.priority_level || 'LOW'}</span>
                </div>
            </div>
        </div>
        
        <div class="compare-card">
            <h3>${escapeHtml(district2)}</h3>
            <div class="compare-metrics-grid">
                ${metrics.map(metric => `
                    <div class="compare-metric-item">
                        <span class="compare-metric-label">${metricLabels[metric]}</span>
                        <span class="compare-metric-value">${formatScore(metrics2[metric] || 0, metric === 'sel_index' ? 2 : 2)}</span>
                    </div>
                `).join('')}
            </div>
            <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #e9ecef;">
                <div class="compare-metric-item">
                    <span class="compare-metric-label">Priority Level</span>
                    <span class="priority-badge ${(metrics2.priority_level || 'LOW').toLowerCase()}">${metrics2.priority_level || 'LOW'}</span>
                </div>
            </div>
        </div>
        
        ${comparisonSummary}
    `;
}

// View district details (from table)
window.viewDistrictDetails = function(district) {
    switchMode('single');
    const singleSelect = document.getElementById('singleDistrictSelect');
    if (singleSelect) {
        singleSelect.value = district;
        loadSingleDistrictMetrics(district);
    }
};

// Helper functions
function formatScore(score, decimals = 1) {
    if (score === null || score === undefined) return 'N/A';
    return Number(score).toFixed(decimals);
}

function getScoreClass(score) {
    if (score >= 7) return 'high';
    if (score >= 4) return 'medium';
    return 'low';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export for dashboard.js
window.initializeMetrics = initializeMetrics;


// AI Policy Sandbox JavaScript

const SCENARIOS = {
    traffic: {
        name: "Traffic & Infrastructure Policy",
        inputs: [
            { label: "Congestion Tax", value: "₹50/day" },
            { label: "Public Transport Subsidy", value: "50%" },
            { label: "Scope", value: "Pune Central Business District (CBD)" },
            { label: "Start Date", value: "6 months from now" }
        ],
        outputs: [
            { label: "Private Vehicle Traffic (Peak Hours)", value: "↓ 18%", type: "positive" },
            { label: "Public Transport Ridership", value: "↑ 25%", type: "positive" },
            { label: "Minor Accidents", value: "↓ 12%", type: "positive" }
        ],
        analysis: [
            { text: "30% increase in bus maintenance demand", alert: false },
            { text: "10% temporary backlog in pass renewals", alert: true },
            { text: "15 maintenance workers shifted from Road Maintenance → Transport", alert: false }
        ],
        resourceShifts: [
            { from: "Road Maintenance", to: "Transport", workers: 15 }
        ],
        risk: {
            level: "medium",
            title: "Equity Risk",
            description: "Potential sentiment backlash from low-income commuters who may face higher effective costs despite subsidies."
        },
        chartType: "line",
        chartData: {
            labels: ['Month 1', 'Month 2', 'Month 3', 'Month 4', 'Month 5', 'Month 6'],
            datasets: [
                {
                    label: 'Private Vehicle Volume',
                    data: [100, 95, 88, 85, 83, 82],
                    color: '#ef4444'
                },
                {
                    label: 'Public Transport Ridership',
                    data: [100, 108, 115, 120, 123, 125],
                    color: '#10b981'
                }
            ]
        }
    },
    health: {
        name: "Public Health & Service Delivery Policy",
        inputs: [
            { label: "Delegation", value: "Birth Certificate Authority → 450 CHCs" },
            { label: "Training", value: "1 Admin Staff/CHC" },
            { label: "Target", value: "Reduce processing time by 50%" }
        ],
        outputs: [
            { label: "Processing Speed (within 21-day window)", value: "↑ 45%", type: "positive" },
            { label: "Citizen Travel Time", value: "↓ 60%", type: "positive" },
            { label: "District HQ Wait Time", value: "↓ 7%", type: "positive" }
        ],
        analysis: [
            { text: "Need 300 tablets/laptops for CHC admins", alert: false },
            { text: "15% CHCs lack adequate bandwidth", alert: true },
            { text: "Estimated ₹2.5 Cr infrastructure investment required", alert: false }
        ],
        resourceShifts: [
            { from: "District HQ Staff", to: "CHC Training", workers: 25 }
        ],
        risk: {
            level: "medium",
            title: "Data Integrity",
            description: "+8% error rate expected in first 3 months due to staff learning curve and system adjustments."
        },
        chartType: "bar",
        chartData: {
            labels: ['Before Policy', 'After Policy'],
            datasets: [
                {
                    label: 'Avg. Processing Time (days)',
                    data: [30, 15],
                    color: '#667eea'
                }
            ]
        }
    },
    revenue: {
        name: "Revenue & Citizen Compliance Policy",
        inputs: [
            { label: "Amnesty Period", value: "3 months" },
            { label: "Penalty/Interest Waiver", value: "50%" },
            { label: "Target", value: "Property Tax defaulters (2+ years overdue)" }
        ],
        outputs: [
            { label: "Defaulters Paying During Scheme", value: "↑ 35%", type: "positive" },
            { label: "Tax Collected", value: "₹450 Cr (vs ₹150 Cr baseline)", type: "positive" },
            { label: "Collection Target Achievement", value: "90% (₹450 Cr / ₹500 Cr)", type: "positive" }
        ],
        analysis: [
            { text: "150% surge in foot traffic near deadline", alert: true },
            { text: "40 Education Dept. staff temporarily redeployed to Revenue", alert: false },
            { text: "Online payment portal traffic: 300% increase", alert: false }
        ],
        resourceShifts: [
            { from: "Education Department", to: "Revenue Collection", workers: 40 }
        ],
        risk: {
            level: "medium",
            title: "Moral Hazard",
            description: "Long-term compliance may decrease by ~5% post-scheme as citizens anticipate future amnesty programs."
        },
        chartType: "gauge",
        chartData: {
            value: 450,
            target: 500,
            label: "Tax Collection (₹ Cr)"
        }
    }
};

let currentScenario = 'traffic';
let simulationRunning = false;
let resultsVisible = false;

// Initialize Policy Sandbox
window.initializePolicySandbox = function() {
    console.log('Initializing Policy Sandbox...');
    
    const scenarioSelect = document.getElementById('scenarioSelect');
    const scenarioContent = document.getElementById('scenarioContent');
    
    console.log('scenarioSelect:', scenarioSelect);
    console.log('scenarioContent:', scenarioContent);
    
    if (scenarioSelect) {
        // Remove existing event listeners by cloning
        const newSelect = scenarioSelect.cloneNode(true);
        scenarioSelect.parentNode.replaceChild(newSelect, scenarioSelect);
        
        newSelect.addEventListener('change', (e) => {
            console.log('Scenario changed to:', e.target.value);
            currentScenario = e.target.value;
            resultsVisible = false;
            loadScenario(currentScenario);
        });
        
        // Load initial scenario with a small delay to ensure DOM is ready
        setTimeout(() => {
            console.log('Loading initial scenario:', currentScenario);
            loadScenario(currentScenario);
        }, 100);
    } else {
        console.error('scenarioSelect element not found!');
    }
};

// Load scenario content
function loadScenario(scenarioKey) {
    console.log('loadScenario called with:', scenarioKey);
    const scenario = SCENARIOS[scenarioKey];
    const contentDiv = document.getElementById('scenarioContent');
    
    console.log('scenario:', scenario);
    console.log('contentDiv:', contentDiv);
    
    if (!contentDiv) {
        console.error('scenarioContent div not found!');
        return;
    }
    
    if (!scenario) {
        console.error('Scenario not found:', scenarioKey);
        return;
    }
    
    // Build the scenario HTML
    contentDiv.innerHTML = `
        <!-- Policy Inputs Section -->
        <section class="policy-inputs-section">
            <h2 class="section-title">
                <span class="section-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 20h9"></path>
                        <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                    </svg>
                </span>
                Policy Inputs & Conditions
            </h2>
            <div class="policy-inputs-grid">
                ${scenario.inputs.map(input => `
                    <div class="input-card">
                        <label class="input-label">${input.label}</label>
                        <div class="input-value">${input.value}</div>
                    </div>
                `).join('')}
            </div>
            <button class="run-simulation-btn" id="runSimulationBtn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
                Run Simulation
            </button>
        </section>
        
        <!-- Results Section (initially hidden) -->
        <div id="resultsContainer" style="display: none;">
            <!-- Predicted Output Section -->
            <section class="predicted-output-section results-section">
                <h2 class="section-title">
                    <span class="section-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                        </svg>
                    </span>
                    Predicted AI Output
                </h2>
                <div class="output-metrics-grid">
                    ${scenario.outputs.map(output => `
                        <div class="metric-card ${output.type}">
                            <div class="metric-value">${output.value}</div>
                            <div class="metric-label">${output.label}</div>
                        </div>
                    `).join('')}
                </div>
                <div class="chart-container">
                    <h3 class="chart-title">Trend Visualization</h3>
                    <canvas id="scenarioChart" width="800" height="400"></canvas>
                </div>
            </section>
            
            <!-- Analysis Section -->
            <section class="analysis-section results-section">
                <h2 class="section-title">
                    <span class="section-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="12" y1="1" x2="12" y2="23"></line>
                            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                        </svg>
                    </span>
                    Resource Analysis & Forecasted Shifts
                </h2>
                <div class="analysis-grid">
                    ${scenario.analysis.map(item => `
                        <div class="analysis-card ${item.alert ? 'alert' : ''}">
                            <svg class="analysis-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                ${item.alert 
                                    ? '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>'
                                    : '<polyline points="20 6 9 17 4 12"></polyline>'
                                }
                            </svg>
                            <span>${item.text}</span>
                        </div>
                    `).join('')}
                </div>
                
                <table class="resource-table">
                    <thead>
                        <tr>
                            <th>From Department</th>
                            <th></th>
                            <th>To Department</th>
                            <th>Workers</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${scenario.resourceShifts.map(shift => `
                            <tr>
                                <td>${shift.from}</td>
                                <td class="resource-arrow">→</td>
                                <td>${shift.to}</td>
                                <td><strong>${shift.workers}</strong></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </section>
            
            <!-- Risk Assessment Section -->
            <section class="risk-assessment-section results-section">
                <h2 class="section-title">
                    <span class="section-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                        </svg>
                    </span>
                    Risk Assessment
                </h2>
                <span class="risk-level-badge ${scenario.risk.level}">${scenario.risk.level} Risk</span>
                <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 12px;">${scenario.risk.title}</h3>
                <p class="risk-description">${scenario.risk.description}</p>
                <div class="chart-container">
                    <h3 class="chart-title">Risk Impact Visualization</h3>
                    <canvas id="riskChart" width="600" height="300"></canvas>
                </div>
            </section>
        </div>
    `;
    
    // Add event listener to run simulation button
    const runBtn = document.getElementById('runSimulationBtn');
    if (runBtn) {
        runBtn.addEventListener('click', () => runSimulation(scenarioKey));
    }
    
    // If results were visible, show them again
    if (resultsVisible) {
        setTimeout(() => {
            showResults(scenarioKey);
        }, 100);
    }
}

// Run simulation
async function runSimulation(scenarioKey) {
    if (simulationRunning) return;
    
    simulationRunning = true;
    const btn = document.getElementById('runSimulationBtn');
    
    // Update button state
    btn.disabled = true;
    btn.innerHTML = `
        <div class="spinner"></div>
        Running Predictive Model...
    `;
    
    // Simulate 2-second delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Show results
    showResults(scenarioKey);
    resultsVisible = true;
    
    // Reset button
    btn.disabled = false;
    btn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        Re-run Simulation
    `;
    
    simulationRunning = false;
}

// Show results
function showResults(scenarioKey) {
    const resultsContainer = document.getElementById('resultsContainer');
    if (resultsContainer) {
        resultsContainer.style.display = 'block';
        
        // Scroll to results
        setTimeout(() => {
            resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
        
        // Render charts
        renderScenarioChart(scenarioKey);
        renderRiskChart(scenarioKey);
    }
}

// Render scenario chart
function renderScenarioChart(scenarioKey) {
    const scenario = SCENARIOS[scenarioKey];
    const canvas = document.getElementById('scenarioChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    if (scenario.chartType === 'line') {
        drawLineChart(ctx, canvas, scenario.chartData);
    } else if (scenario.chartType === 'bar') {
        drawBarChart(ctx, canvas, scenario.chartData);
    } else if (scenario.chartType === 'gauge') {
        drawGaugeChart(ctx, canvas, scenario.chartData);
    }
}

// Render risk chart
function renderRiskChart(scenarioKey) {
    const canvas = document.getElementById('riskChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    if (scenarioKey === 'traffic') {
        drawPieChart(ctx, canvas, [
            { label: 'Low Income Areas', value: 60, color: '#ef4444' },
            { label: 'Middle Income Areas', value: 25, color: '#f59e0b' },
            { label: 'High Income Areas', value: 15, color: '#10b981' }
        ]);
    } else if (scenarioKey === 'health') {
        drawPieChart(ctx, canvas, [
            { label: 'Data Entry Errors', value: 70, color: '#ef4444' },
            { label: 'System Faults', value: 20, color: '#f59e0b' },
            { label: 'Network Issues', value: 10, color: '#667eea' }
        ]);
    } else if (scenarioKey === 'revenue') {
        drawBarChart(ctx, canvas, {
            labels: ['Before Scheme', 'During Scheme', 'After Scheme (Projected)'],
            datasets: [{
                label: 'Compliance Rate (%)',
                data: [65, 85, 60],
                color: '#667eea'
            }]
        });
    }
}

// Draw line chart
function drawLineChart(ctx, canvas, data) {
    const width = canvas.width;
    const height = canvas.height;
    const padding = 60;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;
    
    ctx.clearRect(0, 0, width, height);
    
    // Draw axes
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, height - padding);
    ctx.lineTo(width - padding, height - padding);
    ctx.stroke();
    
    // Draw grid lines
    ctx.strokeStyle = '#f3f4f6';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    }
    
    // Draw datasets
    const pointSpacing = chartWidth / (data.labels.length - 1);
    
    data.datasets.forEach((dataset, dsIndex) => {
        ctx.strokeStyle = dataset.color;
        ctx.fillStyle = dataset.color;
        ctx.lineWidth = 3;
        
        // Draw line
        ctx.beginPath();
        dataset.data.forEach((value, i) => {
            const x = padding + i * pointSpacing;
            const y = height - padding - (value / 130 * chartHeight);
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.stroke();
        
        // Draw points
        dataset.data.forEach((value, i) => {
            const x = padding + i * pointSpacing;
            const y = height - padding - (value / 130 * chartHeight);
            
            ctx.beginPath();
            ctx.arc(x, y, 5, 0, Math.PI * 2);
            ctx.fill();
        });
    });
    
    // Draw labels
    ctx.fillStyle = '#666666';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    data.labels.forEach((label, i) => {
        const x = padding + i * pointSpacing;
        ctx.fillText(label, x, height - padding + 25);
    });
    
    // Draw legend
    let legendX = padding;
    data.datasets.forEach((dataset, i) => {
        ctx.fillStyle = dataset.color;
        ctx.fillRect(legendX, padding - 30, 20, 12);
        
        ctx.fillStyle = '#333333';
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(dataset.label, legendX + 25, padding - 20);
        
        legendX += ctx.measureText(dataset.label).width + 50;
    });
}

// Draw bar chart
function drawBarChart(ctx, canvas, data) {
    const width = canvas.width;
    const height = canvas.height;
    const padding = 60;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;
    
    ctx.clearRect(0, 0, width, height);
    
    // Draw axes
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, height - padding);
    ctx.lineTo(width - padding, height - padding);
    ctx.stroke();
    
    const barWidth = chartWidth / data.labels.length * 0.6;
    const barSpacing = chartWidth / data.labels.length;
    const maxValue = Math.max(...data.datasets[0].data);
    
    data.datasets[0].data.forEach((value, i) => {
        const barHeight = (value / maxValue) * chartHeight * 0.9;
        const x = padding + i * barSpacing + (barSpacing - barWidth) / 2;
        const y = height - padding - barHeight;
        
        // Draw bar
        const gradient = ctx.createLinearGradient(0, y, 0, height - padding);
        gradient.addColorStop(0, data.datasets[0].color);
        gradient.addColorStop(1, data.datasets[0].color + 'aa');
        
        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, barWidth, barHeight);
        
        // Draw value on top
        ctx.fillStyle = '#333333';
        ctx.font = 'bold 16px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(value, x + barWidth / 2, y - 10);
        
        // Draw label
        ctx.fillStyle = '#666666';
        ctx.font = '12px sans-serif';
        const label = data.labels[i];
        const words = label.split(' ');
        words.forEach((word, wi) => {
            ctx.fillText(word, x + barWidth / 2, height - padding + 20 + wi * 15);
        });
    });
}

// Draw gauge chart
function drawGaugeChart(ctx, canvas, data) {
    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2 + 50;
    const radius = 150;
    
    ctx.clearRect(0, 0, width, height);
    
    // Draw background arc
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 30;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, Math.PI, 2 * Math.PI);
    ctx.stroke();
    
    // Draw progress arc
    const percentage = data.value / data.target;
    const endAngle = Math.PI + (percentage * Math.PI);
    
    const gradient = ctx.createLinearGradient(centerX - radius, 0, centerX + radius, 0);
    gradient.addColorStop(0, '#667eea');
    gradient.addColorStop(1, '#764ba2');
    
    ctx.strokeStyle = gradient;
    ctx.lineWidth = 30;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, Math.PI, endAngle);
    ctx.stroke();
    
    // Draw value text
    ctx.fillStyle = '#333333';
    ctx.font = 'bold 48px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`₹${data.value} Cr`, centerX, centerY - 10);
    
    ctx.font = '18px sans-serif';
    ctx.fillStyle = '#666666';
    ctx.fillText(`Target: ₹${data.target} Cr`, centerX, centerY + 25);
    
    ctx.font = 'bold 24px sans-serif';
    ctx.fillStyle = '#667eea';
    ctx.fillText(`${Math.round(percentage * 100)}%`, centerX, centerY + 55);
}

// Draw pie chart
function drawPieChart(ctx, canvas, data) {
    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2 - 100;
    const centerY = height / 2;
    const radius = 100;
    
    ctx.clearRect(0, 0, width, height);
    
    const total = data.reduce((sum, item) => sum + item.value, 0);
    let currentAngle = -Math.PI / 2;
    
    // Draw pie slices
    data.forEach((item, i) => {
        const sliceAngle = (item.value / total) * 2 * Math.PI;
        
        ctx.fillStyle = item.color;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
        ctx.closePath();
        ctx.fill();
        
        // Draw stroke
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 3;
        ctx.stroke();
        
        currentAngle += sliceAngle;
    });
    
    // Draw legend
    let legendY = 50;
    data.forEach((item) => {
        ctx.fillStyle = item.color;
        ctx.fillRect(width / 2 + 50, legendY, 20, 20);
        
        ctx.fillStyle = '#333333';
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(item.label, width / 2 + 80, legendY + 15);
        
        ctx.fillStyle = '#666666';
        ctx.fillText(`${item.value}%`, width - 80, legendY + 15);
        
        legendY += 35;
    });
}

// Initialize on page load if view is visible
document.addEventListener('DOMContentLoaded', () => {
    const policySandboxView = document.getElementById('policySandboxView');
    if (policySandboxView && !policySandboxView.classList.contains('hidden')) {
        window.initializePolicySandbox();
    }
});


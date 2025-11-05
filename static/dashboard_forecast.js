// Enhanced dashboard.js with all visualizations and AI insights
let forecastChart = null;
let diseaseChart = null;
let wardChart = null;
let trendChart = null;
let correlationChart = null;

// Initialize dashboard on load
window.onload = async () => {
  await loadOverallStats();
  await fetchSeries();
  await loadDataVisualizations();
  
  // Auto-select first series and run forecast
  const select = document.getElementById('seriesSelect');
  if (select.options.length > 0) {
    select.selectedIndex = 0;
    setTimeout(runForecast, 300);
  }
};

// Load overall statistics
async function loadOverallStats() {
  try {
    const res = await fetch('/api/overall-stats');
    if (res.status === 503) {
      showDataUnavailableMessage();
      return;
    }
    const data = await res.json();
    
    document.getElementById('statTotalCases').textContent = data.total_cases.toLocaleString();
    document.getElementById('statAvgWeekly').textContent = Math.round(data.avg_weekly_cases).toLocaleString();
    document.getElementById('statWards').textContent = data.unique_wards;
    document.getElementById('statDiseases').textContent = data.unique_diseases;
  } catch (error) {
    console.error('Failed to load overall stats:', error);
    showDataUnavailableMessage();
  }
}

// Fetch available series
async function fetchSeries() {
  try {
    const res = await fetch('/api/series');
    const data = await res.json();
    const select = document.getElementById('seriesSelect');
    select.innerHTML = '';
    data.series.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s;
      opt.text = s;
      select.appendChild(opt);
    });
  } catch (error) {
    console.error('Failed to fetch series:', error);
  }
}

// Load data visualizations
async function loadDataVisualizations() {
  await loadDiseaseDistribution();
  await loadWardAnalysis();
  await loadTimeTrends();
  await loadCorrelationAnalysis();
}

// Disease Distribution Chart
async function loadDiseaseDistribution() {
  try {
    const res = await fetch('/api/disease-distribution');
    const data = await res.json();
    
    const ctx = document.getElementById('diseaseChart').getContext('2d');
    if (diseaseChart) diseaseChart.destroy();
    
    diseaseChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.diseases,
        datasets: [{
          label: 'Total Cases',
          data: data.total_cases,
          backgroundColor: [
            '#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe',
            '#43e97b', '#fa709a', '#fee140', '#30cfd0', '#a8edea'
          ]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom'
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const value = context.parsed || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value.toLocaleString()} (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  } catch (error) {
    console.error('Failed to load disease distribution:', error);
  }
}

// Ward Analysis Chart
async function loadWardAnalysis() {
  try {
    const res = await fetch('/api/ward-analysis?top_n=10');
    const data = await res.json();
    
    const ctx = document.getElementById('wardChart').getContext('2d');
    if (wardChart) wardChart.destroy();
    
    wardChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.wards,
        datasets: [{
          label: 'Total Cases',
          data: data.total_cases,
          backgroundColor: '#667eea',
          borderColor: '#764ba2',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return value.toLocaleString();
              }
            }
          },
          x: {
            ticks: {
              maxRotation: 45,
              minRotation: 45
            }
          }
        }
      }
    });
  } catch (error) {
    console.error('Failed to load ward analysis:', error);
  }
}

// Time Trends Chart
async function loadTimeTrends() {
  try {
    const res = await fetch('/api/time-trends?period=weekly');
    const data = await res.json();
    
    // Limit to last 52 weeks for readability
    const limit = 52;
    const periods = data.periods.slice(-limit);
    const totalCases = data.total_cases.slice(-limit);
    
    const ctx = document.getElementById('trendChart').getContext('2d');
    if (trendChart) trendChart.destroy();
    
    trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: periods,
        datasets: [{
          label: 'Total Weekly Cases',
          data: totalCases,
          borderColor: '#667eea',
          backgroundColor: 'rgba(102, 126, 234, 0.1)',
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: true
          }
        },
        scales: {
          x: {
            ticks: {
              maxRotation: 45,
              minRotation: 45,
              maxTicksLimit: 20
            }
          },
          y: {
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return value.toLocaleString();
              }
            }
          }
        }
      }
    });
  } catch (error) {
    console.error('Failed to load time trends:', error);
  }
}

// Correlation Analysis Chart
async function loadCorrelationAnalysis() {
  try {
    const res = await fetch('/api/correlations');
    const data = await res.json();
    
    const correlations = data.correlations || {};
    const labels = Object.keys(correlations);
    const values = Object.values(correlations);
    
    if (labels.length === 0) {
      document.getElementById('correlationChart').parentElement.innerHTML = 
        '<div class="loading">No correlation data available</div>';
      return;
    }
    
    const ctx = document.getElementById('correlationChart').getContext('2d');
    if (correlationChart) correlationChart.destroy();
    
    // Create color array based on correlation strength
    const colors = values.map(v => {
      const absV = Math.abs(v);
      if (absV > 0.7) return '#dc3545'; // Strong
      if (absV > 0.4) return '#ffc107'; // Moderate
      return '#6c757d'; // Weak
    });
    
    correlationChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Correlation with New Cases',
          data: values,
          backgroundColor: colors,
          borderColor: colors.map(c => c.replace('0.8', '1')),
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const value = context.parsed.y;
                const strength = Math.abs(value) > 0.7 ? 'Strong' : 
                               Math.abs(value) > 0.4 ? 'Moderate' : 'Weak';
                return `Correlation: ${value.toFixed(3)} (${strength})`;
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: false,
            min: -1,
            max: 1,
            ticks: {
              callback: function(value) {
                return value.toFixed(2);
              }
            }
          },
          x: {
            ticks: {
              maxRotation: 45,
              minRotation: 45
            }
          }
        }
      }
    });
  } catch (error) {
    console.error('Failed to load correlation analysis:', error);
  }
}

// Render Forecast Chart
function renderForecastChart(history, forecast) {
  const ctx = document.getElementById('forecastChart').getContext('2d');
  const histDates = history.map(r => r.date);
  const histVals = history.map(r => r.new_cases);
  const fcDates = forecast.map(r => r.date);
  const fcVals = forecast.map(r => r.y_pred);

  const labels = [...histDates, ...fcDates];
  const histDataset = {
    label: 'Historical Cases',
    data: [...histVals, ...new Array(fcVals.length).fill(null)],
    fill: false,
    borderColor: 'rgb(102, 126, 234)',
    backgroundColor: 'rgba(102, 126, 234, 0.1)',
    tension: 0.4,
    pointRadius: 2
  };
  const fcDataset = {
    label: 'Forecast',
    data: [...new Array(histVals.length).fill(null), ...fcVals],
    fill: false,
    borderColor: 'rgb(244, 67, 54)',
    borderDash: [5, 5],
    tension: 0.4,
    pointRadius: 3
  };

  if (forecastChart) forecastChart.destroy();
  forecastChart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [histDataset, fcDataset] },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: true,
          position: 'top'
        },
        tooltip: {
          mode: 'index',
          intersect: false
        }
      },
      scales: {
        x: {
          display: true,
          title: {
            display: true,
            text: 'Date'
          },
          ticks: {
            maxRotation: 45,
            minRotation: 45,
            maxTicksLimit: 20
          }
        },
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Number of Cases'
          },
          ticks: {
            callback: function(value) {
              return value.toLocaleString();
            }
          }
        }
      }
    }
  });
}

// Display AI Insights
function displayInsights(insights) {
  const insightsSection = document.getElementById('insightsSection');
  const insightsContent = document.getElementById('insightsContent');
  
  if (!insights || Object.keys(insights).length === 0) {
    insightsSection.style.display = 'none';
    return;
  }
  
  insightsContent.innerHTML = '';
  
  // Trend Analysis
  if (insights.trend_analysis && insights.trend_analysis.length > 0) {
    const trendDiv = document.createElement('div');
    trendDiv.innerHTML = '<div class="insight-category"><i class="fas fa-chart-line me-2"></i>Trend Analysis</div>';
    insights.trend_analysis.forEach(text => {
      const item = document.createElement('div');
      item.className = 'insight-item';
      item.textContent = text;
      trendDiv.appendChild(item);
    });
    insightsContent.appendChild(trendDiv);
  }
  
  // Forecast Insights
  if (insights.forecast_insights && insights.forecast_insights.length > 0) {
    const forecastDiv = document.createElement('div');
    forecastDiv.innerHTML = '<div class="insight-category"><i class="fas fa-crystal-ball me-2"></i>Forecast Insights</div>';
    insights.forecast_insights.forEach(text => {
      const item = document.createElement('div');
      item.className = 'insight-item';
      item.textContent = text;
      forecastDiv.appendChild(item);
    });
    insightsContent.appendChild(forecastDiv);
  }
  
  // Risk Assessment
  if (insights.risk_assessment && insights.risk_assessment.length > 0) {
    const riskDiv = document.createElement('div');
    riskDiv.innerHTML = '<div class="insight-category"><i class="fas fa-exclamation-triangle me-2"></i>Risk Assessment</div>';
    insights.risk_assessment.forEach(text => {
      const item = document.createElement('div');
      item.className = 'insight-item';
      item.style.borderLeftColor = '#dc3545';
      item.textContent = text;
      riskDiv.appendChild(item);
    });
    insightsContent.appendChild(riskDiv);
  }
  
  // Recommendations
  if (insights.recommendations && insights.recommendations.length > 0) {
    const recDiv = document.createElement('div');
    recDiv.innerHTML = '<div class="insight-category"><i class="fas fa-lightbulb me-2"></i>Recommendations</div>';
    insights.recommendations.forEach(text => {
      const item = document.createElement('div');
      item.className = 'insight-item';
      item.style.borderLeftColor = '#28a745';
      item.textContent = text;
      recDiv.appendChild(item);
    });
    insightsContent.appendChild(recDiv);
  }
  
  insightsSection.style.display = 'block';
}

// Run Forecast
async function runForecast() {
  const series = document.getElementById('seriesSelect').value;
  const h = parseInt(document.getElementById('horizon').value || "12");
  const finetune = parseInt(document.getElementById('finetuneSteps').value || "10");
  
  if (!series) {
    alert('Please select a series');
    return;
  }
  
  const runBtn = document.getElementById('runBtn');
  runBtn.disabled = true;
  runBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Running...';

  try {
    const payload = { unique_id: series, h: h, finetune_steps: finetune };
    const res = await fetch('/api/forecast', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    
    if (!res.ok) {
      throw new Error(`Forecast failed: ${res.statusText}`);
    }
    
    const data = await res.json();
    renderForecastChart(data.history, data.forecast);
    
    // Display insights if available
    if (data.insights) {
      displayInsights(data.insights);
    }
    
    // Calculate forecast average
    const forecastAvg = data.forecast.reduce((sum, r) => sum + r.y_pred, 0) / data.forecast.length;
    document.getElementById('kpi_forecast_avg').textContent = Math.round(forecastAvg).toLocaleString();
    
    // Fetch KPIs
    const kpiRes = await fetch(`/api/kpis?unique_id=${encodeURIComponent(series)}&h=8&finetune_steps=${finetune}`);
    const k = await kpiRes.json();
    const kpis = k.kpis || {};
    
    document.getElementById('kpi_mae').textContent = kpis.MAE ? kpis.MAE.toFixed(2) : '-';
    document.getElementById('kpi_rmse').textContent = kpis.RMSE ? kpis.RMSE.toFixed(2) : '-';
    document.getElementById('kpi_mape').textContent = kpis.MAPE_pct ? kpis.MAPE_pct.toFixed(2) + '%' : '-';
    document.getElementById('kpi_last').textContent = k.last_week_cases ?? '-';
    document.getElementById('kpi_avg12').textContent = k.avg_last_12_weeks ? Math.round(k.avg_last_12_weeks).toLocaleString() : '-';
    
    document.getElementById('forecastKPIs').style.display = 'flex';
    
  } catch (error) {
    console.error('Forecast error:', error);
    alert('Failed to run forecast: ' + error.message);
  } finally {
    runBtn.disabled = false;
    runBtn.innerHTML = '<i class="fas fa-play me-1"></i>Run Forecast';
  }
}

// Load Insights separately (if needed)
async function loadInsights() {
  const series = document.getElementById('seriesSelect').value;
  const h = parseInt(document.getElementById('horizon').value || "12");
  const finetune = parseInt(document.getElementById('finetuneSteps').value || "10");
  
  if (!series) {
    alert('Please select a series first');
    return;
  }
  
  const btn = document.getElementById('loadInsightsBtn');
  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Loading...';
  
  try {
    const payload = { unique_id: series, h: h, finetune_steps: finetune };
    const res = await fetch('/api/insights', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    
    if (!res.ok) {
      throw new Error(`Insights failed: ${res.statusText}`);
    }
    
    const insights = await res.json();
    displayInsights(insights);
    
  } catch (error) {
    console.error('Insights error:', error);
    alert('Failed to load insights: ' + error.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-brain me-1"></i>Load Insights';
  }
}

// Show data unavailable message
function showDataUnavailableMessage() {
  const mainContent = document.querySelector('.container');
  if (mainContent && !document.getElementById('dataUnavailableAlert')) {
    const alertDiv = document.createElement('div');
    alertDiv.id = 'dataUnavailableAlert';
    alertDiv.className = 'alert alert-warning alert-dismissible fade show mt-3';
    alertDiv.style.cssText = 'border-left: 4px solid #ffc107; background: #fff3cd;';
    alertDiv.innerHTML = `
      <div class="d-flex align-items-start">
        <i class="fas fa-exclamation-triangle me-3 mt-1" style="font-size: 1.5rem; color: #856404;"></i>
        <div>
          <h5 class="alert-heading mb-2">Forecasting Data Not Available</h5>
          <p class="mb-2">The disease forecasting data file (<code>PHREWS2_timegpt_weekly_v2.csv</code>) is missing.</p>
          <p class="mb-0"><strong>To enable forecasting:</strong></p>
          <ol class="mb-0 mt-2">
            <li>Obtain the <code>PHREWS2_timegpt_weekly_v2.csv</code> file</li>
            <li>Place it in the root directory: <code>${window.location.origin.replace('http://', '').replace('https://', '')}</code></li>
            <li>Restart the server</li>
          </ol>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;
    mainContent.insertBefore(alertDiv, mainContent.firstChild);
    
    // Disable controls
    document.getElementById('runBtn').disabled = true;
    document.getElementById('loadInsightsBtn').disabled = true;
    document.getElementById('seriesSelect').disabled = true;
  }
}

// Event Listeners
document.getElementById('runBtn').addEventListener('click', runForecast);
document.getElementById('loadInsightsBtn').addEventListener('click', loadInsights);

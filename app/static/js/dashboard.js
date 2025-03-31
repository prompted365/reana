/**
 * REanna Router - CRM Monitoring Dashboard
 * 
 * This script handles:
 * - Fetching monitoring data from API endpoints
 * - Updating dashboard UI elements
 * - Chart visualizations
 * - Navigation between dashboard sections
 * - Failed operations management
 */

// Global variables
let apiStatsData = {};
let rateLimitsData = {};
let circuitStatesData = {};
let summaryData = {};
let failedOperationsData = [];
let alertsData = [];
let alertConfigsData = {};
let refreshInterval = null;
let responseTimeChart = null;
let apiCallsChart = null;

// DOM elements
const sections = document.querySelectorAll('.dashboard-section');
const navLinks = document.querySelectorAll('nav a');

// Constants
const REFRESH_INTERVAL = 30000; // 30 seconds
const MAX_DISPLAY_ITEMS = 50;

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    fetchAllData();
    setupRefreshInterval();
    setupEventListeners();
});

/**
 * Initialize navigation functionality
 */
function initNavigation() {
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('data-target');
            
            // Update active nav link
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // Show target section, hide others
            sections.forEach(section => {
                section.classList.remove('active');
                if (section.id === targetId) {
                    section.classList.add('active');
                }
            });
        });
    });
}

/**
 * Set up automatic refresh interval
 */
function setupRefreshInterval() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    refreshInterval = setInterval(fetchAllData, REFRESH_INTERVAL);
}

/**
 * Set up event listeners for interactive elements
 */
function setupEventListeners() {
    // API Stats table sorting
    const sortSelect = document.getElementById('sort-by');
    if (sortSelect) {
        sortSelect.addEventListener('change', () => {
            renderApiStatsTable(apiStatsData);
        });
    }
    
    // API Stats search
    const searchInput = document.getElementById('endpoint-search');
    const searchButton = document.getElementById('search-button');
    if (searchInput && searchButton) {
        searchButton.addEventListener('click', () => {
            renderApiStatsTable(apiStatsData);
        });
        searchInput.addEventListener('keyup', (e) => {
            if (e.key === 'Enter') {
                renderApiStatsTable(apiStatsData);
            }
        });
    }
    
    // Failed operations filter
    const failedOpsFilter = document.getElementById('failed-ops-filter');
    if (failedOpsFilter) {
        failedOpsFilter.addEventListener('change', () => {
            renderFailedOperationsTable(failedOperationsData);
        });
    }
    
    // Retry all button
    const retryAllButton = document.getElementById('retry-all-button');
    if (retryAllButton) {
        retryAllButton.addEventListener('click', retryAllFailedOperations);
    }
    
    // Test alert button
    const testAlertButton = document.getElementById('test-alert-button');
    if (testAlertButton) {
        testAlertButton.addEventListener('click', () => {
            const alertType = document.getElementById('test-alert-type').value;
            const recipient = document.getElementById('test-alert-recipient').value;
            testAlert(alertType, recipient);
        });
    }
}

/**
 * Fetch all data from monitoring endpoints
 */
function fetchAllData() {
    fetchSummary();
    fetchApiStats();
    fetchRateLimits();
    fetchCircuitStates();
    fetchFailedOperations();
    fetchAlerts();
    fetchAlertConfigs();
}

/**
 * Fetch monitoring summary data
 */
function fetchSummary() {
    fetch('/api/monitoring/summary')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch summary data');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                summaryData = data.data;
                updateSummaryDisplay();
            }
        })
        .catch(error => {
            console.error('Error fetching summary:', error);
            updateSystemHealth('UNKNOWN');
        });
}

/**
 * Fetch API statistics
 */
function fetchApiStats() {
    fetch('/api/monitoring/api-stats')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch API stats');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                apiStatsData = data.data;
                renderApiStatsTable(apiStatsData);
                updateApiCharts();
            }
        })
        .catch(error => {
            console.error('Error fetching API stats:', error);
        });
}

/**
 * Fetch rate limits data
 */
function fetchRateLimits() {
    fetch('/api/monitoring/rate-limits')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch rate limits');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                rateLimitsData = data.data;
                renderRateLimitsGrid(rateLimitsData);
            }
        })
        .catch(error => {
            console.error('Error fetching rate limits:', error);
        });
}

/**
 * Fetch circuit breaker states
 */
function fetchCircuitStates() {
    fetch('/api/monitoring/circuit-states')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch circuit states');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                circuitStatesData = data.data;
                renderCircuitBreakersGrid(circuitStatesData);
            }
        })
        .catch(error => {
            console.error('Error fetching circuit states:', error);
        });
}

/**
 * Fetch failed operations
 */
function fetchFailedOperations() {
    fetch('/api/monitoring/failed-operations')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch failed operations');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                failedOperationsData = data.data;
                renderFailedOperationsTable(failedOperationsData);
            }
        })
        .catch(error => {
            console.error('Error fetching failed operations:', error);
            // Mock data for presentation until endpoint is implemented
            mockFailedOperations();
        });
}

/**
 * Fetch alerts data
 */
function fetchAlerts() {
    fetch('/api/monitoring/alerts')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch alerts');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                alertsData = data.data;
                renderAlertsTable(alertsData);
                updateAlertBadge(alertsData);
            }
        })
        .catch(error => {
            console.error('Error fetching alerts:', error);
        });
}

/**
 * Fetch alert configurations
 */
function fetchAlertConfigs() {
    fetch('/api/monitoring/alert-configs')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch alert configurations');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                alertConfigsData = data.data;
                renderAlertConfigCards(alertConfigsData);
            }
        })
        .catch(error => {
            console.error('Error fetching alert configurations:', error);
        });
}

/**
 * Update the system summary information
 */
function updateSummaryDisplay() {
    // Update system health indicator
    updateSystemHealth(summaryData.system_health);
    
    // Update last updated time
    const lastUpdated = document.getElementById('last-updated');
    if (lastUpdated) {
        const date = new Date(summaryData.timestamp);
        lastUpdated.textContent = `Last updated: ${date.toLocaleTimeString()}`;
    }
    
    // Update API stats overview
    document.getElementById('total-api-calls').textContent = summaryData.api_stats.total_calls.toLocaleString();
    document.getElementById('total-errors').textContent = summaryData.api_stats.total_errors.toLocaleString();
    document.getElementById('total-retries').textContent = summaryData.api_stats.total_retries.toLocaleString();
    
    const errorRate = document.getElementById('error-rate');
    if (errorRate) {
        errorRate.textContent = summaryData.api_stats.error_rate.toFixed(2);
        const errorRateContainer = document.getElementById('error-rate-container');
        
        // Color code error rate
        errorRateContainer.className = 'metric-large';
        if (summaryData.api_stats.error_rate > 10) {
            errorRateContainer.classList.add('text-danger');
        } else if (summaryData.api_stats.error_rate > 5) {
            errorRateContainer.classList.add('text-warning');
        } else {
            errorRateContainer.classList.add('text-success');
        }
    }
    
    // Update circuit breaker counts
    document.getElementById('open-circuits').textContent = summaryData.circuit_breakers.open;
    document.getElementById('half-open-circuits').textContent = summaryData.circuit_breakers.half_open;
    document.getElementById('closed-circuits').textContent = summaryData.circuit_breakers.closed;
    
    // Update rate limit status
    const rateLimitStatus = document.getElementById('rate-limit-status');
    if (rateLimitStatus) {
        rateLimitStatus.textContent = summaryData.rate_limits.status;
        rateLimitStatus.className = 'status-indicator';
        
        if (summaryData.rate_limits.status === 'HEALTHY') {
            rateLimitStatus.classList.add('status-healthy');
        } else if (summaryData.rate_limits.status === 'WARNING') {
            rateLimitStatus.classList.add('status-warning');
        } else if (summaryData.rate_limits.status === 'CRITICAL') {
            rateLimitStatus.classList.add('status-critical');
        }
    }
    
    document.getElementById('lowest-remaining-percent').textContent = 
        summaryData.rate_limits.lowest_remaining_percent.toFixed(1);
        
    // Update failed operations count if available
    if (summaryData.failed_operations) {
        const recentFailuresEl = document.getElementById('recent-failures');
        if (recentFailuresEl) {
            recentFailuresEl.textContent = summaryData.failed_operations.recent_count;
            
            if (summaryData.failed_operations.recent_count > 10) {
                recentFailuresEl.classList.add('text-danger');
            } else if (summaryData.failed_operations.recent_count > 5) {
                recentFailuresEl.classList.add('text-warning');
            } else {
                recentFailuresEl.classList.add('text-success');
            }
        }
    }
}

/**
 * Update the system health indicator
 */
function updateSystemHealth(health) {
    const healthElement = document.getElementById('system-health');
    if (!healthElement) return;
    
    healthElement.textContent = health;
    healthElement.className = 'health-status';
    
    switch (health) {
        case 'HEALTHY':
            healthElement.classList.add('health-healthy');
            break;
        case 'WARNING':
            healthElement.classList.add('health-warning');
            break;
        case 'DEGRADED':
            healthElement.classList.add('health-degraded');
            break;
        default:
            healthElement.classList.add('health-unknown');
            break;
    }
}

/**
 * Render the API statistics table
 */
function renderApiStatsTable(data) {
    const tableBody = document.getElementById('api-stats-body');
    if (!tableBody) return;
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    // Get search filter
    const searchValue = document.getElementById('endpoint-search')?.value.toLowerCase() || '';
    
    // Get sort preference
    const sortBy = document.getElementById('sort-by')?.value || 'calls';
    
    // Filter and sort the data
    let endpoints = Object.values(data);
    
    // Apply search filter
    if (searchValue) {
        endpoints = endpoints.filter(endpoint => 
            endpoint.endpoint.toLowerCase().includes(searchValue)
        );
    }
    
    // Apply sorting
    endpoints.sort((a, b) => {
        switch (sortBy) {
            case 'calls':
                return b.total_count - a.total_count;
            case 'errors':
                return b.error_count - a.error_count;
            case 'response-time':
                return b.average_response_time - a.average_response_time;
            default:
                return 0;
        }
    });
    
    // Limit to a reasonable number of rows
    endpoints = endpoints.slice(0, MAX_DISPLAY_ITEMS);
    
    // Generate table rows
    endpoints.forEach(endpoint => {
        const row = document.createElement('tr');
        
        // Calculate error rate percentage
        const errorRate = endpoint.total_count > 0 
            ? ((endpoint.error_count / endpoint.total_count) * 100).toFixed(2) 
            : '0.00';
        
        // Format last called date
        const lastCalled = endpoint.last_called 
            ? new Date(endpoint.last_called).toLocaleString() 
            : 'Never';
        
        row.innerHTML = `
            <td>${endpoint.endpoint}</td>
            <td>${endpoint.total_count.toLocaleString()}</td>
            <td>${endpoint.success_count.toLocaleString()}</td>
            <td>${endpoint.error_count.toLocaleString()}</td>
            <td>${errorRate}%</td>
            <td>${endpoint.average_response_time.toFixed(2)}ms</td>
            <td>${endpoint.percentile_95.toFixed(2)}ms</td>
            <td>${endpoint.retry_count.toLocaleString()}</td>
            <td>${lastCalled}</td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Display empty state if no data
    if (endpoints.length === 0) {
        const emptyRow = document.createElement('tr');
        emptyRow.innerHTML = `
            <td colspan="9" class="text-center">No API calls matching filter criteria</td>
        `;
        tableBody.appendChild(emptyRow);
    }
}

/**
 * Render the circuit breakers grid
 */
function renderCircuitBreakersGrid(data) {
    const grid = document.getElementById('circuit-breakers-grid');
    if (!grid) return;
    
    // Clear existing content
    grid.innerHTML = '';
    
    // If no data, show empty state
    if (Object.keys(data).length === 0) {
        grid.innerHTML = '<div class="empty-state">No circuit breakers active</div>';
        return;
    }
    
    // Create a card for each circuit breaker
    Object.values(data).forEach(circuit => {
        const card = document.createElement('div');
        card.className = 'circuit-card';
        
        // Define state class
        let stateClass = 'state-closed';
        if (circuit.current_state === 'OPEN') {
            stateClass = 'state-open';
        } else if (circuit.current_state === 'HALF_OPEN') {
            stateClass = 'state-half-open';
        }
        
        // Format timestamps
        const lastStateChange = circuit.last_state_change
            ? new Date(circuit.last_state_change).toLocaleString()
            : 'N/A';
        const lastFailure = circuit.last_failure
            ? new Date(circuit.last_failure).toLocaleString()
            : 'N/A';
        const lastSuccess = circuit.last_success
            ? new Date(circuit.last_success).toLocaleString()
            : 'N/A';
        
        card.innerHTML = `
            <div class="circuit-state ${stateClass}">${circuit.current_state}</div>
            <div class="circuit-details">
                <div class="circuit-name">${circuit.name}</div>
                <div class="circuit-stats">
                    <div class="circuit-stat">
                        <span class="circuit-stat-label">Failures:</span>
                        <span>${circuit.failure_count}</span>
                    </div>
                    <div class="circuit-stat">
                        <span class="circuit-stat-label">State Changes:</span>
                        <span>${circuit.state_change_count}</span>
                    </div>
                    <div class="circuit-stat">
                        <span class="circuit-stat-label">Last State Change:</span>
                        <span>${lastStateChange}</span>
                    </div>
                    <div class="circuit-stat">
                        <span class="circuit-stat-label">Last Failure:</span>
                        <span>${lastFailure}</span>
                    </div>
                    <div class="circuit-stat">
                        <span class="circuit-stat-label">Last Success:</span>
                        <span>${lastSuccess}</span>
                    </div>
                    <div class="circuit-stat">
                        <span class="circuit-stat-label">Open Duration:</span>
                        <span>${circuit.open_duration}</span>
                    </div>
                    <div class="circuit-stat">
                        <span class="circuit-stat-label">Total Open Time:</span>
                        <span>${circuit.total_open_time}</span>
                    </div>
                </div>
            </div>
        `;
        
        grid.appendChild(card);
    });
}

/**
 * Render the rate limits grid
 */
function renderRateLimitsGrid(data) {
    const grid = document.getElementById('rate-limits-grid');
    if (!grid) return;
    
    // Clear existing content
    grid.innerHTML = '';
    
    // If no data, show empty state
    if (Object.keys(data).length === 0) {
        grid.innerHTML = '<div class="empty-state">No rate limit data available</div>';
        return;
    }
    
    // Create a card for each rate limit
    Object.values(data).forEach(limit => {
        const card = document.createElement('div');
        card.className = 'card';
        
        // Calculate percentage used
        const percentUsed = limit.limit > 0
            ? ((limit.limit - limit.remaining) / limit.limit) * 100
            : 0;
        
        // Format reset time
        const resetTime = limit.reset_time
            ? new Date(limit.reset_time).toLocaleString()
            : 'N/A';
        
        // Format last updated
        const lastUpdated = limit.last_updated
            ? new Date(limit.last_updated).toLocaleString()
            : 'N/A';
        
        // Determine status class
        let statusClass = 'bg-success';
        if (percentUsed > 90) {
            statusClass = 'bg-danger';
        } else if (percentUsed > 75) {
            statusClass = 'bg-warning';
        }
        
        card.innerHTML = `
            <div class="card-header">
                <h3>${limit.endpoint}</h3>
            </div>
            <div class="card-body">
                <div class="rate-limit-progress">
                    <div class="progress">
                        <div class="progress-bar ${statusClass}" style="width: ${percentUsed}%"></div>
                    </div>
                    <div class="usage-label">
                        ${Math.round(percentUsed)}% Used (${limit.limit - limit.remaining}/${limit.limit})
                    </div>
                </div>
                <div class="rate-limit-details">
                    <div class="rate-limit-stat">
                        <span class="stat-label">Remaining:</span>
                        <span>${limit.remaining}</span>
                    </div>
                    <div class="rate-limit-stat">
                        <span class="stat-label">Reset Time:</span>
                        <span>${resetTime}</span>
                    </div>
                    <div class="rate-limit-stat">
                        <span class="stat-label">Last Updated:</span>
                        <span>${lastUpdated}</span>
                    </div>
                </div>
            </div>
        `;
        
        grid.appendChild(card);
    });
}

/**
 * Render the failed operations table
 */
function renderFailedOperationsTable(data) {
    const tableBody = document.getElementById('failed-ops-body');
    if (!tableBody) return;
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    // Get filter value
    const filterValue = document.getElementById('failed-ops-filter')?.value || 'all';
    
    // Filter the data
    let operations = data;
    if (filterValue !== 'all') {
        operations = data.filter(op => op.type === filterValue);
    }
    
    // If no data, show empty state
    if (operations.length === 0) {
        const emptyRow = document.createElement('tr');
        emptyRow.innerHTML = `
            <td colspan="7" class="text-center">No failed operations found</td>
        `;
        tableBody.appendChild(emptyRow);
        return;
    }
    
    // Generate table rows
    operations.forEach(op => {
        const row = document.createElement('tr');
        
        // Format last attempt time
        const lastAttempt = new Date(op.last_attempt).toLocaleString();
        
        // Determine status class
        let statusClass = '';
        switch (op.status) {
            case 'FAILED':
                statusClass = 'status-failed';
                break;
            case 'PENDING_RETRY':
                statusClass = 'status-retry';
                break;
            case 'PENDING':
                statusClass = 'status-pending';
                break;
        }
        
        row.innerHTML = `
            <td>${op.id}</td>
            <td>${op.operation}</td>
            <td class="${statusClass}">${op.status}</td>
            <td>${lastAttempt}</td>
            <td>${op.retry_count}</td>
            <td>${op.error}</td>
            <td class="action-cell">
                <button class="retry-button" data-id="${op.id}">
                    <i class="fas fa-sync"></i> Retry
                </button>
                <button class="delete-button" data-id="${op.id}">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Add event listeners for action buttons
    document.querySelectorAll('.retry-button').forEach(button => {
        button.addEventListener('click', () => {
            retryFailedOperation(button.getAttribute('data-id'));
        });
    });
    
    document.querySelectorAll('.delete-button').forEach(button => {
        button.addEventListener('click', () => {
            deleteFailedOperation(button.getAttribute('data-id'));
        });
    });
}

/**
 * Render the alerts table
 */
function renderAlertsTable(data) {
    const tableBody = document.getElementById('alerts-table-body');
    if (!tableBody) return;
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    // If no data, show empty state
    if (!data || data.length === 0) {
        const emptyRow = document.createElement('tr');
        emptyRow.innerHTML = `
            <td colspan="6" class="text-center">No alerts found</td>
        `;
        tableBody.appendChild(emptyRow);
        return;
    }
    
    // Generate table rows
    data.forEach(alert => {
        const row = document.createElement('tr');
        
        // Determine severity class
        let severityClass = '';
        switch (alert.level) {
            case 'CRITICAL':
                severityClass = 'alert-danger';
                break;
            case 'ERROR':
                severityClass = 'alert-warning';
                break;
            case 'WARNING':
                severityClass = 'alert-info';
                break;
            case 'INFO':
                severityClass = 'alert-success';
                break;
        }
        
        // Format timestamp
        const timestamp = new Date(alert.timestamp).toLocaleString();
        
        row.className = severityClass;
        row.innerHTML = `
            <td>${timestamp}</td>
            <td>${alert.level}</td>
            <td>${alert.type}</td>
            <td>${alert.entity_type} - ${alert.entity_id}</td>
            <td>${alert.message}</td>
            <td>
                <button class="btn btn-sm btn-primary view-alert-details" data-id="${alert.id}">
                    <i class="fas fa-eye"></i> Details
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Add event listeners for view details buttons
    document.querySelectorAll('.view-alert-details').forEach(button => {
        button.addEventListener('click', () => {
            viewAlertDetails(button.getAttribute('data-id'));
        });
    });
}

/**
 * Render alert configuration cards
 */
function renderAlertConfigCards(data) {
    const container = document.getElementById('alert-configs-container');
    if (!container) return;
    
    // Clear existing content
    container.innerHTML = '';
    
    // If no data, show empty state
    if (!data || Object.keys(data).length === 0) {
        container.innerHTML = '<div class="empty-state">No alert configurations found</div>';
        return;
    }
    
    // Create a card for each alert configuration
    Object.entries(data).forEach(([type, config]) => {
        const card = document.createElement('div');
        card.className = 'card mb-3';
        
        // Format methods list
        const methods = Array.isArray(config.methods) 
            ? config.methods.join(', ') 
            : config.methods;
        
        card.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5>${type}</h5>
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" id="toggle-${type.replace(/\s+/g, '-')}"
                        ${config.enabled ? 'checked' : ''} data-type="${type}">
                    <label class="form-check-label" for="toggle-${type.replace(/\s+/g, '-')}">
                        ${config.enabled ? 'Enabled' : 'Disabled'}
                    </label>
                </div>
            </div>
            <div class="card-body">
                <div class="alert-config-details">
                    <div><strong>Level:</strong> ${config.level}</div>
                    <div><strong>Threshold:</strong> ${config.threshold} failures within ${config.window_minutes} minutes</div>
                    <div><strong>Methods:</strong> ${methods}</div>
                    <div><strong>Cooldown:</strong> ${config.cooldown_minutes} minutes</div>
                </div>
                <button class="btn btn-sm btn-primary mt-2 edit-alert-config" data-type="${type}">
                    <i class="fas fa-edit"></i> Edit
                </button>
            </div>
        `;
        
        container.appendChild(card);
    });
    
    // Add event listeners for toggle switches
    document.querySelectorAll('.form-check-input').forEach(toggle => {
        toggle.addEventListener('change', function() {
            const type = this.getAttribute('data-type');
            const enabled = this.checked;
            toggleAlertConfig(type, enabled);
            this.nextElementSibling.textContent = enabled ? 'Enabled' : 'Disabled';
        });
    });
    
    // Add event listeners for edit buttons
    document.querySelectorAll('.edit-alert-config').forEach(button => {
        button.addEventListener('click', function() {
            const type = this.getAttribute('data-type');
            showEditAlertConfigModal(type, data[type]);
        });
    });
}

/**
 * Show edit alert configuration modal
 */
function showEditAlertConfigModal(type, config) {
    // In a real implementation, this would create a modal dialog
    // For now, we'll just log the config and show an alert
    console.log(`Editing alert config for ${type}:`, config);
    alert(`Editing configuration for ${type} would open a modal dialog (not implemented in demo)`);
}

/**
 * Toggle alert configuration enabled state
 */
function toggleAlertConfig(type, enabled) {
    // In a real implementation, this would call the API to update the config
    console.log(`Toggling alert config for ${type}: ${enabled ? 'enabled' : 'disabled'}`);
    
    // For now, just update the local data
    if (alertConfigsData[type]) {
        alertConfigsData[type].enabled = enabled;
    }
}

/**
 * View alert details
 */
function viewAlertDetails(alertId) {
    // Find the alert in the data
    const alert = alertsData.find(a => a.id === alertId);
    
    if (!alert) {
        console.error(`Alert with ID ${alertId} not found`);
        return;
    }
    
    // In a real implementation, this would open a modal with alert details
    console.log('Alert details:', alert);
    alert(`Alert details for ${alertId} would open a modal dialog (not implemented in demo)`);
}

/**
 * Update alert indicator badge
 */
function updateAlertBadge(alerts) {
    const badge = document.getElementById('alerts-badge');
    if (!badge) return;
    
    // Count critical and error alerts
    const highSeverityCount = alerts.filter(alert => 
        alert.level === 'CRITICAL' || alert.level === 'ERROR'
    ).length;
    
    if (highSeverityCount > 0) {
        badge.textContent = highSeverityCount;
        badge.classList.remove('d-none');
    } else {
        badge.classList.add('d-none');
    }
}

/**
 * Update charts with API stats data
 */
function updateApiCharts() {
    updateResponseTimeChart();
    updateApiCallsChart();
}

/**
 * Update the response time chart
 */
function updateResponseTimeChart() {
    const ctx = document.getElementById('response-time-chart');
    if (!ctx) return;
    
    // Extract data for chart
    const endpoints = Object.values(apiStatsData)
        .filter(endpoint => endpoint.success_count > 0)
        .sort((a, b) => b.average_response_time - a.average_response_time)
        .slice(0, 10);
    
    const labels = endpoints.map(endpoint => {
        // Shorten endpoint names for better display
        return endpoint.endpoint.length > 25
            ? endpoint.endpoint.substring(0, 22) + '...'
            : endpoint.endpoint;
    });
    
    const avgData = endpoints.map(endpoint => endpoint.average_response_time);
    const p95Data = endpoints.map(endpoint => endpoint.percentile_95);
    
    // Create or update chart
    if (responseTimeChart) {
        responseTimeChart.data.labels = labels;
        responseTimeChart.data.datasets[0].data = avgData;
        responseTimeChart.data.datasets[1].data = p95Data;
        responseTimeChart.update();
    } else {
        responseTimeChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Average (ms)',
                        data: avgData,
                        backgroundColor: 'rgba(52, 152, 219, 0.5)',
                        borderColor: 'rgba(52, 152, 219, 1)',
                        borderWidth: 1
                    },
                    {
                        label: '95th Percentile (ms)',
                        data: p95Data,
                        backgroundColor: 'rgba(231, 76, 60, 0.5)',
                        borderColor: 'rgba(231, 76, 60, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Response Time (ms)'
                        }
                    },
                    x: {
                        ticks: {
                            autoSkip: false,
                            maxRotation: 90,
                            minRotation: 45
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            title: function(tooltipItems) {
                                const index = tooltipItems[0].dataIndex;
                                return endpoints[index].endpoint;
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Update the API calls chart
 */
function updateApiCallsChart() {
    const ctx = document.getElementById('api-calls-chart');
    if (!ctx) return;
    
    // Extract data for chart
    const endpoints = Object.values(apiStatsData)
        .sort((a, b) => b.total_count - a.total_count)
        .slice(0, 10);
    
    const labels = endpoints.map(endpoint => {
        // Shorten endpoint names for better display
        return endpoint.endpoint.length > 25
            ? endpoint.endpoint.substring(0, 22) + '...'
            : endpoint.endpoint;
    });
    
    const successData = endpoints.map(endpoint => endpoint.success_count);
    const errorData = endpoints.map(endpoint => endpoint.error_count);
    
    // Create or update chart
    if (apiCallsChart) {
        apiCallsChart.data.labels = labels;
        apiCallsChart.data.datasets[0].data = successData;
        apiCallsChart.data.datasets[1].data = errorData;
        apiCallsChart.update();
    } else {
        apiCallsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Successful Calls',
                        data: successData,
                        backgroundColor: 'rgba(46, 204, 113, 0.5)',
                        borderColor: 'rgba(46, 204, 113, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Failed Calls',
                        data: errorData,
                        backgroundColor: 'rgba(231, 76, 60, 0.5)',
                        borderColor: 'rgba(231, 76, 60, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of API Calls'
                        },
                        stacked: true
                    },
                    x: {
                        ticks: {
                            autoSkip: false,
                            maxRotation: 90,
                            minRotation: 45
                        },
                        stacked: true
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            title: function(tooltipItems) {
                                const index = tooltipItems[0].dataIndex;
                                return endpoints[index].endpoint;
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Retry a failed operation
 */
function retryFailedOperation(id) {
    fetch(`/api/monitoring/retry-operation/${id}`, {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to retry operation');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // Refresh failed operations
            fetchFailedOperations();
            
            // Show success message
            alert('Operation queued for retry');
        } else {
            alert(`Failed to retry operation: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error retrying operation:', error);
        alert('Failed to retry operation. See console for details.');
    });
}

/**
 * Delete a failed operation
 */
function deleteFailedOperation(id) {
    if (!confirm('Are you sure you want to delete this failed operation? This cannot be undone.')) {
        return;
    }
    
    fetch(`/api/monitoring/delete-operation/${id}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to delete operation');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // Refresh failed operations
            fetchFailedOperations();
            
            // Show success message
            alert('Operation deleted successfully');
        } else {
            alert(`Failed to delete operation: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error deleting operation:', error);
        alert('Failed to delete operation. See console for details.');
    });
}

/**
 * Retry all failed operations
 */
function retryAllFailedOperations() {
    if (!confirm('Are you sure you want to retry all failed operations?')) {
        return;
    }
    
    fetch('/api/monitoring/retry-all-operations', {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to retry all operations');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // Refresh failed operations
            fetchFailedOperations();
            
            // Show success message
            alert(`${data.count} operations queued for retry`);
        } else {
            alert(`Failed to retry operations: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error retrying all operations:', error);
        alert('Failed to retry operations. See console for details.');
    });
}

/**
 * Test an alert notification
 */
function testAlert(alertType, recipient) {
    if (!alertType || !recipient) {
        alert('Please provide both alert type and recipient');
        return;
    }
    
    fetch(`/api/monitoring/test-alert?alert_type=${alertType}&recipient=${recipient}`, {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to send test alert');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            alert(`Test alert sent successfully: ${data.message}`);
        } else {
            alert(`Failed to send test alert: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error sending test alert:', error);
        alert('Failed to send test alert. See console for details.');
    });
}

/**
 * Mock failed operations data for display purposes until API is implemented
 */
function mockFailedOperations() {
    failedOperationsData = [
        {
            id: 'mock-1',
            operation: 'Tour Sync - Property #12345',
            type: 'tour-sync',
            status: 'FAILED',
            last_attempt: new Date().toISOString(),
            retry_count: 3,
            error: 'API Connection Timeout'
        },
        {
            id: 'mock-2',
            operation: 'Feedback Sync - Client #54321',
            type: 'feedback-sync',
            status: 'PENDING_RETRY',
            last_attempt: new Date(Date.now() - 3600000).toISOString(),
            retry_count: 2,
            error: 'Rate Limit Exceeded'
        },
        {
            id: 'mock-3',
            operation: 'Tour Sync - Property #67890',
            type: 'tour-sync',
            status: 'FAILED',
            last_attempt: new Date(Date.now() - 7200000).toISOString(),
            retry_count: 5,
            error: 'Invalid Response Format'
        }
    ];
    
    renderFailedOperationsTable(failedOperationsData);
}
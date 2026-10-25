// ==========================================================================
// APEX INSTITUTE OF ENGINEERING & TECHNOLOGY
// Centralized Student Grievance Redressal Portal (C-SGRP)
// Administrative Client Scripts
// ==========================================================================

document.addEventListener('DOMContentLoaded', function () {
    // Initialize Chart.js for Admin Dashboard if container exists
    const adminChartsContainer = document.getElementById('admin-analytics-section');
    if (adminChartsContainer) {
        initAdminAnalytics();
    }
});

function initAdminAnalytics() {
    fetch('/api/analytics')
        .then(response => response.json())
        .then(data => {
            renderCategoryChart(data.categories);
            renderDepartmentChart(data.departments);
            renderPriorityChart(data.priorities);
            renderStatusChart(data.statuses);
            renderTrendChart(data.monthly);
        })
        .catch(err => console.error("Failed to load analytics data:", err));
}

function renderCategoryChart(catData) {
    const ctx = document.getElementById('categoryChart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: catData.labels,
            datasets: [{
                data: catData.data,
                backgroundColor: [
                    '#002147', '#0369a1', '#15803d', '#b45309',
                    '#6b21a8', '#b91c1c', '#475569', '#0d9488'
                ],
                borderWidth: 1,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } }
            }
        }
    });
}

function renderDepartmentChart(deptData) {
    const ctx = document.getElementById('departmentChart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: deptData.labels,
            datasets: [{
                label: 'Assigned Complaints',
                data: deptData.data,
                backgroundColor: '#002147',
                borderRadius: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } },
                x: { ticks: { font: { size: 10 }, maxRotation: 45, minRotation: 25 } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

function renderPriorityChart(prioData) {
    const ctx = document.getElementById('priorityChart');
    if (!ctx) return;
    
    const colors = prioData.labels.map(l => {
        if (l === 'High') return '#b91c1c';
        if (l === 'Medium') return '#b45309';
        return '#475569';
    });

    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: prioData.labels,
            datasets: [{
                data: prioData.data,
                backgroundColor: colors,
                borderWidth: 1,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } }
            }
        }
    });
}

function renderStatusChart(statusData) {
    const ctx = document.getElementById('statusChart');
    if (!ctx) return;
    
    const colors = statusData.labels.map(s => {
        if (s === 'Resolved') return '#15803d';
        if (s === 'In Progress') return '#0284c7';
        if (s === 'Assigned') return '#b45309';
        return '#475569';
    });

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: statusData.labels,
            datasets: [{
                label: 'Grievances',
                data: statusData.data,
                backgroundColor: colors,
                borderRadius: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

function renderTrendChart(trendData) {
    const ctx = document.getElementById('trendChart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: trendData.labels,
            datasets: [{
                label: 'Monthly Submissions',
                data: trendData.data,
                borderColor: '#002147',
                backgroundColor: 'rgba(0, 33, 71, 0.06)',
                borderWidth: 2,
                fill: true,
                tension: 0.2,
                pointBackgroundColor: '#c59b27',
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

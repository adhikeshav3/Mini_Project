// Main JavaScript for Student Grievance Portal

document.addEventListener('DOMContentLoaded', function () {
    // 1. Initialize Chart.js for Admin Dashboard if container exists
    const adminChartsContainer = document.getElementById('admin-analytics-section');
    if (adminChartsContainer) {
        initAdminAnalytics();
    }

    // 2. Real-time AI Grievance Assistant Preview on Student Form
    const grievanceTitle = document.getElementById('grievance-title-input');
    const grievanceDesc = document.getElementById('grievance-desc-input');
    const previewContainer = document.getElementById('ai-live-preview');

    if (grievanceTitle && grievanceDesc && previewContainer) {
        let debounceTimer;
        const fetchPreview = () => {
            const title = grievanceTitle.value.trim();
            const desc = grievanceDesc.value.trim();

            if (title.length < 5 && desc.length < 10) {
                previewContainer.classList.add('d-none');
                return;
            }

            fetch('/api/predict-preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: title, description: desc })
            })
            .then(res => res.json())
            .then(data => {
                if (data && !data.error) {
                    previewContainer.classList.remove('d-none');
                    document.getElementById('ai-pred-category').innerText = data.category || 'Analyzing...';
                    document.getElementById('ai-pred-confidence').innerText = (data.confidence * 100).toFixed(0) + '%';
                    document.getElementById('ai-pred-priority').innerText = data.priority || 'Medium';
                    document.getElementById('ai-pred-sentiment').innerText = data.sentiment || 'Neutral';

                    const safetyBox = document.getElementById('ai-safety-alert');
                    if (data.is_safety_escalated) {
                        safetyBox.classList.remove('d-none');
                        safetyBox.innerText = "⚠ Safety Alert: " + data.escalation_reason;
                    } else {
                        safetyBox.classList.add('d-none');
                    }
                }
            })
            .catch(err => console.error("AI preview error:", err));
        };

        const debouncedFetch = () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(fetchPreview, 600);
        };

        grievanceTitle.addEventListener('input', debouncedFetch);
        grievanceDesc.addEventListener('input', debouncedFetch);
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
                    '#1e3a8a', '#0284c7', '#059669', '#d97706',
                    '#7c3aed', '#dc2626', '#475569', '#0d9488'
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
                backgroundColor: '#1e3a8a',
                borderRadius: 4
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
    
    // Map colors to priority labels
    const colors = prioData.labels.map(l => {
        if (l === 'High') return '#dc2626';
        if (l === 'Medium') return '#d97706';
        return '#64748b';
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
        if (s === 'Resolved') return '#059669';
        if (s === 'In Progress') return '#0284c7';
        if (s === 'Assigned') return '#d97706';
        return '#64748b';
    });

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: statusData.labels,
            datasets: [{
                label: 'Grievances',
                data: statusData.data,
                backgroundColor: colors,
                borderRadius: 4
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
                borderColor: '#1e3a8a',
                backgroundColor: 'rgba(30, 58, 138, 0.08)',
                borderWidth: 2,
                fill: true,
                tension: 0.25,
                pointBackgroundColor: '#c28c19',
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

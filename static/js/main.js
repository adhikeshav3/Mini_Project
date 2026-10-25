// ==========================================================================
// APEX INSTITUTE OF TECHNOLOGY & ENGINEERING
// Student Grievance Resolution Portal - Client Scripts
// ==========================================================================

document.addEventListener('DOMContentLoaded', function () {
    // 1. Initialize Chart.js for Admin Analytics if on admin page
    const adminChartsContainer = document.getElementById('admin-analytics-section');
    if (adminChartsContainer && typeof Chart !== 'undefined') {
        initAdminAnalytics();
    }

    // 2. Client-side fast table filter if input has data-table-filter attribute
    document.querySelectorAll('[data-table-filter]').forEach(function (input) {
        const tableSelector = input.getAttribute('data-table-filter');
        const table = document.querySelector(tableSelector);
        if (!table) return;

        input.addEventListener('input', function () {
            const query = input.value.toLowerCase().trim();
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(function (row) {
                const text = row.textContent.toLowerCase();
                if (text.includes(query)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    });

    // 3. Auto-dismiss alerts after 6 seconds for clean UX (except error alerts)
    document.querySelectorAll('.alert-success, .alert-info').forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 6000);
    });
});

// --------------------------------------------------------------------------
// Admin Analytics Visualizations (Chart.js)
// --------------------------------------------------------------------------
function initAdminAnalytics() {
    fetch('/api/analytics')
        .then(function (response) {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(function (data) {
            renderCategoryChart(data.categories);
            renderDepartmentChart(data.departments);
            renderPriorityChart(data.priorities);
            renderStatusChart(data.statuses);
            renderTrendChart(data.monthly);
        })
        .catch(function (err) {
            console.error('Failed to load institutional analytics:', err);
        });
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
                    '#0b2545', '#134074', '#0284c7', '#16a34a',
                    '#d97706', '#dc2626', '#475569', '#0d9488'
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11, family: 'sans-serif' } } }
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
                backgroundColor: '#0b2545',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } },
                x: { ticks: { font: { size: 10 }, maxRotation: 35, minRotation: 20 } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

function renderPriorityChart(prioData) {
    const ctx = document.getElementById('priorityChart');
    if (!ctx) return;

    const colors = prioData.labels.map(function (l) {
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
                borderWidth: 2,
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

    const colors = statusData.labels.map(function (s) {
        if (s === 'Resolved') return '#16a34a';
        if (s === 'In Progress') return '#0284c7';
        if (s === 'Assigned') return '#7c3aed';
        return '#64748b';
    });

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: statusData.labels,
            datasets: [{
                label: 'Count',
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
                borderColor: '#134074',
                backgroundColor: 'rgba(19, 64, 116, 0.08)',
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointBackgroundColor: '#0b2545'
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

// --------------------------------------------------------------------------
// UI Helper Utilities
// --------------------------------------------------------------------------

// 1-Click Demo Credentials Populator
function fillCreds(email, pwd) {
    const emailField = document.getElementById('email');
    const pwdField = document.getElementById('password');
    if (emailField && pwdField) {
        emailField.value = email;
        pwdField.value = pwd;
        emailField.focus();
    }
}

// Password Visibility Toggle
function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isPassword = input.getAttribute('type') === 'password';
    input.setAttribute('type', isPassword ? 'text' : 'password');
    const icon = btn.querySelector('i');
    if (icon) {
        icon.className = isPassword ? 'bi bi-eye-slash' : 'bi bi-eye';
    }
}

// Attachment File Name Display
function updateFileName(input, targetId) {
    const target = document.getElementById(targetId);
    if (!target) return;
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
        target.textContent = file.name + ' (' + sizeMb + ' MB)';
        target.classList.remove('text-muted');
        target.classList.add('text-primary', 'fw-semibold');
    } else {
        target.textContent = '';
    }
}

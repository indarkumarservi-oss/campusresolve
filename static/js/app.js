// CampusResolve Frontend JavaScript

(function() {
    'use strict';
    
    // Get CSRF token from meta tag
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
    
    const csrfToken = getCsrfToken();
    const apiHeaders = csrfToken ? {'X-CSRFToken': csrfToken, 'Content-Type': 'application/json'} : {'Content-Type': 'application/json'};
    
    // Initialize tooltips
    function initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Initialize popovers
    function initPopovers() {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function(popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
    
    // Auto-dismiss alerts after 5 seconds
    function autoDismissAlerts() {
        setTimeout(function() {
            document.querySelectorAll('.alert-dismissible').forEach(function(alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            });
        }, 5000);
    }
    
    // Confirm delete actions
    function initConfirmActions() {
        document.querySelectorAll('[data-confirm]').forEach(function(element) {
            element.addEventListener('click', function(e) {
                const message = this.getAttribute('data-confirm') || 'Are you sure?';
                if (!confirm(message)) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            });
        });
    }
    
    // Copy to clipboard
    function initCopyButtons() {
        document.querySelectorAll('[data-copy]').forEach(function(button) {
            button.addEventListener('click', function() {
                const targetId = this.getAttribute('data-copy');
                const target = document.getElementById(targetId);
                if (target) {
                    const text = target.value || target.textContent;
                    navigator.clipboard.writeText(text).then(function() {
                        const originalText = button.innerHTML;
                        button.innerHTML = '<i class="bi bi-check"></i> Copied!';
                        button.classList.remove('btn-outline-secondary');
                        button.classList.add('btn-success');
                        setTimeout(function() {
                            button.innerHTML = originalText;
                            button.classList.remove('btn-success');
                            button.classList.add('btn-outline-secondary');
                        }, 2000);
                    });
                }
            });
        });
    }
    
    // Form validation enhancement
    function initFormValidation() {
        document.querySelectorAll('form[novalidate]').forEach(function(form) {
            form.addEventListener('submit', function(e) {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Focus first invalid field
                    const firstInvalid = form.querySelector(':invalid');
                    if (firstInvalid) {
                        firstInvalid.focus();
                    }
                }
                form.classList.add('was-validated');
            });
        });
    }
    
    // Character counters for textareas
    function initCharCounters() {
        document.querySelectorAll('[data-max-length]').forEach(function(textarea) {
            const maxLength = parseInt(textarea.getAttribute('data-max-length'), 10);
            const counterId = textarea.getAttribute('data-counter');
            const counter = counterId ? document.getElementById(counterId) : null;
            
            function updateCounter() {
                const length = textarea.value.length;
                if (counter) {
                    counter.textContent = length;
                    counter.classList.toggle('text-danger', length > maxLength);
                }
            }
            
            textarea.addEventListener('input', updateCounter);
            updateCounter();
        });
    }
    
    // Table row click navigation
    function initTableRowClick() {
        document.querySelectorAll('table[data-row-link] tbody tr').forEach(function(row) {
            const link = row.getAttribute('data-row-link');
            if (link) {
                row.style.cursor = 'pointer';
                row.addEventListener('click', function(e) {
                    if (e.target.tagName !== 'A' && e.target.tagName !== 'BUTTON' && 
                        !e.target.closest('a') && !e.target.closest('button')) {
                        window.location.href = link;
                    }
                });
            }
        });
    }
    
    // Debounce function
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }
    
    // Search/filter debounce
    function initSearchDebounce() {
        document.querySelectorAll('form[data-debounce] input[type="search"], form[data-debounce] input[type="text"]').forEach(function(input) {
            const form = input.closest('form');
            const delay = parseInt(form.getAttribute('data-debounce'), 10) || 300;
            
            const debouncedSubmit = debounce(function() {
                form.requestSubmit();
            }, delay);
            
            input.addEventListener('input', debouncedSubmit);
        });
    }
    
    // Notification badge update
    function updateNotificationBadge() {
        if (typeof fetch === 'undefined') return;
        
        fetch('/api/notifications/unread-count')
            .then(res => res.json())
            .then(data => {
                const badge = document.getElementById('notif-badge');
                if (badge) {
                    if (data.count > 0) {
                        badge.textContent = data.count > 99 ? '99+' : data.count;
                        badge.style.display = 'inline-flex';
                    } else {
                        badge.style.display = 'none';
                    }
                }
            })
            .catch(() => {});
    }
    
    // Mark notification as read
    function markNotificationRead(notifId, element) {
        fetch('/api/notifications/read/' + notifId, { method: 'POST', headers: apiHeaders })
            .then(res => res.json())
            .then(data => {
                if (data.success && element) {
                    element.classList.remove('unread');
                    const btn = element.querySelector('.mark-read');
                    if (btn) btn.remove();
                    updateNotificationBadge();
                }
            });
    }
    
    // Initialize notification interactions
    function initNotifications() {
        document.querySelectorAll('.mark-read').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const notifId = this.dataset.notifId;
                const item = this.closest('.notification-item');
                markNotificationRead(notifId, item);
            });
        });
        
        // Update badge periodically
        updateNotificationBadge();
        setInterval(updateNotificationBadge, 30000);
    }
    
    // Print functionality
    function initPrintButtons() {
        document.querySelectorAll('[data-print]').forEach(function(button) {
            button.addEventListener('click', function() {
                window.print();
            });
        });
    }
    
    // Toggle password visibility
    function initPasswordToggle() {
        document.querySelectorAll('[data-toggle-password]').forEach(function(button) {
            button.addEventListener('click', function() {
                const targetId = this.getAttribute('data-toggle-password');
                const input = document.getElementById(targetId);
                if (input) {
                    const type = input.type === 'password' ? 'text' : 'password';
                    input.type = type;
                    this.innerHTML = type === 'password' ? '<i class="bi bi-eye"></i>' : '<i class="bi bi-eye-slash"></i>';
                }
            });
        });
    }
    
    // Star rating
    function initStarRating() {
        document.querySelectorAll('.star-rating').forEach(function(container) {
            const stars = container.querySelectorAll('.star-btn');
            const input = container.querySelector('input[type="hidden"]');
            
            stars.forEach(function(star) {
                star.addEventListener('click', function() {
                    const value = this.dataset.value;
                    if (input) input.value = value;
                    
                    stars.forEach(function(s) {
                        const isActive = s.dataset.value <= value;
                        s.classList.toggle('btn-warning', isActive);
                        s.classList.toggle('btn-outline-warning', !isActive);
                        s.classList.toggle('text-warning', isActive);
                    });
                });
                
                star.addEventListener('mouseenter', function() {
                    const value = this.dataset.value;
                    stars.forEach(function(s) {
                        const isHover = s.dataset.value <= value;
                        s.classList.toggle('text-warning', isHover);
                    });
                });
                
                container.addEventListener('mouseleave', function() {
                    const currentValue = input ? input.value : 0;
                    stars.forEach(function(s) {
                        const isActive = s.dataset.value <= currentValue;
                        s.classList.toggle('text-warning', isActive);
                    });
                });
            });
        });
    }
    
    // Dynamic form fields (show/hide based on selection)
    function initDynamicFields() {
        document.querySelectorAll('[data-show-if]').forEach(function(element) {
            const condition = element.getAttribute('data-show-if');
            const [targetId, targetValue] = condition.split(':');
            const target = document.getElementById(targetId);
            
            function checkCondition() {
                if (target) {
                    const show = target.value === targetValue;
                    element.style.display = show ? 'block' : 'none';
                    if (!show) {
                        element.querySelectorAll('input, select, textarea').forEach(function(input) {
                            input.disabled = true;
                        });
                    } else {
                        element.querySelectorAll('input, select, textarea').forEach(function(input) {
                            input.disabled = false;
                        });
                    }
                }
            }
            
            if (target) {
                target.addEventListener('change', checkCondition);
                checkCondition();
            }
        });
    }
    
    // Export table to CSV
    function initExportButtons() {
        document.querySelectorAll('[data-export-csv]').forEach(function(button) {
            button.addEventListener('click', function() {
                const tableId = this.getAttribute('data-export-csv');
                const table = document.getElementById(tableId);
                if (!table) return;
                
                const rows = table.querySelectorAll('tr');
                const csv = [];
                
                rows.forEach(function(row) {
                    const cols = row.querySelectorAll('th, td');
                    const rowData = [];
                    cols.forEach(function(col) {
                        // Skip action columns
                        if (!col.classList.contains('no-export')) {
                            rowData.push('"' + col.textContent.trim().replace(/"/g, '""') + '"');
                        }
                    });
                    csv.push(rowData.join(','));
                });
                
                const blob = new Blob([csv.join('\n')], { type: 'text/csv;charset=utf-8;' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = tableId + '_' + new Date().toISOString().split('T')[0] + '.csv';
                link.click();
            });
        });
    }
    
    // Initialize all components when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        initTooltips();
        initPopovers();
        autoDismissAlerts();
        initConfirmActions();
        initCopyButtons();
        initFormValidation();
        initCharCounters();
        initTableRowClick();
        initSearchDebounce();
        initNotifications();
        initPrintButtons();
        initPasswordToggle();
        initStarRating();
        initDynamicFields();
        initExportButtons();
        
        // Add loaded class for CSS transitions
        document.body.classList.add('loaded');
    });
    
    // Export functions for global access
    window.CampusResolve = {
        updateNotificationBadge,
        markNotificationRead,
        debounce
    };
})();
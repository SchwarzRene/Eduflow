let isValidated = false;
async function fetchRequests() {
    try {
        const r = await fetch('/api/requests');
        const data = await r.json();
        if (!data.success) return;
        const list = document.getElementById('requestsList');
        if (!data.requests || data.requests.length === 0) {
            list.textContent = 'No requests yet.';
            return;
        }
        list.innerHTML = data.requests.map(req => `#${req.id} - ${req.status} - ${req.success ? '✅' : '❌'} - ${req.message || ''}`).join('<br>');
    } catch (e) {}
}
async function logout() {
    try {
        await fetch('/auth/logout', { method: 'POST' });
        window.location.href = '/login';
    } catch (e) {}
}
document.getElementById('logoutBtn').addEventListener('click', logout);
let autoSaveTimeout; // To manage auto-save debounce
const saveBtn = document.getElementById('saveBtn');
const originalSaveBtnText = '💾 Save Configuration';

// Mode selector functionality
document.querySelectorAll('.mode-option').forEach(option => {
    option.addEventListener('click', function() {
        document.querySelectorAll('.mode-option').forEach(opt => opt.classList.remove('active'));
        this.classList.add('active');
        document.getElementById('mode').value = this.dataset.mode;
        isValidated = false;
        document.getElementById('runBtn').disabled = true;
        markFormChanged(); // Mark form as changed on mode selection
        queueAutoSave(); // Trigger auto-save on mode change
    });
});

// Form input change handler
document.querySelectorAll('input, select').forEach(input => {
    input.addEventListener('input', function() {
        isValidated = false;
        document.getElementById('runBtn').disabled = true;
        this.classList.remove('error');
        const errorElement = document.getElementById(this.name + '-error');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
        markFormChanged(); // Mark form as changed on input
    });
});

function showStatus(message, type) {
    const status = document.getElementById('status');
    status.className = 'status ' + type;
    status.innerHTML = message;
    status.style.display = 'block';
}

function hideStatus() {
    document.getElementById('status').style.display = 'none';
}

function showError(fieldName, message) {
    const field = document.getElementById(fieldName);
    const errorElement = document.getElementById(fieldName + '-error');
    
    if (field) field.classList.add('error');
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
}

function validateForm() {
    hideStatus();
    let isValid = true;
    
    // Clear previous errors
    document.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
    document.querySelectorAll('.error-message').forEach(el => el.style.display = 'none');

    // Required field validation
    const requiredFields = ['username', 'password', 'dswid', 'dsrid', 'semester', 'courseNr', 'group_index'];
    
    requiredFields.forEach(fieldName => {
        const field = document.getElementById(fieldName);
        if (!field.value.trim()) {
            showError(fieldName, 'This field is required');
            isValid = false;
        }
    });

    // Semester format validation
    const semester = document.getElementById('semester').value;
    if (semester && !/^\d{4}[SW]$/i.test(semester)) {
        showError('semester', 'Format should be YYYYS or YYYYW (e.g., 2025S)');
        isValid = false;
    }

    // Study number format validation
    const studyNumber = document.getElementById('study_number').value;
    if (studyNumber && !/^\d{3}\s\d{3}$/.test(studyNumber)) {
        showError('study_number', 'Format should be "123 456" (with space)');
        isValid = false;
    }

    // Group index validation
    const groupIndex = document.getElementById('group_index').value;
    if (groupIndex !== '' && (isNaN(groupIndex) || groupIndex < 0)) {
        showError('group_index', 'Must be a non-negative number');
        isValid = false;
    }

    // Slot index validation
    const slotIndex = document.getElementById('slot_index').value;
    if (slotIndex !== '' && (isNaN(slotIndex) || slotIndex < 0)) {
        showError('slot_index', 'Must be a non-negative number or empty');
        isValid = false;
    }

    if (isValid) {
        isValidated = true;
        document.getElementById('runBtn').disabled = false;
        showStatus('✅ Configuration is valid! You can now start the registration process.', 'success');
    } else {
        isValidated = false;
        document.getElementById('runBtn').disabled = true;
        showStatus('❌ Please fix the errors above before proceeding.', 'error');
    }
}

function collectFormData() {
    const formData = {};
    const form = document.getElementById('tissForm');
    const formElements = form.querySelectorAll('input, select');
    
    formElements.forEach(element => {
        if (element.name && element.value !== '') {
            let value = element.value;
            
            // Convert numeric fields
            if (element.type === 'number') {
                value = parseInt(value);
            }
            
            // Handle datetime-local
            if (element.type === 'datetime-local') {
                value = value.replace('T', ' ') + ':00';
            }
            
            formData[element.name] = value;
        }
    });
    
    return formData;
}

async function saveConfigAndRun(config) {
    try {
        showStatus('🔄 Starting registration process...', 'running');
        
        const response = await fetch('/api/requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        
        if (result.success && result.request_id) {
            showStatus('🚀 Automation started! Monitoring progress...', 'running');
            monitorStatus(result.request_id);
            fetchRequests();
        } else {
            showStatus(`❌ Failed to start: ${result.message}`, 'error');
        }
    } catch (error) {
        showStatus(`❌ Network error: ${error.message}`, 'error');
    }
}
    
async function monitorStatus(requestId) {
    const checkStatus = async () => {
        try {
            const response = await fetch(`/api/requests/${requestId}`);
            const data = await response.json();
            if (!data.success) { showStatus('❌ Unable to fetch status', 'error'); return; }
            const req = data.request;
            if (req.status === 'running' || req.status === 'queued') {
                showStatus(`🔄 ${req.message || 'Processing...'}`, 'running');
                setTimeout(checkStatus, 2000);
            } else {
                showStatus(`${req.success ? '✅' : '❌'} ${req.message || req.status}`, req.success ? 'success' : 'error');
                document.getElementById('runBtn').disabled = false;
                fetchRequests();
            }
        } catch (error) {
            showStatus(`❌ Status check failed: ${error.message}`, 'error');
            document.getElementById('runBtn').disabled = false;
        }
    };
    
    setTimeout(checkStatus, 1000);
}

// Form submission
document.getElementById('tissForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    if (!isValidated) {
        showStatus('❌ Please validate the form first!', 'error');
        return;
    }
    
    document.getElementById('runBtn').disabled = true;
    const config = collectFormData();
    await saveConfigAndRun(config);
});

// Manual Save Configuration Function
async function saveConfiguration() {
    const config = collectFormData();
    if (!config.username || !config.dswid) {
        showStatus('Please fill in Username and DSWID before saving.', 'error');
        return;
    }
    try {
        saveBtn.innerHTML = '💾 Saving...';
        saveBtn.disabled = true;
        // Persist to backend for cross-device persistence
        const resp = await fetch('/api/user_config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config) });
        const res = await resp.json();
        if (!res.success) { throw new Error(res.message || 'Save failed'); }
        // Also keep a local copy for faster load
        localStorage.setItem('tiss_config', JSON.stringify(config));
        showStatus('✅ Configuration saved!', 'success');
        saveBtn.innerHTML = '✓ Saved!';
        saveBtn.classList.add('saved-state');
    } catch (error) {
        showStatus(`❌ Failed to save locally: ${error.message}`, 'error');
        saveBtn.innerHTML = '⚠ Save Failed';
        saveBtn.classList.remove('saved-state');
    } finally {
        setTimeout(() => {
            saveBtn.disabled = false;
            if (saveBtn.innerHTML !== '✓ Saved!') {
                saveBtn.innerHTML = originalSaveBtnText;
                saveBtn.classList.remove('saved-state');
            }
        }, 1000);
    }
}

// Function to mark the form as changed
function markFormChanged() {
    if (saveBtn.classList.contains('saved-state')) {
        saveBtn.innerHTML = originalSaveBtnText;
        saveBtn.classList.remove('saved-state');
    }
}

// Load existing configuration if available
async function loadExistingConfig() {
    let config = {};
    // Prefer server-side stored config; fallback to injected or localStorage
    try {
        const resp = await fetch('/api/user_config');
        const res = await resp.json();
        if (res && res.success && res.config) { config = res.config; }
    } catch (e) {}
    if (!config || !Object.keys(config).length) {
        if (window.EXISTING_CONFIG && Object.keys(window.EXISTING_CONFIG).length) {
            config = window.EXISTING_CONFIG;
        } else {
            try {
                const stored = localStorage.getItem('tiss_config');
                if (stored) config = JSON.parse(stored);
            } catch (e) {}
        }
    }
    if (config && Object.keys(config).length) {
        
        // Populate all form fields with existing data
        Object.keys(config).forEach(key => {
            const field = document.getElementById(key);
            if (field && config[key] !== null && config[key] !== undefined) {
                if (field.type === 'datetime-local') {
                    // Handle datetime-local format conversion
                    if (config[key].includes(' ')) {
                        const dateTime = config[key].replace(' ', 'T').substring(0, 16);
                        field.value = dateTime;
                    }
                } else if (key === 'mode') {
                    // Handle mode selector
                    document.querySelectorAll('.mode-option').forEach(opt => opt.classList.remove('active'));
                    document.querySelector(`[data-mode="${config[key]}"]`)?.classList.add('active');
                    field.value = config[key];
                } else {
                    field.value = config[key];
                }
            }
        });
        
        console.log('Loaded existing configuration');
        
        // If we have a valid configuration, enable validation button
        if (config.username && config.dswid) {
            showStatus('📋 Loaded existing configuration. Please verify and update if needed.', 'success');
            // Manually set the save button to 'Saved!' state after loading a config
            saveBtn.innerHTML = '✓ Saved!';
            saveBtn.classList.add('saved-state');
        }
    }
}

// Auto-save configuration with debouncing
function queueAutoSave() {
    clearTimeout(autoSaveTimeout);
    
    if (!saveBtn.classList.contains('saved-state')) { // Only show auto-saving if not already in 'Saved' state
        saveBtn.innerHTML = 'Auto-saving...';
        saveBtn.disabled = true; // Temporarily disable while auto-saving
    }

    autoSaveTimeout = setTimeout(async () => {
        const config = collectFormData();
        
        // Don't auto-save if essential fields are missing
        if (!config.username || !config.dswid) {
            if (!saveBtn.classList.contains('saved-state')) {
                saveBtn.innerHTML = originalSaveBtnText;
            }
            saveBtn.disabled = false;
            return;
        }
        
        try {
            // Save in background to backend and localStorage
            await fetch('/api/user_config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config) });
            localStorage.setItem('tiss_config', JSON.stringify(config));
            saveBtn.innerHTML = '✓ Saved!';
            saveBtn.classList.add('saved-state');
        } catch (error) {
            console.log('Local auto-save failed:', error);
            saveBtn.innerHTML = '⚠ Auto-Save Failed';
            saveBtn.classList.remove('saved-state');
        } finally {
            saveBtn.disabled = false;
            if (saveBtn.innerHTML === '⚠ Auto-Save Failed') {
                setTimeout(() => {
                    if (!saveBtn.classList.contains('saved-state')) {
                         saveBtn.innerHTML = originalSaveBtnText;
                    }
                }, 1000);
            }
        }
    }, 1000); // Debounce auto-save by 1 second
}

// Add auto-save listeners to form fields
function setupAutoSave() {
    const saveableFields = ['username', 'dswid', 'dsrid', 'semester', 'courseNr', 'study_number', 'group_index', 'slot_index', 'password', 'anmelden_time'];
    
    saveableFields.forEach(fieldName => {
        const field = document.getElementById(fieldName);
        if (field) {
            field.addEventListener('input', queueAutoSave); // Use input for immediate feedback
            field.addEventListener('change', queueAutoSave); // Fallback for some field types
            field.addEventListener('blur', queueAutoSave); // Ensure save on blur
        }
    });
    
    // Save mode changes immediately
    document.querySelectorAll('.mode-option').forEach(option => {
        option.addEventListener('click', function() {
            setTimeout(queueAutoSave, 100); 
        });
    });
}

// Auto-validate on page load if fields are pre-filled
window.addEventListener('load', async function() {
    // Load existing configuration first
    await loadExistingConfig();
    
    // Setup auto-save functionality
    setupAutoSave();
    
    // Set current datetime as default for anmelden_time if not already set
    const anmeldenTimeField = document.getElementById('anmelden_time');
    if (!anmeldenTimeField.value) {
        const now = new Date();
        now.setMinutes(now.getMinutes() + 5); // 5 minutes from now
        anmeldenTimeField.value = now.toISOString().slice(0, 16);
    }

    // Perform initial validation if config was loaded and essential fields are present
    if ((window.EXISTING_CONFIG && window.EXISTING_CONFIG.username && window.EXISTING_CONFIG.dswid) || (localStorage.getItem('tiss_config'))) {
         validateForm(); // Validate after loading config
    }
    document.getElementById('welcomeUser').textContent = (window.SESSION_USER) ? `👤 Logged in as ${window.SESSION_USER}` : '';
    // Reduce automatic polling: fetch once on load; further updates via manual actions
    fetchRequests();
});

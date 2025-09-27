let mode = 'login';
const tabs = document.querySelectorAll('.tab');
tabs.forEach(t => t.addEventListener('click', () => {
    tabs.forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    mode = t.dataset.mode;
    document.getElementById('status').textContent = '';
    document.getElementById('status').className = 'status'; // Clear previous status styling
}));

function setStatus(text, ok=false) {
    const el = document.getElementById('status');
    el.textContent = text;
    el.className = 'status ' + (ok ? 'success' : 'error');
}

document.getElementById('submitBtn').addEventListener('click', async () => {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    if (!username || !password) { setStatus('Please fill username and password', false); return; }
    try {
        const res = await fetch(mode === 'login' ? '/auth/login' : '/auth/register', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (data.success) {
            setStatus(data.message || 'Success!', true);
            window.location.href = '/';
            return;
        }
        setStatus(data.message || 'Failed', false);
    } catch (e) {
        setStatus(e.message, false);
    }
});

const $ = (id)=>document.getElementById(id);
function showStatus(msg, ok){ const el=$('status'); el.textContent=msg; el.className='status ' + (ok?'success':'error'); }
async function logout(){ try{ await fetch('/auth/logout',{method:'POST'}); window.location.href='/login'; }catch(e){} }
$('logoutBtn').addEventListener('click', logout);

async function fetchConfig(){ try{ const s = localStorage.getItem('tiss_config'); return s ? JSON.parse(s) : {}; } catch(e){ return {}; } }
async function listRequests(){ try{ const r = await fetch('/api/requests'); const d = await r.json(); if(!d.success) return []; return d.requests; } catch(e){ return []; } }
function canCancel(status){ return status==='queued' || status==='running' || status==='cancelling'; }
function renderRows(rows){ const tb=$('tbody'); tb.innerHTML = rows.map(r=>{
    const escMsg = (r.message||'').replace(/</g,'&lt;');
    const cancelBtn = canCancel(r.status) ? `<button data-cancel="${r.id}" class="btn secondary sm"><i class="fas fa-times"></i> Cancel</button>` : '';
    const successIcon = r.success ? '✅' : (r.success === false ? '❌' : '⏳'); // Added a loading icon for null/pending
    return `<tr><td>${r.id}</td><td>${r.status}</td><td>${successIcon}</td><td>${escMsg}</td><td>${r.updated_at||''}</td><td>${cancelBtn}</td></tr>`;
}).join('');
Array.from(tb.querySelectorAll('button[data-cancel]')).forEach(btn=>{ btn.addEventListener('click', ()=> cancelRequest(parseInt(btn.dataset.cancel))); }); }

async function send(){
    try{
        showStatus('Starting request...', true);
        const cfg = await fetchConfig();
        const r = await fetch('/api/requests',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(cfg)});
        const d = await r.json();
        if(d.success){ showStatus('Request started. Monitoring...', true); monitor(d.request_id); refresh(); }
        else { showStatus(d.message||'Failed to start', false); }
    }catch(e){ showStatus(e.message, false); }
}

// monitoring removed to reduce server load

async function refresh(){ const rows = await listRequests(); renderRows(rows); }
$('refreshBtn').addEventListener('click', refresh);

window.addEventListener('load', async ()=>{
    $('welcomeUser').textContent = (window.SESSION_USER) ? `👤 Logged in as ${window.SESSION_USER}` : '';
    await refresh();
});

async function cancelRequest(id){
    try{
        const r = await fetch(`/api/requests/${id}/cancel`, {method:'POST'});
        const d = await r.json();
        if(d.success){ showStatus('Cancellation requested', true); refresh(); }
        else { showStatus(d.message||'Failed to cancel', false); }
    }catch(e){ showStatus(e.message, false); }
}

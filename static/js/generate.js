const $ = (id)=>document.getElementById(id);
function showStatus(msg, ok){ const el=$('status'); el.textContent=msg; el.className='status ' + (ok?'success':'error'); }

// Function to set default time (1 hour in the future)
function setDefaultTime() {
    const dt = $('anmelden_time');
    const now = new Date();
    now.setHours(now.getHours() + 3); // Set to 1 hour in the future
    dt.value = now.toISOString().slice(0, 16);
}

function collect(){
    const map = ['username','password','dswid','dsrid','semester','courseNr','mode','group_index','slot_index','study_number','anmelden_time'];
    const d = {};
    map.forEach(k=>{
        const el=$(k);
        if(!el) return;
        let v=el.value.trim(); // Trim whitespace
        if(el.type==='number'&&v!=='') {
            v=parseInt(v);
            // Enforce 1-based indices in UI; 0 is not accepted
            if ((k === 'group_index' || k === 'slot_index') && v <= 0) {
                throw new Error('Group and Slot Index must be greater than 1');
            }
            // Convert to 0-based for backend when provided
            if ((k === 'group_index' || k === 'slot_index') && v >= 1) {
                v = v - 1;
            }
        }
        if(el.type==='datetime-local'&&v) v=v.replace('T',' ') + ':00';
        if(v!==''&&v!=null) d[k]=v;
    });
    return d;
}

function clearFields() {
    const map = ['username','password','dswid','dsrid','semester','courseNr','group_index','slot_index','study_number','anmelden_time'];
    map.forEach(k => {
        const el = $(k);
        if (el) {
            el.value = '';
        }
    });
    // Reset mode to default (exam)
    document.querySelectorAll('.opt').forEach(x => x.classList.remove('active'));
    document.querySelector('.opt[data-mode="exam"]')?.classList.add('active');
    $('mode').value = 'exam';
    showStatus('All fields cleared!', true);
    // Set default time (1 hour in the future)
    setDefaultTime();
}

async function loadConfig(){
    let c = {};
    let hasConfig = false;
    
    // Prefer server-stored config
    try{ 
        const resp = await fetch('/api/user_config'); 
        const res = await resp.json(); 
        if(res && res.success && res.config){ 
            c = res.config; 
            hasConfig = true;
        } 
    }catch(e){}
    
    // Fallback to injected/window
    if(!hasConfig){ 
        if(window.EXISTING_CONFIG){ 
            c = window.EXISTING_CONFIG; 
            hasConfig = true;
        } 
    }
    
    // Fallback to localStorage
    if(!hasConfig){ 
        try{ 
            const stored = localStorage.getItem('tiss_config'); 
            if(stored){ 
                c = JSON.parse(stored); 
                hasConfig = true;
            } 
        }catch(e){} 
    }
    
    if(hasConfig && c && Object.keys(c).length){
        Object.keys(c).forEach(k=>{
            const el=$(k);
            if(!el||c[k]==null) return;
            
            // Skip loading anmelden_time - always use default (1 hour in future)
            if(k === 'anmelden_time') return;
            
            if(el.type==='datetime-local' && typeof c[k]==='string' && c[k].includes(' ')){
                el.value = c[k].replace(' ','T').substring(0,16);
            } else {
                el.value=c[k];
            }
        });
        
        if(c.mode){ 
            document.querySelectorAll('.opt').forEach(x=>x.classList.remove('active')); 
            document.querySelector(`.opt[data-mode="${c.mode}"]`)?.classList.add('active'); 
            $('mode').value=c.mode; 
        }
        showStatus('📋 Loaded saved configuration. Registration time set to 1 hour from now for safety.', true);
    }
    
    // Always set default time (1 hour in future) regardless of whether config was loaded
    setDefaultTime();
}

function wireMode(){ 
    document.querySelectorAll('.opt').forEach(opt=>{ 
        opt.addEventListener('click',()=>{ 
            document.querySelectorAll('.opt').forEach(x=>x.classList.remove('active')); 
            opt.classList.add('active'); 
            $('mode').value = opt.dataset.mode; 
        }); 
    }); 
}

$('validateBtn').addEventListener('click', async ()=>{
    try{ 
        const res = await fetch('/api/validate',{ 
            method:'POST', 
            headers:{'Content-Type':'application/json'}, 
            body: JSON.stringify(collect())
        }); 
        const data=await res.json(); 
        if(data.valid){ 
            showStatus('Configuration is valid', true);
        } else { 
            const msg = data.errors ? Object.entries(data.errors).map(([k,v])=>`${k}: ${v}`).join(', ') : (data.error||'Invalid'); 
            showStatus(msg,false);
        } 
    } catch(e){ 
        showStatus(e.message,false); 
    }
});

$('saveBtn').addEventListener('click', async ()=>{
    const cfg = collect();
    try{
        // Save to backend
        const resp = await fetch('/api/user_config', { 
            method:'POST', 
            headers:{'Content-Type':'application/json'}, 
            body: JSON.stringify(cfg)
        });
        const res = await resp.json();
        if(!res.success){ 
            throw new Error(res.message || 'Save failed'); 
        }
        // Keep local copy
        localStorage.setItem('tiss_config', JSON.stringify(cfg));
        showStatus('✅ Configuration saved!', true);
    } catch(e){ 
        showStatus(e.message,false); 
    }
});

$('sendAndGoBtn').addEventListener('click', async ()=>{
    try{
        const cfg = collect();
        showStatus('Sending request...', true);
        const r = await fetch('/api/requests',{ 
            method:'POST', 
            headers:{'Content-Type':'application/json'}, 
            body: JSON.stringify(cfg)
        });
        const d = await r.json();
        if(d.success){
            showStatus('Request queued. Redirecting to Requests...', true);
            window.location.href = '/requests';
        } else {
            showStatus(d.message||'Failed to send request', false);
        }
    }catch(e){ 
        showStatus(e.message, false); 
    }
});

$('clearBtn').addEventListener('click', clearFields);

async function logout(){ 
    try{ 
        await fetch('/auth/logout',{method:'POST'}); 
        window.location.href='/login'; 
    }catch(e){} 
}
$('logoutBtn').addEventListener('click', logout);

window.addEventListener('load', async ()=>{
    $('welcomeUser').textContent = (window.SESSION_USER) ? `Logged in as ${window.SESSION_USER}` : '';
    
    // Load configuration first (this will also set the default time)
    await loadConfig(); 
    wireMode();
});

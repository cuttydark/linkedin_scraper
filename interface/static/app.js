// State
let currentPerson = null;
let selectedIds = new Set();

// Navigation
document.querySelectorAll('.nav-item[data-screen]').forEach(item => {
  item.addEventListener('click', () => {
    const screen = item.dataset.screen;
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    item.classList.add('active');
    document.getElementById('screen-' + screen).classList.add('active');
    if (screen === 'leads') loadLeads();
    if (screen === 'session') loadSessionStatus();
  });
});

// -- SEARCH --

async function doSearch() {
  const url = document.getElementById('search-url').value.trim();
  if (!url) return;

  const btn = document.getElementById('btn-search');
  const banner = document.getElementById('search-banner');
  const card = document.getElementById('result-card');

  setBanner(banner, null);
  card.style.display = 'none';
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Buscando...';

  try {
    const res = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    const data = await res.json();

    if (!res.ok) {
      const msg = res.status === 429
        ? 'LinkedIn esta limitando las peticiones. Espera unos minutos.'
        : res.status === 401
        ? 'Sesion expirada. Ve a "Sesion LinkedIn" y recarga session.json.'
        : res.status === 404
        ? 'Perfil no encontrado o privado.'
        : data.detail || 'Error al buscar el perfil.';
      setBanner(banner, msg, 'error');
      return;
    }

    currentPerson = data;
    document.getElementById('r-name').textContent = data.name || '(sin nombre)';
    document.getElementById('r-meta').textContent = [data.role, data.company, data.location].filter(Boolean).join(' · ');
    document.getElementById('r-about').textContent = data.about ? data.about.slice(0, 200) + (data.about.length > 200 ? '...' : '') : '';
    card.style.display = 'block';

    const saveBtn = document.getElementById('btn-save');
    saveBtn.textContent = 'Guardar como lead';
    saveBtn.disabled = false;
    saveBtn.style.background = '';

  } catch (e) {
    setBanner(banner, 'Error de red. Asegurate de que la app esta corriendo.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Buscar';
  }
}

async function doSave() {
  if (!currentPerson) return;

  const btn = document.getElementById('btn-save');
  const banner = document.getElementById('search-banner');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Guardando...';

  try {
    const res = await fetch('/api/leads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentPerson),
    });

    if (res.ok) {
      btn.textContent = 'Guardado';
      btn.style.background = '#0369a1';
    } else {
      btn.disabled = false;
      btn.textContent = 'Guardar como lead';
      setBanner(banner, 'No se pudo guardar el lead.', 'error');
    }
  } catch (e) {
    btn.disabled = false;
    btn.textContent = 'Guardar como lead';
    setBanner(banner, 'Error de red al guardar.', 'error');
  }
}

document.getElementById('search-url').addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch();
});

// -- LEADS --

async function loadLeads() {
  const banner = document.getElementById('leads-banner');
  const name = document.getElementById('f-name').value;
  const company = document.getElementById('f-company').value;
  const role = document.getElementById('f-role').value;
  const location = document.getElementById('f-location').value;

  const params = new URLSearchParams();
  if (name) params.set('name', name);
  if (company) params.set('company', company);
  if (role) params.set('role', role);
  if (location) params.set('location', location);

  let leads;
  try {
    const res = await fetch('/api/leads?' + params.toString());
    if (!res.ok) throw new Error('Error ' + res.status);
    leads = await res.json();
  } catch (e) {
    setBanner(banner, 'No se pudieron cargar los leads. Asegurate de que la app esta corriendo.', 'error');
    return;
  }

  setBanner(banner, null);
  selectedIds.clear();
  updateBulkActions();

  document.getElementById('leads-count').textContent = leads.length + ' perfiles';
  const tbody = document.getElementById('leads-body');
  tbody.innerHTML = '';

  if (leads.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#94a3b8;padding:24px;">No hay leads guardados.</td></tr>';
    return;
  }

  leads.forEach(lead => {
    const tr = document.createElement('tr');
    const date = lead.saved_at ? new Date(lead.saved_at).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' }) : '';
    tr.innerHTML = `
      <td><input type="checkbox" data-id="${lead.id}" onchange="toggleSelect(${lead.id}, this)" /></td>
      <td style="font-weight:600">${esc(lead.name || '')}</td>
      <td style="color:#64748b">${esc(lead.role || '')}</td>
      <td style="color:#64748b">${esc(lead.company || '')}</td>
      <td style="color:#94a3b8;font-size:12px">${esc(lead.location || '')}</td>
      <td style="color:#94a3b8;font-size:12px">${date}</td>
      <td><a href="${safeHref(lead.linkedin_url)}" target="_blank" style="color:#3b5bdb;font-size:12px;text-decoration:none">Ver perfil</a></td>
    `;
    tbody.appendChild(tr);
  });
}

function toggleSelect(id, chk) {
  if (chk.checked) selectedIds.add(id);
  else selectedIds.delete(id);
  updateBulkActions();
}

function toggleAll(chk) {
  document.querySelectorAll('#leads-body input[type=checkbox]').forEach(c => {
    c.checked = chk.checked;
    const id = parseInt(c.dataset.id);
    if (chk.checked) selectedIds.add(id);
    else selectedIds.delete(id);
  });
  updateBulkActions();
}

function updateBulkActions() {
  const el = document.getElementById('bulk-actions');
  if (selectedIds.size > 0) {
    el.style.display = 'block';
    document.getElementById('bulk-count').textContent = selectedIds.size;
  } else {
    el.style.display = 'none';
  }
}

async function deleteSelected() {
  if (selectedIds.size === 0) return;
  if (!confirm('Eliminar ' + selectedIds.size + ' lead(s)?')) return;
  const results = await Promise.allSettled(
    [...selectedIds].map(id => fetch('/api/leads/' + id, { method: 'DELETE' }))
  );
  const failed = results.filter(r => r.status === 'rejected' || (r.value && !r.value.ok)).length;
  if (failed > 0) {
    setBanner(document.getElementById('leads-banner'), failed + ' lead(s) no pudieron eliminarse.', 'warning');
  }
  loadLeads();
}

function exportLeads() {
  const params = new URLSearchParams();
  const name = document.getElementById('f-name').value;
  const company = document.getElementById('f-company').value;
  const role = document.getElementById('f-role').value;
  const location = document.getElementById('f-location').value;
  if (name) params.set('name', name);
  if (company) params.set('company', company);
  if (role) params.set('role', role);
  if (location) params.set('location', location);
  window.location.href = '/api/export?' + params.toString();
}

async function exportSelected() {
  const res = await fetch('/api/leads');
  const all = await res.json();
  const filtered = all.filter(l => selectedIds.has(l.id));

  const header = 'name,role,company,location,linkedin_url,saved_at\n';
  const lines = filtered.map(l =>
    ['name', 'role', 'company', 'location', 'linkedin_url', 'saved_at'].map(k => '"' + (l[k] || '').toString().replace(/"/g, '""') + '"').join(',')
  ).join('\n');

  const blob = new Blob([header + lines], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'leads-seleccion.csv';
  a.click();
  URL.revokeObjectURL(url);
}

// -- SESSION --

async function loadSessionStatus() {
  const res = await fetch('/api/session');
  const data = await res.json();
  const line = document.getElementById('session-status-line');
  const info = document.getElementById('session-info');
  const dot = '<span class="status-dot ' + esc(data.status) + '"></span>';
  const labels = { active: 'Activa', expired: 'Expirada', missing: 'Sin sesion', error: 'Error' };
  line.innerHTML = dot + (labels[data.status] || esc(data.status));
  info.textContent = data.message || (data.session_file ? 'Archivo: ' + data.session_file : '');
}

async function reloadSession() {
  const btn = document.querySelector('#screen-session .btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Recargando...'; }
  try {
    await fetch('/api/session/reload', { method: 'POST' });
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Recargar session.json'; }
  }
  await loadSessionStatus();
}

// -- UTILS --

function setBanner(el, msg, type) {
  el.className = 'banner';
  el.textContent = '';
  if (msg) {
    el.classList.add(type || 'error');
    el.textContent = msg;
  }
}

function esc(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/** Returns url only if it uses http/https, otherwise '#' to prevent javascript: injection. */
function safeHref(url) {
  try {
    const u = new URL(url);
    return (u.protocol === 'https:' || u.protocol === 'http:') ? url : '#';
  } catch {
    return '#';
  }
}

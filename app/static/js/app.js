/* ============ UTILS ============ */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function toast(msg, type = 'info') {
    const container = $('#toastContainer');
    if (!container) return;
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    container.appendChild(t);
    setTimeout(() => t.remove(), 3500);
}

async function api(url, options = {}) {
    try {
        const res = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Error');
        return data;
    } catch (err) {
        toast(err.message, 'error');
        throw err;
    }
}

function formatDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '22-digit' });
}

function toLocalInput(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/* ============ SIDEBAR ============ */
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = $('#sidebar');
    const toggle = $('#menuToggle');
    const close = $('#sidebarClose');
    if (toggle) toggle.onclick = () => sidebar.classList.add('open');
    if (close) close.onclick = () => sidebar.classList.remove('open');

    // Fecha en topbar
    const today = $('#todayLabel');
    if (today) {
        today.textContent = new Date().toLocaleDateString('es-PE', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' });
    }
});

/* ============================================================
   ADMIN - USUARIOS
   ============================================================ */
if ($('#usersTable')) {
    let allUsers = [];

    async function loadUsers() {
        allUsers = await api('/api/users');
        renderUsers();
        renderStats();
        renderUnitFilter();
    }

    function renderStats() {
        $('#statTotal').textContent = allUsers.length;
        $('#statAdmin').textContent = allUsers.filter(u => u.role === 'admin').length;
        $('#statSup').textContent = allUsers.filter(u => u.role === 'supervisor').length;
        $('#statGuard').textContent = allUsers.filter(u => u.role === 'guardia').length;
    }

    function renderUnitFilter() {
        const units = [...new Set(allUsers.map(u => u.unit).filter(Boolean))];
        const sel = $('#filterUnit');
        sel.innerHTML = '<option value="">Todas las unidades</option>' +
            units.map(u => `<option value="${u}">${u}</option>`).join('');
    }

    function renderUsers() {
        const search = ($('#searchInput').value || '').toLowerCase();
        const role = $('#filterRole').value;
        const unit = $('#filterUnit').value;

        const filtered = allUsers.filter(u => {
            if (search && !u.name.toLowerCase().includes(search) && !u.code.toLowerCase().includes(search)) return false;
            if (role && u.role !== role) return false;
            if (unit && u.unit !== unit) return false;
            return true;
        });

        const tbody = $('#usersTable');
        if (!filtered.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Sin usuarios</td></tr>';
            return;
        }
        tbody.innerHTML = filtered.map(u => `
            <tr>
                <td><strong>${u.code}</strong></td>
                <td>${u.name}</td>
                <td>${u.unit || '—'}</td>
                <td>${u.post || '—'}</td>
                <td><span class="role-badge role-${u.role}">${u.role}</span></td>
                <td>${u.shift === 'noche' ? '🌙 Noche' : '☀️ Día'}</td>
                <td class="text-right">
                    <div class="action-btns">
                        <button class="icon-btn" onclick="editUser('${u.id}')" title="Editar">✏️</button>
                        <button class="icon-btn danger" onclick="deleteUser('${u.id}', '${u.name}')" title="Eliminar">🗑️</button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    window.openUserModal = function(user = null) {
        $('#userModal').classList.add('open');
        $('#userForm').reset();
        $('#userId').value = '';
        if (user) {
            $('#modalTitle').textContent = 'Editar usuario';
            $('#userId').value = user.id;
            $('#fCode').value = user.code;
            $('#fName').value = user.name;
            $('#fUnit').value = user.unit;
            $('#fPost').value = user.post;
            $('#fRole').value = user.role;
            $('#fShift').value = user.shift;
            $('#fPassword').required = false;
            $('#pwdHint').textContent = '(dejar vacío = no cambiar)';
        } else {
            $('#modalTitle').textContent = 'Nuevo usuario';
            $('#fPassword').required = true;
            $('#pwdHint').textContent = '(mín. 6)';
        }
    };

    window.closeUserModal = () => $('#userModal').classList.remove('open');

    window.editUser = (id) => {
        const u = allUsers.find(x => x.id === id);
        if (u) openUserModal(u);
    };

    window.deleteUser = async (id, name) => {
        if (!confirm(`¿Eliminar al usuario "${name}"? Esta acción no se puede deshacer.`)) return;
        try {
            await api(`/api/users/${id}`, { method: 'DELETE' });
            toast('Usuario eliminado', 'success');
            loadUsers();
        } catch (e) {}
    };

    $('#userForm').onsubmit = async (e) => {
        e.preventDefault();
        const id = $('#userId').value;
        const payload = {
            code: $('#fCode').value,
            name: $('#fName').value,
            unit: $('#fUnit').value,
            post: $('#fPost').value,
            role: $('#fRole').value,
            shift: $('#fShift').value
        };
        const pwd = $('#fPassword').value;
        if (pwd) payload.password = pwd;

        try {
            if (id) {
                await api(`/api/users/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
                toast('Usuario actualizado', 'success');
            } else {
                if (!pwd) { toast('La contraseña es obligatoria', 'error'); return; }
                payload.password = pwd;
                await api('/api/users', { method: 'POST', body: JSON.stringify(payload) });
                toast('Usuario creado', 'success');
            }
            closeUserModal();
            loadUsers();
        } catch (e) {}
    };

    ['searchInput', 'filterRole', 'filterUnit'].forEach(id => {
        const el = $(`#${id}`);
        if (el) el.addEventListener('input', renderUsers);
    });

    loadUsers();
}

/* ============================================================
   EVIDENCIA DE PATRULLAS
   ============================================================ */
if ($('#evidenceForm')) {
    let currentLocation = null;
    let photoDataUrls = [];
    let editingId = null;

    // Cargar datos del usuario
    async function loadSession() {
        const u = await api('/api/session');
        $('#autoUser').textContent = u.name;
        $('#autoUnit').textContent = u.unit || '—';
        $('#fTimestamp').value = toLocalInput(new Date().toISOString());
    }

    // GPS
    window.getGPS = function() {
        $('#autoGps').textContent = 'Obteniendo...';
        if (!navigator.geolocation) {
            $('#autoGps').textContent = 'No disponible';
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                currentLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                $('#autoGps').textContent = `${currentLocation.lat.toFixed(5)}, ${currentLocation.lng.toFixed(5)}`;
            },
            () => { $('#autoGps').textContent = 'Permiso denegado'; },
            { enableHighAccuracy: true, timeout: 10000 }
        );
    };

    // Selector patrulla
    $$('.patrol-btn').forEach(btn => {
        btn.onclick = () => {
            $$('.patrol-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            $('#fPatrol').value = btn.dataset.patrol;
        };
    });

    // Fotos
    $('#fPhotos').onchange = (e) => {
        Array.from(e.target.files).forEach(file => {
            const reader = new FileReader();
            reader.onload = (ev) => {
                photoDataUrls.push(ev.target.result);
                renderPhotos();
            };
            reader.readAsDataURL(file);
        });
        e.target.value = '';
    };

    function renderPhotos() {
        const container = $('#photoPreview');
        container.innerHTML = photoDataUrls.map((src, i) => `
            <div class="photo-thumb">
                <img src="${src}" alt="foto ${i+1}">
                <button type="button" class="photo-remove" onclick="removePhoto(${i})">✕</button>
            </div>
        `).join('');
    }

    window.removePhoto = (i) => {
        photoDataUrls.splice(i, 1);
        renderPhotos();
    };

    // Submit
    $('#evidenceForm').onsubmit = async (e) => {
        e.preventDefault();
        if (!photoDataUrls.length) { toast('Adjunta al menos una foto', 'error'); return; }

        const payload = {
            patrol_num: $('#fPatrol').value,
            paquete: $('#fPaquete').value,
            progresiva: $('#fProgresiva').value,
            margen: $('#fMargen').value,
            zona: $('#fZona').value,
            descripcion: $('#fDescripcion').value,
            photos: photoDataUrls,
            location: currentLocation,
            timestamp: $('#fTimestamp').value ? new Date($('#fTimestamp').value).toISOString() : null
        };

        try {
            if (editingId) {
                await api(`/api/patrol-evidence/${editingId}`, { method: 'PUT', body: JSON.stringify(payload) });
                toast('Registro actualizado', 'success');
            } else {
                await api('/api/patrol-evidence', { method: 'POST', body: JSON.stringify(payload) });
                toast('Evidencia guardada', 'success');
            }
            resetForm();
            loadEvidences();
        } catch (e) {}
    };

    window.resetForm = function() {
        $('#evidenceForm').reset();
        $$('.patrol-btn').forEach(b => b.classList.remove('active'));
        $('#fPatrol').value = '';
        photoDataUrls = [];
        editingId = null;
        renderPhotos();
        $('#fTimestamp').value = toLocalInput(new Date().toISOString());
    };

    // Listado
    window.loadEvidences = async function() {
        const params = new URLSearchParams();
        const p = $('#filterPatrol').value; if (p) params.set('patrol', p);
        const f = $('#filterFrom').value; if (f) params.set('from', new Date(f).toISOString());
        const t = $('#filterTo').value; if (t) params.set('to', new Date(t + 'T23:59:59').toISOString());
        const z = $('#filterZona').value; if (z) params.set('zona', z);

        const list = await api('/api/patrol-evidence?' + params.toString());
        renderEvidenceList(list);
        renderEvidenceStats(list);
    };

    function renderEvidenceStats(list) {
        const total = list.length;
        const byPatrol = {};
        list.forEach(e => {
            const k = e.patrol_num || '—';
            byPatrol[k] = (byPatrol[k] || 0) + 1;
        });
        const html = `<div class="stat-card"><div class="stat-value">${total}</div><div class="stat-label">Total registros</div></div>` +
            Object.entries(byPatrol).map(([k, v]) =>
                `<div class="stat-card"><div class="stat-value">${v}</div><div class="stat-label">Patrulla ${k}</div></div>`
            ).join('');
        $('#evidenceStats').innerHTML = html;
    }

    function renderEvidenceList(list) {
        const container = $('#evidenceList');
        if (!list.length) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📭</div><p>Sin registros aún</p></div>';
            return;
        }
        container.innerHTML = list.map(e => {
            const texto = `${e.user_name}, realizó ronda por Paquete ${e.paquete || '—'}, ${e.progresiva || '—'}, margen ${e.margen || '—'} ${e.zona}. ${e.descripcion}`;
            const fotos = (e.photos || []).slice(0, 2).map(src => `<img src="${src}" alt="evidencia">`).join('');
            return `
                <div class="evidence-card">
                    <div class="evidence-header">
                        <div class="evidence-meta">
                            <span class="evidence-date">🕒 ${formatDate(e.timestamp)}</span>
                            ${e.patrol_num ? `<span class="patrol-badge">Patrulla ${e.patrol_num}</span>` : ''}
                        </div>
                    </div>
                    <div class="evidence-text">${texto}</div>
                    ${fotos ? `<div class="evidence-photos">${fotos}</div>` : ''}
                    <div class="evidence-actions">
                        <button class="icon-btn" onclick="editEvidence('${e.id}')">✏️ Editar</button>
                        <button class="icon-btn danger" onclick="deleteEvidence('${e.id}')">🗑️ Eliminar</button>
                    </div>
                </div>
            `;
        }).join('');
    }

    window.editEvidence = async (id) => {
        const list = await api('/api/patrol-evidence');
        const e = list.find(x => x.id === id);
        if (!e) return;
        editingId = id;
        $('#fPatrol').value = e.patrol_num;
        $$('.patrol-btn').forEach(b => b.classList.toggle('active', b.dataset.patrol === e.patrol_num));
        $('#fPaquete').value = e.paquete;
        $('#fProgresiva').value = e.progresiva;
        $('#fMargen').value = e.margen;
        $('#fZona').value = e.zona;
        $('#fDescripcion').value = e.descripcion;
        photoDataUrls = [...(e.photos || [])];
        renderPhotos();
        if (e.timestamp) $('#fTimestamp').value = toLocalInput(e.timestamp);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    window.deleteEvidence = async (id) => {
        if (!confirm('¿Eliminar este registro?')) return;
        try {
            await api(`/api/patrol-evidence/${id}`, { method: 'DELETE' });
            toast('Registro eliminado', 'success');
            loadEvidences();
        } catch (e) {}
    };

    window.generatePDF = function() {
        // Asegurar título visible en impresión
        let title = $('.print-title');
        if (!title) {
            title = document.createElement('h1');
            title.className = 'print-title';
            title.textContent = 'EVIDENCIA DE PATRULLAS';
            $('#evidenceList').before(title);
        }
        window.print();
    };

    loadSession();
    getGPS();
    loadEvidences();
}
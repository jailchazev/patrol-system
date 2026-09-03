/* ============ UTILS ============ */
const getEl = (sel) => document.querySelector(sel);
const getEls = (sel) => document.querySelectorAll(sel);

function toast(msg, type = 'info') {
    const container = getEl('#toastContainer');
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

/**
 * Formatear fecha ISO a formato Perú (UTC-5)
 */
function formatDate(iso) {
    if (!iso) return '';
    try {
        const d = new Date(iso);
        // Restar 5 horas (UTC a Perú)
        const peruDate = new Date(d.getTime() - (5 * 60 * 60 * 1000));
        
        const pad = (n) => String(n).padStart(2, '0');
        const day = pad(peruDate.getUTCDate());
        const month = pad(peruDate.getUTCMonth() + 1);
        const year = peruDate.getUTCFullYear();
        let hours = peruDate.getUTCHours();
        const minutes = pad(peruDate.getUTCMinutes());
        const ampm = hours >= 12 ? 'p. m.' : 'a. m.';
        const displayHours = hours % 12 || 12;
        
        return `${day}/${month}/${year}, ${String(displayHours).padStart(2, '0')}:${minutes} ${ampm}`;
    } catch (e) {
        console.error('Error formateando fecha:', e);
        return iso;
    }
}

function toLocalInput(dateObj) {
    const pad = (n) => String(n).padStart(2, '0');
    return `${dateObj.getFullYear()}-${pad(dateObj.getMonth()+1)}-${pad(dateObj.getDate())}T${pad(dateObj.getHours())}:${pad(dateObj.getMinutes())}`;
}

function getPeruDateTime() {
    const now = new Date();
    const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
    return new Date(utc + (3600000 * -5));
}

/**
 * Convierte una cadena de fecha local (del input) a UTC, asumiendo que la entrada es hora de Perú (UTC-5)
 */
function peruTimeToUTC(localString) {
    if (!localString) {
        // Si está vacío, usar la hora actual de Perú convertida a UTC
        return getPeruDateTime().toISOString();
    }
    // 1. Forzamos que el string se interprete como UTC (ej: "2026-09-03T05:09:00Z")
    const date = new Date(localString + ":00Z");
    // 2. Le sumamos 5 horas para obtener el UTC real 
    // (Ej: Si el usuario puso 05:09 AM en Perú, el UTC real es 10:09 AM)
    date.setUTCHours(date.getUTCHours() + 5);
    return date.toISOString();
}

/* ============ SIDEBAR ============ */
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = getEl('#sidebar');
    const toggle = getEl('#menuToggle');
    const close = getEl('#sidebarClose');
    if (toggle) toggle.onclick = () => sidebar.classList.add('open');
    if (close) close.onclick = () => sidebar.classList.remove('open');

    const today = getEl('#todayLabel');
    if (today) {
        today.textContent = getPeruDateTime().toLocaleDateString('es-PE', { 
            weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' 
        });
    }
});

/* ============================================================
   ADMIN - USUARIOS
   ============================================================ */
if (getEl('#usersTable')) {
    let allUsers = [];

    async function loadUsers() {
        allUsers = await api('/api/users');
        renderUsers();
        renderStats();
        renderUnitFilter();
    }

    function renderStats() {
        getEl('#statTotal').textContent = allUsers.length;
        getEl('#statAdmin').textContent = allUsers.filter(u => u.role === 'admin').length;
        getEl('#statSup').textContent = allUsers.filter(u => u.role === 'supervisor').length;
        getEl('#statGuard').textContent = allUsers.filter(u => u.role === 'guardia').length;
    }

    function renderUnitFilter() {
        const units = [...new Set(allUsers.map(u => u.unit).filter(Boolean))];
        const sel = getEl('#filterUnit');
        sel.innerHTML = '<option value="">Todas las unidades</option>' +
            units.map(u => `<option value="${u}">${u}</option>`).join('');
    }

    function renderUsers() {
        const search = (getEl('#searchInput').value || '').toLowerCase();
        const role = getEl('#filterRole').value;
        const unit = getEl('#filterUnit').value;

        const filtered = allUsers.filter(u => {
            if (search && !u.name.toLowerCase().includes(search) && !u.code.toLowerCase().includes(search)) return false;
            if (role && u.role !== role) return false;
            if (unit && u.unit !== unit) return false;
            return true;
        });

        const tbody = getEl('#usersTable');
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
        getEl('#userModal').classList.add('open');
        getEl('#userForm').reset();
        getEl('#userId').value = '';
        if (user) {
            getEl('#modalTitle').textContent = 'Editar usuario';
            getEl('#userId').value = user.id;
            getEl('#fCode').value = user.code;
            getEl('#fName').value = user.name;
            getEl('#fUnit').value = user.unit;
            getEl('#fPost').value = user.post;
            getEl('#fRole').value = user.role;
            getEl('#fShift').value = user.shift;
            getEl('#fPassword').required = false;
            getEl('#pwdHint').textContent = '(dejar vacío = no cambiar)';
        } else {
            getEl('#modalTitle').textContent = 'Nuevo usuario';
            getEl('#fPassword').required = true;
            getEl('#pwdHint').textContent = '(mín. 6)';
        }
    };

    window.closeUserModal = () => getEl('#userModal').classList.remove('open');
    window.editUser = (id) => { const u = allUsers.find(x => x.id === id); if (u) window.openUserModal(u); };
    window.deleteUser = async (id, name) => {
        if (!confirm(`¿Eliminar al usuario "${name}"?`)) return;
        try { await api(`/api/users/${id}`, { method: 'DELETE' }); toast('Usuario eliminado', 'success'); loadUsers(); } catch (e) {}
    };

    getEl('#userForm').onsubmit = async (e) => {
        e.preventDefault();
        const id = getEl('#userId').value;
        const payload = {
            code: getEl('#fCode').value, name: getEl('#fName').value, unit: getEl('#fUnit').value,
            post: getEl('#fPost').value, role: getEl('#fRole').value, shift: getEl('#fShift').value
        };
        const pwd = getEl('#fPassword').value;
        if (pwd) payload.password = pwd;

        try {
            if (id) {
                await api(`/api/users/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
                toast('Usuario actualizado', 'success');
            } else {
                if (!pwd) { toast('La contraseña es obligatoria', 'error'); return; }
                await api('/api/users', { method: 'POST', body: JSON.stringify(payload) });
                toast('Usuario creado', 'success');
            }
            window.closeUserModal();
            loadUsers();
        } catch (e) {}
    };

    ['searchInput', 'filterRole', 'filterUnit'].forEach(id => {
        const el = getEl(`#${id}`);
        if (el) el.addEventListener('input', renderUsers);
    });

    loadUsers();
}

/* ============================================================
   EVIDENCIA DE PATRULLAS
   ============================================================ */
if (getEl('#evidenceForm')) {
    let currentLocation = null;
    let photoDataUrls = [];
    let editingId = null;

    async function loadSession() {
        try {
            const u = await api('/api/session');
            const autoUser = getEl('#autoUser'); if (autoUser) autoUser.textContent = u.name || '—';
            const autoUnit = getEl('#autoUnit'); if (autoUnit) autoUnit.textContent = u.unit || '—';
            const autoRoleLabel = getEl('#autoRoleLabel');
            if (autoRoleLabel && u.role) autoRoleLabel.textContent = u.role.charAt(0).toUpperCase() + u.role.slice(1);
            
            const fTimestamp = getEl('#fTimestamp');
            if (fTimestamp) fTimestamp.value = toLocalInput(getPeruDateTime());
            console.log('✅ Sesión cargada:', u);
        } catch (error) {
            console.error('❌ Error cargando sesión:', error);
        }
    }

    window.getGPS = function() {
        const autoGps = getEl('#autoGps');
        if (autoGps) autoGps.textContent = 'Obteniendo...';
        if (!navigator.geolocation) { if (autoGps) autoGps.textContent = 'No disponible'; return; }
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                currentLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                if (autoGps) autoGps.textContent = `${currentLocation.lat.toFixed(5)}, ${currentLocation.lng.toFixed(5)}`;
            },
            (err) => { if (autoGps) autoGps.textContent = 'Permiso denegado'; },
            { enableHighAccuracy: true, timeout: 10000 }
        );
    };

    const patrolBtns = getEls('.patrol-btn');
    if (patrolBtns.length > 0) {
        patrolBtns.forEach(btn => {
            btn.onclick = function() {
                patrolBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                const fPatrol = getEl('#fPatrol');
                if (fPatrol) fPatrol.value = this.dataset.patrol;
            };
        });
    }

    // Manejo de fotos (Cámara y Galería)
    function handlePhotoSelect(files) {
        Array.from(files).forEach(file => {
            const reader = new FileReader();
            reader.onload = (ev) => {
                photoDataUrls.push(ev.target.result);
                window.renderPhotos();
            };
            reader.readAsDataURL(file);
        });
    }

    const fPhotosCamera = getEl('#fPhotosCamera');
    if (fPhotosCamera) {
        fPhotosCamera.onchange = (e) => { handlePhotoSelect(e.target.files); e.target.value = ''; };
    }

    const fPhotosGallery = getEl('#fPhotosGallery');
    if (fPhotosGallery) {
        fPhotosGallery.onchange = (e) => { handlePhotoSelect(e.target.files); e.target.value = ''; };
    }

    window.renderPhotos = function() {
        const container = getEl('#photoPreview');
        if (!container) return;
        if (photoDataUrls.length === 0) { container.innerHTML = ''; return; }
        container.innerHTML = photoDataUrls.map((src, i) => `
            <div class="photo-thumb">
                <img src="${src}" alt="foto ${i+1}">
                <button type="button" class="photo-remove" onclick="window.removePhoto(${i})">✕</button>
            </div>
        `).join('');
    };

    window.removePhoto = (i) => {
        photoDataUrls.splice(i, 1);
        window.renderPhotos();
    };

    const evidenceForm = getEl('#evidenceForm');
    if (evidenceForm) {
        evidenceForm.onsubmit = async (e) => {
            e.preventDefault();
            if (!photoDataUrls.length) { toast('Adjunta al menos una foto', 'error'); return; }

            const payload = {
                patrol_num: getEl('#fPatrol')?.value || '',
                paquete: getEl('#fPaquete')?.value || '',
                progresiva: getEl('#fProgresiva')?.value || '',
                margen: getEl('#fMargen')?.value || '',
                zona: getEl('#fZona')?.value || '',
                descripcion: getEl('#fDescripcion')?.value || '',
                photos: photoDataUrls,
                location: currentLocation,
                timestamp: peruTimeToUTC(getEl('#fTimestamp')?.value)
            };

            try {
                if (editingId) {
                    await api(`/api/patrol-evidence/${editingId}`, { method: 'PUT', body: JSON.stringify(payload) });
                    toast('Registro actualizado', 'success');
                } else {
                    await api('/api/patrol-evidence', { method: 'POST', body: JSON.stringify(payload) });
                    toast('Evidencia guardada', 'success');
                }
                window.resetForm();
                await window.loadEvidences();
            } catch (error) {
                console.error('❌ Error al guardar:', error);
            }
        };
    }

    window.resetForm = function() {
        const evidenceForm = getEl('#evidenceForm');
        if (evidenceForm) evidenceForm.reset();
        const pBtns = getEls('.patrol-btn');
        if (pBtns) pBtns.forEach(b => b.classList.remove('active'));
        const fPatrol = getEl('#fPatrol');
        if (fPatrol) fPatrol.value = '';
        photoDataUrls = [];
        editingId = null;
        window.renderPhotos();
        const fTimestamp = getEl('#fTimestamp');
        if (fTimestamp) fTimestamp.value = toLocalInput(getPeruDateTime());
    };

    window.loadEvidences = async function() {
        const params = new URLSearchParams();
        const filterPatrol = getEl('#filterPatrol');
        const filterFrom = getEl('#filterFrom');
        const filterTo = getEl('#filterTo');
        const filterZona = getEl('#filterZona');
        
        if (filterPatrol?.value) params.set('patrol', filterPatrol.value);
        if (filterFrom?.value) params.set('from', new Date(filterFrom.value).toISOString());
        if (filterTo?.value) params.set('to', new Date(filterTo.value + 'T23:59:59').toISOString());
        if (filterZona?.value) params.set('zona', filterZona.value);

        try {
            const list = await api('/api/patrol-evidence?' + params.toString());
            renderEvidenceList(list);
            renderEvidenceStats(list);
        } catch (error) {
            console.error('❌ Error cargando evidencias:', error);
        }
    };

    function renderEvidenceStats(list) {
        const container = getEl('#evidenceStats');
        if (!container) return;
        const total = list.length;
        const byPatrol = {};
        list.forEach(e => { const k = e.patrol_num || '—'; byPatrol[k] = (byPatrol[k] || 0) + 1; });
        
        const html = `<div class="stat-card"><div class="stat-value">${total}</div><div class="stat-label">Total registros</div></div>` +
            Object.entries(byPatrol).map(([k, v]) => `<div class="stat-card"><div class="stat-value">${v}</div><div class="stat-label">Patrulla ${k}</div></div>`).join('');
        container.innerHTML = html;
    }

    function renderEvidenceList(list) {
        const container = getEl('#evidenceList');
        if (!container) return;
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
                        <button class="icon-btn" onclick="window.editEvidence('${e.id}')">✏️ Editar</button>
                        <button class="icon-btn danger" onclick="window.deleteEvidence('${e.id}')">🗑️ Eliminar</button>
                    </div>
                </div>
            `;
        }).join('');
    }

    window.editEvidence = async (id) => {
        try {
            const list = await api('/api/patrol-evidence');
            const e = list.find(x => x.id === id);
            if (!e) return;
            editingId = id;
            
            const fPatrol = getEl('#fPatrol'); if (fPatrol) fPatrol.value = e.patrol_num;
            const pBtns = getEls('.patrol-btn');
            if (pBtns) pBtns.forEach(b => b.classList.toggle('active', b.dataset.patrol === e.patrol_num));
            
            const fPaquete = getEl('#fPaquete'); if (fPaquete) fPaquete.value = e.paquete;
            const fProgresiva = getEl('#fProgresiva'); if (fProgresiva) fProgresiva.value = e.progresiva;
            const fMargen = getEl('#fMargen'); if (fMargen) fMargen.value = e.margen;
            const fZona = getEl('#fZona'); if (fZona) fZona.value = e.zona;
            const fDescripcion = getEl('#fDescripcion'); if (fDescripcion) fDescripcion.value = e.descripcion;
            
            photoDataUrls = [...(e.photos || [])];
            window.renderPhotos();
            
            if (e.timestamp) {
                const fTimestamp = getEl('#fTimestamp');
                if (fTimestamp) {
                    const utcDate = new Date(e.timestamp);
                    const peruDate = new Date(utcDate.getTime() - (5 * 60 * 60 * 1000));
                    fTimestamp.value = toLocalInput(peruDate);
                }
            }
            window.scrollTo({ top: 0, behavior: 'smooth' });
            toast('Editando registro...', 'info');
        } catch (error) { console.error('❌ Error al editar:', error); }
    };

    window.deleteEvidence = async (id) => {
        if (!confirm('¿Eliminar este registro?')) return;
        try {
            await api(`/api/patrol-evidence/${id}`, { method: 'DELETE' });
            toast('Registro eliminado', 'success');
            window.loadEvidences();
        } catch (error) { console.error('❌ Error al eliminar:', error); }
    };

    window.generatePDF = async function() {
        const params = new URLSearchParams();
        const filterPatrol = getEl('#filterPatrol');
        const filterFrom = getEl('#filterFrom');
        const filterTo = getEl('#filterTo');
        const filterZona = getEl('#filterZona');
        
        if (filterPatrol?.value) params.set('patrol', filterPatrol.value);
        if (filterFrom?.value) params.set('from', new Date(filterFrom.value).toISOString());
        if (filterTo?.value) params.set('to', new Date(filterTo.value + 'T23:59:59').toISOString());
        if (filterZona?.value) params.set('zona', filterZona.value);
        
        try {
            toast('Generando PDF...', 'info');
            const response = await fetch('/api/patrol-evidence/pdf?' + params.toString());
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || `Error ${response.status}`);
            }
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `evidencia_patrullas_${new Date().getTime()}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            toast('PDF generado exitosamente', 'success');
        } catch (error) {
            console.error('❌ Error al generar PDF:', error);
            toast(error.message || 'Error al generar PDF', 'error');
        }
    };

    console.log('🚀 Inicializando módulo de evidencias...');
    loadSession();
    window.getGPS();
    window.loadEvidences();
}
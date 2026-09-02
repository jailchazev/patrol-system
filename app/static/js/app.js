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
    return d.toLocaleString('es-PE', { 
        day: '2-digit', 
        month: '2-digit', 
        year: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
    });
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
        today.textContent = new Date().toLocaleDateString('es-PE', { 
            weekday: 'long', 
            day: '2-digit', 
            month: 'long', 
            year: 'numeric' 
        });
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
                        <button class="icon-btn danger" onclick="deleteUser('${u.id}', '${u.name}')" title="Eliminar">️</button>
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

    // Cargar datos del usuario y mostrar ROL dinámico
    async function loadSession() {
        try {
            const u = await api('/api/session');
            
            // Mostrar nombre del usuario
            const autoUser = $('#autoUser');
            if (autoUser) autoUser.textContent = u.name || '—';
            
            // Mostrar unidad
            const autoUnit = $('#autoUnit');
            if (autoUnit) autoUnit.textContent = u.unit || '—';
            
            // MOSTRAR ROL DINÁMICO (Resguardo, Guardia, etc.)
            const autoRoleLabel = $('#autoRoleLabel');
            if (autoRoleLabel && u.role) {
                const rol = u.role.charAt(0).toUpperCase() + u.role.slice(1);
                autoRoleLabel.textContent = rol;
            }
            
            // Fecha/hora actual
            const fTimestamp = $('#fTimestamp');
            if (fTimestamp) fTimestamp.value = toLocalInput(new Date().toISOString());
            
            console.log('✅ Sesión cargada:', u);
        } catch (error) {
            console.error('❌ Error cargando sesión:', error);
            toast('Error al cargar datos del usuario', 'error');
        }
    }

    // GPS
    window.getGPS = function() {
        const autoGps = $('#autoGps');
        if (autoGps) autoGps.textContent = 'Obteniendo...';
        
        if (!navigator.geolocation) {
            if (autoGps) autoGps.textContent = 'No disponible';
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                currentLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                if (autoGps) autoGps.textContent = `${currentLocation.lat.toFixed(5)}, ${currentLocation.lng.toFixed(5)}`;
                console.log('📍 GPS obtenido:', currentLocation);
            },
            (err) => { 
                if (autoGps) autoGps.textContent = 'Permiso denegado';
                console.warn('⚠️ GPS denegado:', err);
            },
            { enableHighAccuracy: true, timeout: 10000 }
        );
    };

    // Selector de patrulla - FUNCIONAL
    const patrolBtns = $$('.patrol-btn');
    if (patrolBtns.length > 0) {
        patrolBtns.forEach(btn => {
            btn.onclick = function() {
                // Quitar active de todos
                patrolBtns.forEach(b => b.classList.remove('active'));
                // Agregar active al clickeado
                this.classList.add('active');
                // Guardar valor
                const fPatrol = $('#fPatrol');
                if (fPatrol) fPatrol.value = this.dataset.patrol;
                console.log('🎯 Patrulla seleccionada:', this.dataset.patrol);
            };
        });
    }

    // Fotos - FUNCIONAL
    const fPhotos = $('#fPhotos');
    if (fPhotos) {
        fPhotos.onchange = (e) => {
            console.log(' Fotos seleccionadas:', e.target.files.length);
            Array.from(e.target.files).forEach(file => {
                const reader = new FileReader();
                reader.onload = (ev) => {
                    photoDataUrls.push(ev.target.result);
                    renderPhotos();
                };
                reader.readAsDataURL(file);
            });
            e.target.value = ''; // Reset para permitir seleccionar la misma foto
        };
    }

    function renderPhotos() {
        const container = $('#photoPreview');
        if (!container) return;
        
        if (photoDataUrls.length === 0) {
            container.innerHTML = '';
            return;
        }
        
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

    // Submit del formulario - FUNCIONAL
    const evidenceForm = $('#evidenceForm');
    if (evidenceForm) {
        evidenceForm.onsubmit = async (e) => {
            e.preventDefault();
            
            console.log('📝 Formulario enviado');
            
            if (!photoDataUrls.length) { 
                toast('Adjunta al menos una foto', 'error'); 
                return; 
            }

            const fPatrol = $('#fPatrol');
            const fPaquete = $('#fPaquete');
            const fProgresiva = $('#fProgresiva');
            const fMargen = $('#fMargen');
            const fZona = $('#fZona');
            const fDescripcion = $('#fDescripcion');
            const fTimestamp = $('#fTimestamp');

            const payload = {
                patrol_num: fPatrol ? fPatrol.value : '',
                paquete: fPaquete ? fPaquete.value : '',
                progresiva: fProgresiva ? fProgresiva.value : '',
                margen: fMargen ? fMargen.value : '',
                zona: fZona ? fZona.value : '',
                descripcion: fDescripcion ? fDescripcion.value : '',
                photos: photoDataUrls,
                location: currentLocation,
                timestamp: (fTimestamp && fTimestamp.value) ? new Date(fTimestamp.value).toISOString() : null
            };

            console.log(' Payload:', payload);

            try {
                if (editingId) {
                    await api(`/api/patrol-evidence/${editingId}`, { 
                        method: 'PUT', 
                        body: JSON.stringify(payload) 
                    });
                    toast('Registro actualizado', 'success');
                } else {
                    const saved = await api('/api/patrol-evidence', { 
                        method: 'POST', 
                        body: JSON.stringify(payload) 
                    });
                    console.log('✅ Evidencia guardada:', saved);
                    toast('Evidencia guardada', 'success');
                }
                resetForm();
                await loadEvidences();
            } catch (error) {
                console.error('❌ Error al guardar:', error);
            }
        };
    }

    window.resetForm = function() {
        const evidenceForm = $('#evidenceForm');
        if (evidenceForm) evidenceForm.reset();
        
        const patrolBtns = $$('.patrol-btn');
        if (patrolBtns) patrolBtns.forEach(b => b.classList.remove('active'));
        
        const fPatrol = $('#fPatrol');
        if (fPatrol) fPatrol.value = '';
        
        photoDataUrls = [];
        editingId = null;
        renderPhotos();
        
        const fTimestamp = $('#fTimestamp');
        if (fTimestamp) fTimestamp.value = toLocalInput(new Date().toISOString());
    };

    // Listado de evidencias
    window.loadEvidences = async function() {
        console.log(' Cargando evidencias...');
        
        const params = new URLSearchParams();
        const filterPatrol = $('#filterPatrol');
        const filterFrom = $('#filterFrom');
        const filterTo = $('#filterTo');
        const filterZona = $('#filterZona');
        
        if (filterPatrol && filterPatrol.value) params.set('patrol', filterPatrol.value);
        if (filterFrom && filterFrom.value) params.set('from', new Date(filterFrom.value).toISOString());
        if (filterTo && filterTo.value) params.set('to', new Date(filterTo.value + 'T23:59:59').toISOString());
        if (filterZona && filterZona.value) params.set('zona', filterZona.value);

        try {
            const list = await api('/api/patrol-evidence?' + params.toString());
            console.log('✅ Evidencias recibidas:', list.length);
            
            renderEvidenceList(list);
            renderEvidenceStats(list);
        } catch (error) {
            console.error('❌ Error cargando evidencias:', error);
        }
    };

    function renderEvidenceStats(list) {
        const container = $('#evidenceStats');
        if (!container) return;
        
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
        container.innerHTML = html;
    }

    function renderEvidenceList(list) {
        const container = $('#evidenceList');
        if (!container) return;
        
        if (!list.length) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon"></div><p>Sin registros aún</p></div>';
            return;
        }
        
        container.innerHTML = list.map(e => {
            const texto = `${e.user_name}, realizó ronda por Paquete ${e.paquete || '—'}, ${e.progresiva || '—'}, margen ${e.margen || '—'} ${e.zona}. ${e.descripcion}`;
            const fotos = (e.photos || []).slice(0, 2).map(src => `<img src="${src}" alt="evidencia">`).join('');
            return `
                <div class="evidence-card">
                    <div class="evidence-header">
                        <div class="evidence-meta">
                            <span class="evidence-date"> ${formatDate(e.timestamp)}</span>
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
        try {
            const list = await api('/api/patrol-evidence');
            const e = list.find(x => x.id === id);
            if (!e) return;
            
            editingId = id;
            
            const fPatrol = $('#fPatrol');
            if (fPatrol) fPatrol.value = e.patrol_num;
            
            const patrolBtns = $$('.patrol-btn');
            if (patrolBtns) {
                patrolBtns.forEach(b => {
                    b.classList.toggle('active', b.dataset.patrol === e.patrol_num);
                });
            }
            
            const fPaquete = $('#fPaquete');
            if (fPaquete) fPaquete.value = e.paquete;
            
            const fProgresiva = $('#fProgresiva');
            if (fProgresiva) fProgresiva.value = e.progresiva;
            
            const fMargen = $('#fMargen');
            if (fMargen) fMargen.value = e.margen;
            
            const fZona = $('#fZona');
            if (fZona) fZona.value = e.zona;
            
            const fDescripcion = $('#fDescripcion');
            if (fDescripcion) fDescripcion.value = e.descripcion;
            
            photoDataUrls = [...(e.photos || [])];
            renderPhotos();
            
            if (e.timestamp) {
                const fTimestamp = $('#fTimestamp');
                if (fTimestamp) fTimestamp.value = toLocalInput(e.timestamp);
            }
            
            window.scrollTo({ top: 0, behavior: 'smooth' });
            toast('Editando registro...', 'info');
        } catch (error) {
            console.error('❌ Error al editar:', error);
        }
    };

    window.deleteEvidence = async (id) => {
        if (!confirm('¿Eliminar este registro?')) return;
        try {
            await api(`/api/patrol-evidence/${id}`, { method: 'DELETE' });
            toast('Registro eliminado', 'success');
            loadEvidences();
        } catch (error) {
            console.error('❌ Error al eliminar:', error);
        }
    };

    window.generatePDF = async function() {
        const params = new URLSearchParams();
        const filterPatrol = $('#filterPatrol');
        const filterFrom = $('#filterFrom');
        const filterTo = $('#filterTo');
        const filterZona = $('#filterZona');
        
        if (filterPatrol && filterPatrol.value) params.set('patrol', filterPatrol.value);
        if (filterFrom && filterFrom.value) params.set('from', new Date(filterFrom.value).toISOString());
        if (filterTo && filterTo.value) params.set('to', new Date(filterTo.value + 'T23:59:59').toISOString());
        if (filterZona && filterZona.value) params.set('zona', filterZona.value);
        
        try {
            toast('Generando PDF...', 'info');
            
            const response = await fetch('/api/patrol-evidence/pdf?' + params.toString());
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Error al generar PDF');
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
            toast(error.message, 'error');
        }
    };

    // INICIALIZAR
    console.log('🚀 Inicializando módulo de evidencias...');
    loadSession();
    getGPS();
    loadEvidences();
}
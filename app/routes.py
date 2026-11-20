import os
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file, Response
from flask_login import login_user, logout_user, login_required, current_user
from flask import session
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime
from app import db
from app.models import User, PatrolEvidence, CompanyMembership
from app.tenancy import current_company_id, current_membership, available_memberships

# ============ BLUEPRINTS ============
auth_bp = Blueprint('auth', __name__)
main_bp = Blueprint('main', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Acceso no autorizado'}), 403
        membership = current_membership()
        if membership.role_key != 'company_admin':
            return jsonify({'error': 'Acceso no autorizado'}), 403
        current_company_id()
        return f(*args, **kwargs)
    return decorated

# ============ AUTENTICACIÓN ============
@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        memberships = available_memberships()
        if len(memberships) != 1 and not current_company_id(required=False):
            return redirect(url_for('auth.company_selector'))
        membership = current_membership(required=False)
        if membership and membership.role_key == 'company_admin':
            return redirect(url_for('main.admin_page'))
        return redirect(url_for('main.evidence_page'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        memberships = available_memberships()
        if len(memberships) != 1 and not current_company_id(required=False):
            return redirect(url_for('auth.company_selector'))
        if current_membership(required=False) and current_membership(required=False).role_key == 'company_admin':
            return redirect(url_for('main.admin_page'))
        return redirect(url_for('main.evidence_page'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        password = request.form.get('password', '')
        user = User.query.filter_by(code=code).first()

        if user and check_password_hash(user.password_hash, password):
            session.clear()
            login_user(user, remember=True)
            memberships = available_memberships()
            if len(memberships) != 1:
                return redirect(url_for('auth.company_selector'))
            membership = current_membership(required=False)
            if membership and membership.role_key == 'company_admin':
                return redirect(url_for('main.admin_page'))
            return redirect(url_for('main.evidence_page'))
        flash('Código o contraseña incorrectos', 'error')

    return render_template('login.html')

@auth_bp.route('/companies/select')
@login_required
def company_selector():
    return render_template('company_select.html')


@auth_bp.route('/api/companies', methods=['GET'])
@login_required
def list_available_companies():
    memberships = available_memberships()
    selected_id = session.get('active_company_id')
    return jsonify([
        {
            'id': membership.company_id,
            'name': membership.company.name,
            'slug': membership.company.slug,
            'status': membership.company.status,
            'role': membership.role_key,
            'selected': membership.company_id == selected_id,
        }
        for membership in memberships
    ])


@auth_bp.route('/api/companies/select', methods=['POST'])
@login_required
def select_company():
    data = request.get_json(silent=True) or request.form
    company_id = str(data.get('company_id') or '').strip()
    membership = next(
        (m for m in available_memberships() if m.company_id == company_id),
        None,
    )
    if membership is None:
        return jsonify({'error': 'No tienes acceso activo a esa empresa'}), 403

    # El ID recibido solo selecciona entre membresías ya verificadas en servidor.
    session['active_company_id'] = membership.company_id
    if db.engine.dialect.name == 'postgresql':
        db.session.execute(
            text("SELECT set_config('app.current_company_id', :company_id, true)"),
            {'company_id': membership.company_id},
        )
    destination = url_for('main.admin_page') if membership.role_key == 'company_admin' else url_for('main.evidence_page')
    return jsonify({
        'success': True,
        'company': {'id': membership.company_id, 'name': membership.company.name},
        'redirect_url': destination,
    })


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/session')
@login_required
def session_info():
    return jsonify(current_user.to_dict())

# ============ PANEL ADMIN ============
@main_bp.route('/admin')
@login_required
@admin_required
def admin_page():
    return render_template('admin.html')

@main_bp.route('/api/users', methods=['GET'])
@login_required
@admin_required
def list_users():
    company_id = current_company_id()
    rows = db.session.query(User, CompanyMembership).join(
        CompanyMembership, CompanyMembership.legacy_user_id == User.id
    ).filter(
        CompanyMembership.company_id == company_id
    ).order_by(User.created_at.desc()).all()
    payload = []
    for user, membership in rows:
        item = user.to_dict()
        item['role'] = membership.role_key
        payload.append(item)
    return jsonify(payload)

@main_bp.route('/api/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    data = request.get_json() or {}
    code = (data.get('code') or '').strip().upper()
    name = (data.get('name') or '').strip()
    password = data.get('password') or ''

    if not code or not name or not password:
        return jsonify({'error': 'Código, nombre y contraseña son obligatorios'}), 400
    if len(password) < 6:
        return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
    company_id = current_company_id()
    if User.query.filter_by(code=code).first():
        return jsonify({'error': f'El código {code} ya está registrado'}), 400

    user = User(
        code=code,
        name=name,
        unit=data.get('unit', '').strip(),
        role=data.get('role', 'guardia'),
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.flush()
    membership = CompanyMembership(
        company_id=company_id,
        legacy_user_id=user.id,
        role_key='company_admin' if user.role == 'admin' else ('supervisor' if user.role == 'supervisor' else 'guard'),
    )
    db.session.add(membership)
    db.session.commit()
    payload = user.to_dict()
    payload['role'] = membership.role_key
    return jsonify(payload), 201

@main_bp.route('/api/users/<user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    user = User.query.join(CompanyMembership, CompanyMembership.legacy_user_id == User.id).filter(User.id == user_id, CompanyMembership.company_id == current_company_id()).first_or_404()
    data = request.get_json() or {}

    new_code = (data.get('code') or '').strip().upper()
    if new_code and new_code != user.code:
        if User.query.filter_by(code=new_code).first():
            return jsonify({'error': f'El código {new_code} ya existe'}), 400
        user.code = new_code

    if data.get('name'):
        user.name = data['name'].strip()
    user.unit = (data.get('unit') or '').strip()
    if data.get('role'):
        user.role = data['role']
        membership = current_membership()
        membership.role_key = (
            'company_admin' if user.role == 'admin' else
            'supervisor' if user.role == 'supervisor' else 'guard'
        )
    if data.get('password'):
        if len(data['password']) < 6:
            return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
        user.password_hash = generate_password_hash(data['password'])

    db.session.commit()
    return jsonify(user.to_dict())

@main_bp.route('/api/users/<user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    membership = CompanyMembership.query.filter_by(
        legacy_user_id=user_id,
        company_id=current_company_id(),
    ).first_or_404()
    if user_id == current_user.id:
        return jsonify({'error': 'No puedes eliminar tu propia cuenta'}), 400
    # Revoca el acceso solo a esta empresa; conserva la identidad y sus evidencias históricas.
    db.session.delete(membership)
    db.session.commit()
    return jsonify({'ok': True})

# ============ EVIDENCIA DE PATRULLAS ============
@main_bp.route('/evidencia')
@login_required
def evidence_page():
    """ESTA ES LA RUTA QUE FALTABA Y CAUSABA EL ERROR"""
    return render_template('patrol_evidence.html')

@main_bp.route('/api/patrol-evidence', methods=['POST'])
@login_required
def create_evidence():
    """Crear evidencia con manejo robusto de errores."""
    import traceback
    from app.cloudinary_service import upload_multiple_images
    
    try:
        data = request.get_json(silent=True) or {}
    except Exception as e:
        print(f"❌ Error parseando JSON: {e}")
        return jsonify({'error': 'Datos inválidos'}), 400

    # Validaciones básicas
    if not data.get('descripcion'):
        return jsonify({'error': 'La descripción es obligatoria'}), 400
    
    photos = data.get('photos') or []
    if not isinstance(photos, list) or not 1 <= len(photos) <= 2:
        return jsonify({'error': 'Adjunta una o dos fotografías válidas'}), 400

    print("="*60)
    print(f"📝 NUEVA EVIDENCIA - Usuario: {current_user.name}")
    print(f"📸 Fotos recibidas: {len(photos)}")
    print(f"📝 Descripción: {data.get('descripcion', '')[:50]}...")
    print("="*60)

    photo_urls = []
    
    try:
        # Intentar subir imágenes a Cloudinary
        print("🔄 Iniciando subida a Cloudinary...")
        photo_urls = upload_multiple_images(photos)
        
        if len(photo_urls) != min(len(photos), 2):
            db.session.rollback()
            return jsonify({'error': 'No se pudieron subir todas las fotos. La evidencia no fue guardada; vuelve a intentarlo.'}), 502

        print(f"✅ Cloudinary completado. URLs: {len(photo_urls)} imágenes")
        
    except Exception as e:
        print(f"Error en Cloudinary: {e}")
        db.session.rollback()
        return jsonify({'error': 'No se pudieron subir las fotografías; la evidencia no fue guardada.'}), 502
        
    try:
        # Preparar payload para Google Sheets
        payload = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_role': current_membership().role_key,
            'user_name': current_user.name,
            'patrol_num': data.get('patrol_num', ''),
            'paquete': data.get('paquete', ''),
            'progresiva': data.get('progresiva', ''),
            'margen': data.get('margen', ''),
            'zona': data.get('zona', ''),
            'descripcion': data['descripcion'].strip(),
            'photo_urls': photo_urls,
            'location': data.get('location')
        }
        
        # Enviar a Google Sheets webhook
        webhook_url = os.environ.get('GOOGLE_SHEETS_WEBHOOK_URL')
        
        if webhook_url:
            try:
                print(" Enviando a Google Sheets...")
                response = requests.post(
                    webhook_url, 
                    json=payload, 
                    headers={'Content-Type': 'application/json'},
                    timeout=10  # Timeout de 10 segundos
                )
                
                if response.status_code == 200:
                    print("✅ Google Sheets: Datos guardados correctamente")
                else:
                    print(f"️ Google Sheets respondió: {response.status_code}")
            except Exception as e:
                print(f"⚠️ Error enviando a Google Sheets: {e}")
                # No fallamos la petición por esto
        else:
            print("⚠️ GOOGLE_SHEETS_WEBHOOK_URL no configurado")
        
        # Guardar en BD local (SIEMPRE, incluso si falla lo demás)
        print("💾 Guardando en base de datos local...")
        evidence = PatrolEvidence(
            company_id=current_company_id(),
            user_id=current_user.id,
            patrol_num=data.get('patrol_num', ''),
            paquete=data.get('paquete', ''),
            progresiva=data.get('progresiva', ''),
            margen=data.get('margen', ''),
            zona=data.get('zona', ''),
            descripcion=data['descripcion'].strip(),
            photos=photo_urls if photo_urls else [],  # URLs o lista vacía
            location=data.get('location'),
            timestamp=datetime.utcnow()
        )
        db.session.add(evidence)
        db.session.commit()
        
        print(f"✅ EVIDENCIA GUARDADA - ID: {evidence.id}")
        print("="*60)
        
        return jsonify({
            'success': True, 
            'message': 'Evidencia guardada correctamente',
            'photo_urls': photo_urls,
            'warning': 'Algunas imágenes no se pudieron subir' if not photo_urls else None
        }), 201
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO AL GUARDAR: {e}")
        print(traceback.format_exc())
        print("="*60)
        
        # Rollback por seguridad
        db.session.rollback()
        
        return jsonify({
            'error': 'Error al guardar la evidencia',
            'details': str(e) if os.environ.get('FLASK_ENV') == 'development' else None
        }), 500

@main_bp.route('/api/patrol-evidence', methods=['GET'])
@login_required
def list_evidences():
    query = PatrolEvidence.query.filter(PatrolEvidence.company_id == current_company_id())
    if current_membership().role_key != 'company_admin':
        query = query.filter(PatrolEvidence.user_id == current_user.id)
    
    # Orden ascendente (más antiguo primero)
    evidences = query.order_by(PatrolEvidence.timestamp.asc()).all()
    return jsonify([e.to_dict() for e in evidences])

@main_bp.route('/api/patrol-evidence/<evidence_id>', methods=['PUT'])
@login_required
def update_evidence(evidence_id):
    evidence = PatrolEvidence.query.filter_by(id=evidence_id, company_id=current_company_id()).first_or_404()
    if current_membership().role_key != 'company_admin' and evidence.user_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403

    data = request.get_json() or {}
    for field in ['patrol_num', 'paquete', 'progresiva', 'margen', 'zona', 'descripcion', 'photos']:
        if field in data:
            setattr(evidence, field, data[field])
    
    db.session.commit()
    return jsonify(evidence.to_dict())

@main_bp.route('/api/patrol-evidence/<evidence_id>', methods=['DELETE'])
@login_required
def delete_evidence(evidence_id):
    evidence = PatrolEvidence.query.filter_by(id=evidence_id, company_id=current_company_id()).first_or_404()
    if current_membership().role_key != 'company_admin' and evidence.user_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403
    db.session.delete(evidence)
    db.session.commit()
    return jsonify({'ok': True})

@main_bp.route('/api/patrol-evidence/pdf', methods=['GET'])
@login_required
def generate_pdf():
    from app.pdf_generator import generate_evidence_pdf
    
    query = PatrolEvidence.query.filter(PatrolEvidence.company_id == current_company_id())
    if current_membership().role_key != 'company_admin':
        query = query.filter(PatrolEvidence.user_id == current_user.id)
    
    evidences = query.order_by(PatrolEvidence.timestamp.asc()).all()
    
    if not evidences:
        return jsonify({'error': 'No hay evidencias para generar el PDF'}), 400
    
    pdf_buffer = generate_evidence_pdf([e.to_dict() for e in evidences], title="REPORTE SEMANAL")
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'evidencia_patrullas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    )

# ============ PWA: SERVICE WORKER Y MANIFEST ============
@main_bp.route('/sw.js')
def service_worker():
    from flask import send_from_directory
    return send_from_directory(current_app.static_folder, 'sw.js', mimetype='application/javascript')

@main_bp.route('/manifest.webmanifest')
def manifest_file():
    file_path = os.path.join(current_app.root_path, '..', 'manifest.webmanifest.json')
    file_path = os.path.normpath(file_path)
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='application/manifest+json', headers={'Cache-Control': 'no-cache'})
    return 'Not found', 404
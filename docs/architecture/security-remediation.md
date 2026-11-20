# Correcciones de seguridad — preparación

## Aplicadas en esta rama
- Cookies HttpOnly y SameSite=Lax; Secure cuando APP_ENV=production.
- La aplicación falla al iniciar en producción si falta SECRET_KEY.
- Protección CSRF global para formularios y solicitudes mutables.
- Cierre de sesión preparado para migrar a POST en el cliente.
- Service worker limitado a recursos estáticos; no almacena HTML, páginas autenticadas ni API.
- Creación de tablas y aprovisionamiento del tenant heredado requieren variables explícitas.

## Variables
- APP_ENV=production
- SECRET_KEY: valor aleatorio largo, privado y persistente.
- AUTO_CREATE_TABLES=true: solo en entornos temporales/locales; no sustituye migraciones.
- AUTO_PROVISION_LEGACY_COMPANY=true: solo tras backup y validación del entorno de migración.

## Pendiente antes de producción
- Migraciones Alembic/Flask-Migrate; retirar db.create_all.
- Revisar todas las rutas para aislamiento tenant; no habilitar multiempresa aún.
- Implementar RLS en PostgreSQL y pruebas de aislamiento.
- Verificar Cloudinary/PDF en staging con credenciales reales.
- Pruebas automatizadas de CSRF, XSS, autenticación y permisos.
- Esta rama no está desplegada ni modifica la base de datos existente.

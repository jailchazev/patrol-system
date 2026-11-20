# Fase 1 — Base funcional multiempresa

## Incluido
- Entidades nuevas: empresas, identidades globales, membresías, solicitudes de registro, roles, permisos, relaciones rol-permiso y auditoría.
- La cuenta heredada continúa funcionando durante la transición.
- Al iniciar, se crea un tenant de transición `legacy-migration` y se vinculan los usuarios existentes mediante membresías. No se modifican ni eliminan usuarios o evidencias.
- El secreto de sesión ya no tiene una contraseña literal conocida: se toma de `SECRET_KEY` o se genera uno temporal para desarrollo.

## Límites de esta fase
- Las tablas heredadas `users` y `patrol_evidences` todavía no tienen `company_id`.
- Las rutas heredadas aún no están aisladas por empresa. Por tanto, esta rama NO debe desplegarse como SaaS multiempresa ni abrirse a nuevas compañías todavía.
- `db.create_all()` crea las tablas nuevas, pero no sustituye un sistema de migraciones versionadas.
- La política RLS de PostgreSQL aún no está habilitada.

## Próxima fase obligatoria
1. Incorporar Flask-Migrate/Alembic y migraciones versionadas.
2. Añadir `company_id` a todas las tablas operativas, rellenarlo a partir de las membresías y validar que no quedan filas huérfanas.
3. Actualizar cada ruta y consulta para aplicar el tenant del servidor; nunca aceptar `company_id` del cliente.
4. Añadir pruebas de aislamiento entre dos empresas.
5. Habilitar RLS con un rol de base de datos que no tenga BYPASSRLS.
6. Crear el flujo de registro y aprobación de empresas y el alta segura del primer administrador.

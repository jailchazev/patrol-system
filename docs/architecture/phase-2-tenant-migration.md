# Fase 2 — migraciones y aislamiento inicial

## Qué introduce esta fase
- Flask-Migrate/Alembic como mecanismo versionado.
- Revisión `20261120_0001` para crear tablas de plataforma y membresías.
- Asociación de todos los usuarios históricos con la empresa `legacy-migration`.
- Nueva columna `company_id NOT NULL` en `patrol_evidences`, rellenada con la empresa de migración.
- Filtros de tenant en listado, edición, eliminación y PDF de evidencias.
- Filtros de membresía en la administración de usuarios.
- Contexto PostgreSQL transaccional mediante `set_config('app.current_company_id', ..., true)`.
- RLS con `USING` y `WITH CHECK` en `patrol_evidences` y `company_roles`.
- Pruebas de acceso cruzado entre dos empresas y workflow de CI.

## Secuencia segura de migración
1. Confirmar que el entorno objetivo tiene las tablas heredadas `users` y `patrol_evidences`.
2. Hacer backup de PostgreSQL y restaurarlo en una base de staging independiente.
3. Verificar que el rol de la aplicación no sea superuser, propietario de tablas ni tenga BYPASSRLS.
4. Ejecutar `flask --app wsgi:app db upgrade` solamente en staging.
5. Comprobar recuentos de usuarios y evidencias, membresías, fotos y generación de PDF.
6. Ejecutar pruebas de aislamiento con dos empresas.
7. Probar rollback en una copia desechable; comparar datos y conteos antes/después.

## Restricciones conocidas
- Esta revisión es una migración de transición para bases que ya tienen el esquema heredado. No es una instalación inicial limpia.
- La identidad heredada puede tener una sola membresía activa. La selección de múltiples empresas por usuario aún no está habilitada.
- RLS se activa solo en PostgreSQL. SQLite se usa para pruebas unitarias.
- Las tablas `users` y otros datos heredados aún no se han convertido por completo al nuevo modelo de identidad.
- No habilitar nuevas altas públicas ni considerar completada la separación multiempresa hasta ampliar el tenant scope a cada módulo operativo y probar el rol real de base de datos.

## Estado de despliegue
No ejecutado contra staging ni producción. No se ha conectado ni modificado ninguna base de datos remota.

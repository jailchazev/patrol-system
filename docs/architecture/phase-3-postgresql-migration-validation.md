# Fase 3 — validación de migración PostgreSQL

## Alcance

Se añade una prueba de integración que crea un esquema heredado en una base PostgreSQL desechable, ejecuta la revisión Alembic, comprueba el backfill de la empresa inicial y prueba las políticas RLS con un rol de aplicación restringido. Después ejecuta el downgrade y verifica que usuarios, evidencias, fotografías y ubicación siguen presentes.

## Automatización

El workflow `.github/workflows/postgres-rls.yml` contiene dos trabajos independientes:

- `postgres-rls`: prueba RLS aislada con PostgreSQL 16 y un rol sin privilegios de bypass.
- `postgres-migration`: crea la base dedicada `patrol_migration_test`, prepara el rol `patrol_rls_app`, ejecuta upgrade, validación de acceso multiempresa y downgrade.

La prueba de migración se niega a ejecutarse si la base no se llama exactamente `patrol_migration_test`. Limpia el esquema público de esa base, por lo que no debe apuntarse a staging ni producción.

## Comprobaciones de migración

1. Los usuarios heredados conservan su ID, nombre, contraseña y rol.
2. Las evidencias históricas conservan ID, descripción, fotos, ubicación y relación con el usuario.
3. Cada evidencia heredada recibe el `company_id` de `legacy-migration`.
4. Se crea la membresía activa con el rol esperado.
5. Las políticas RLS de la migración aparecen en PostgreSQL.
6. Un rol de aplicación no superusuario ni `BYPASSRLS` solo puede leer evidencias de su empresa.
7. El rol puede consultar su propia membresía antes de seleccionar empresa.
8. UPDATE/DELETE sobre otra empresa no afectan filas; INSERT con `company_id` ajeno es rechazado.
9. Tras `downgrade base`, se elimina la columna y las tablas multiempresa, pero no se pierden los datos heredados.

## Qué no significa este resultado

La CI valida el esquema de transición reproducido en pruebas, no una copia de la base real del cliente. Antes de staging se debe restaurar un backup reciente de producción en una instancia aislada, comparar conteos y validar todos los archivos referenciados en Cloudinary. No ejecutar la migración real hasta que ese ensayo se complete y se apruebe el plan de corte y reversión.

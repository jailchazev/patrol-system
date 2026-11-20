# Pruebas PostgreSQL RLS

Este flujo valida RLS en PostgreSQL real usando un rol de aplicación separado del propietario de las tablas.

## Ejecución automática

El workflow `.github/workflows/postgres-rls.yml` levanta PostgreSQL 16, crea el rol restringido `patrol_rls_app` y ejecuta `tests/test_postgres_rls.py`.

## Ejecución local

Usa exclusivamente una base desechable, nunca producción:

```bash
export TEST_POSTGRES_ADMIN_URL='postgresql://postgres:postgres@localhost:5432/patrol_test'
export TEST_POSTGRES_APP_URL='postgresql://patrol_rls_app:rls-test-password@localhost:5432/patrol_test'
python -m pytest -q tests/test_postgres_rls.py
```

El rol `patrol_rls_app` debe existir con `NOSUPERUSER`, `NOBYPASSRLS` y no ser propietario de las tablas de prueba. La prueba crea un esquema aleatorio, otorga permisos mínimos y lo elimina al terminar.

## Cobertura

- Sin contexto de empresa, no se leen filas.
- La empresa A solo ve sus propias evidencias.
- Las políticas `USING` bloquean UPDATE y DELETE sobre filas de B.
- `WITH CHECK` rechaza insertar una fila asignada a B.
- El contexto establecido con `set_config(..., true)` desaparece al terminar o revertir la transacción.

## Límite de esta prueba

Esta es una prueba de integración aislada de las políticas RLS. No ejecuta la migración completa sobre el esquema heredado ni demuestra que la configuración de roles de un entorno desplegado sea correcta. Antes de migrar staging, se debe comprobar que el usuario real de la aplicación no sea superusuario, no tenga `BYPASSRLS` y no sea propietario de las tablas protegidas.

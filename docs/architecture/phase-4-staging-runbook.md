# Fase 4 — runbook de staging y migración controlada

## Regla de seguridad

No ejecutar la migración sobre producción desde una sesión de desarrollo. El primer destino debe ser una base PostgreSQL de staging restaurada desde un backup reciente. No compartir contraseñas ni URLs completas de conexión en chats, issues o commits.

## Preparación

1. Crear una base PostgreSQL separada para staging.
2. Restaurar una copia reciente de la base productiva.
3. Confirmar que las tablas heredadas `users` y `patrol_evidences` existen.
4. Tomar y registrar conteos de usuarios y evidencias antes de la migración.
5. Confirmar que las fotos siguen referenciadas por URLs válidas de Cloudinary.
6. Preparar un usuario de aplicación separado del propietario de tablas. Debe ser `NOSUPERUSER` y `NOBYPASSRLS`.
7. Configurar el entorno de staging para usar el controlador PostgreSQL instalado (`psycopg2`); la aplicación normaliza `postgres://` y `postgresql://` a `postgresql+psycopg2://`.

## Preflight de rol y RLS

Conectado como el usuario de base de datos que utilizará Flask, ejecutar:

```bash
psql "$STAGING_DATABASE_URL" -v ON_ERROR_STOP=1 -f docs/architecture/check_postgres_rls_role.sql
```

Antes de migrar, confirmar que el rol no sea superusuario ni tenga `BYPASSRLS`. Después de migrar, comprobar que RLS está habilitado y forzado en las tablas protegidas, que el rol de aplicación no es propietario de ellas y que el recuento de evidencias sin empresa sea cero.

## Ejecución en staging

```bash
flask --app wsgi:app db upgrade
```

Ejecutar el comando con las variables de entorno de staging y después registrar:

- conteo de usuarios heredados;
- conteo de evidencias;
- conteo de membresías;
- empresa inicial `legacy-migration`;
- evidencias sin `company_id` (debe ser cero);
- cantidad de URLs de fotografías que se pueden abrir;
- prueba de descarga de PDF.

## Pruebas funcionales manuales

1. Iniciar sesión con un administrador histórico.
2. Crear un usuario de prueba y verificar que queda vinculado a la empresa inicial.
3. Crear una evidencia con fotografía y ubicación.
4. Verificar que aparece en el listado y en el PDF.
5. Probar una segunda empresa de staging y confirmar que no ve usuarios ni evidencias de la primera.
6. Repetir con una cuenta de supervisor/agente y comprobar sus permisos.
7. Verificar que los registros y archivos históricos siguen disponibles.

## Reversión

- En una base desechable sin nuevas operaciones, la prueba CI ejecuta `flask db downgrade base` y verifica que los datos heredados sobreviven.
- En staging con datos de prueba, detener escrituras, guardar los logs y restaurar el backup previo si se requiere volver al estado anterior.
- No asumir que un downgrade es suficiente después de que se creen empresas y operaciones nuevas: la reversión elimina las tablas multiempresa y la asociación `company_id`.

## Criterio para aprobar un despliegue posterior

No proponer el corte a producción hasta que staging pase todos los puntos, se revise el resultado con los responsables y exista un backup restaurable. La migración de producción requerirá una autorización explícita separada.

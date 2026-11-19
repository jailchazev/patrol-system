# Plan de migración desde la aplicación actual

## Regla de seguridad

No reemplazar la aplicación actual ni ejecutar migraciones destructivas en la rama principal. No borrar usuarios, evidencias, fotografías ni archivos. La migración debe ser reversible y ensayada con copia de datos.

## Fase 0 — inventario y respaldo
- Inventariar rutas, modelos, configuración, integraciones y variables de entorno.
- Confirmar dónde reside la base de datos real (SQLite/PostgreSQL) y quién la administra.
- Crear backup y probar restauración.
- Inventariar objetos de Cloudinary y referencias guardadas.
- Eliminar credenciales por defecto antes de cualquier despliegue público.

## Fase 1 — fundación
- Incorporar configuración por entorno y extensiones.
- Introducir migraciones Alembic/Flask-Migrate.
- Crear entidades de plataforma, empresas y membresías.
- Añadir tenant context y servicios de autorización.
- Mantener rutas heredadas aisladas hasta que tengan tenant resuelto.

## Fase 2 — migración de datos
- Crear una empresa inicial de migración.
- Asociar usuarios y evidencias heredados a esa empresa.
- Preservar hashes de contraseña si son compatibles; forzar restablecimiento si no lo son.
- Verificar recuentos, claves, fotografías, PDFs y reportes.
- Ensayar rollback completo.

## Fase 3 — módulos y rutas
- Migrar primero autenticación y usuarios.
- Migrar clientes, contratos, sedes y puestos.
- Migrar turnos, patrullas, incidencias y evidencias.
- Añadir portal cliente y reportes.
- Eliminar rutas heredadas solo después de pruebas de paridad.

## Fase 4 — lanzamiento
- Pruebas de aislamiento y seguridad.
- Prueba de carga y restauración.
- Despliegue en staging, aceptación y luego producción.
- Monitorización, alertas y procedimiento de incidentes.

## Criterios de aceptación
- Ninguna fuga entre tenants en pruebas automatizadas.
- Los datos heredados coinciden antes/después.
- Restauración desde backup demostrada.
- Secretos y contraseñas por defecto eliminados.
- PDFs, imágenes y exportaciones respetan permisos.
- No se pierde funcionalidad heredada sin sustitución aprobada.

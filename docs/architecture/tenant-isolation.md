# Seguridad y aislamiento de tenants

## Resolución del tenant

El tenant activo se obtiene de la membresía autenticada y validada en el servidor. No confiar en `company_id` de formularios, query strings, cabeceras arbitrarias ni almacenamiento local del navegador.

Si un usuario pertenece a más de una empresa, la selección de contexto debe validar una membresía activa y guardar el tenant elegido en una sesión firmada/servidor; cada petición vuelve a validar autorización.

## Capas obligatorias

1. Autorización de ruta y servicio.
2. Filtro tenant-scoped en repositorios/consultas.
3. Claves foráneas e índices compuestos para integridad.
4. PostgreSQL Row-Level Security (RLS) como defensa adicional.
5. Pruebas automatizadas de acceso cruzado.
6. Autorización independiente para descargas, PDF, imágenes y exportaciones.

## PostgreSQL RLS

Al implementarse:
- Activar RLS en cada tabla tenant-scoped.
- Usar políticas tanto `USING` como `WITH CHECK`.
- Establecer el tenant con contexto transaccional (`SET LOCAL` o `set_config(..., true)`) para evitar contaminación entre conexiones del pool.
- La aplicación no debe conectarse como propietario de tablas ni con un rol que omita RLS.
- Probar que la ausencia de contexto no devuelve ni permite insertar datos.
- Las migraciones usan un rol separado y controlado.

## Superadministrador

Los permisos globales deben residir en una identidad/rol de plataforma separado. Las acciones de soporte que inspeccionen datos de una empresa requieren motivo, alcance, duración y registro de auditoría. No se debe dar acceso universal a administradores de empresa.

## Archivos y evidencias

- Almacenamiento privado, no URLs públicas permanentes.
- Claves/rutas de objeto con tenant y recurso, sin confiar en el nombre enviado por el usuario.
- URLs firmadas de corta duración o endpoint autorizado.
- Validar tipo real, tamaño, extensión y contenido.
- Registrar quién subió, consultó o eliminó evidencia.
- Evitar almacenar secretos o datos personales innecesarios en logs.

## Pruebas mínimas de aislamiento

- Usuario A no puede listar, consultar, editar ni borrar recursos de B.
- Cambiar un UUID en una URL no permite acceso cruzado.
- Exportaciones y PDFs respetan tenant.
- Una tarea asíncrona no procesa datos de otro tenant.
- El pool de conexiones no conserva el tenant anterior.
- Un administrador empresarial no puede invocar rutas de plataforma.
- Una empresa suspendida no puede iniciar nuevas operaciones.

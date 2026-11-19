# Modelo de datos multiempresa (propuesta)

Este modelo es una especificación inicial; no crea tablas ni migra datos todavía.

## Plataforma

### `platform_users`
Identidades con privilegios globales: `id`, `email`, `password_hash`, `is_active`, `created_at`, `last_login_at`.

### `companies`
Tenant: `id`, `legal_name`, `display_name`, `slug`, `tax_id` (opcional y protegido), `status`, `timezone`, `country_code`, `created_at`, `updated_at`.

### `company_applications`
Solicitudes: `id`, datos de empresa y contacto, `status`, `reviewed_by`, `reviewed_at`, `rejection_reason`, timestamps. No debe convertirse automáticamente en una empresa activa.

### `subscription_plans` y `subscriptions`
Planes, límites y periodo contratado. Los límites deben validarse en backend; no son controles meramente visuales.

### `platform_audit_logs`
Actor global, acción, entidad, resultado, fecha, IP/metadatos mínimos y correlación de solicitud. No almacenar contraseñas, tokens ni secretos.

## Identidad empresarial

### `users`
Identidad de acceso empresarial: `id`, `email` (o identificador de acceso), `password_hash`, `name`, `is_active`, timestamps.

### `company_memberships`
Relación usuario-empresa: `id`, `company_id`, `user_id`, `status`, `joined_at`, `created_by`. Restricción única propuesta: (`company_id`, `user_id`).

### `roles`, `permissions`, `role_permissions`, `membership_roles`
RBAC por empresa. Los roles personalizados deben pertenecer a su tenant salvo roles de sistema explícitos.

## Operaciones tenant-scoped

Las siguientes entidades deben incluir `company_id NOT NULL` y claves/índices compuestos donde corresponda:

- `clients`, `contracts`
- `sites`, `posts`
- `shifts`, `assignments`, `attendance`
- `patrols`, `patrol_routes`, `checkpoints`
- `incidents`, `incident_actions`
- `patrol_evidence`, `evidence_files`
- `notifications`, `company_settings`
- `audit_logs`

## Integridad entre tenants

- Una asignación no puede relacionar un trabajador de Empresa A con un puesto de Empresa B.
- Una evidencia debe pertenecer al mismo tenant que la patrulla/incidencia asociada.
- Usar claves foráneas compuestas cuando sea apropiado: (`company_id`, `resource_id`).
- Evitar endpoints que acepten IDs sin volver a comprobar tenant y permiso.
- Toda consulta tenant-scoped debe filtrar por contexto validado, además de RLS en PostgreSQL.

## Datos heredados

El modelo actual usa usuarios y evidencias sin tenant. Antes de migrar se debe:
1. Hacer backup verificable de la base de datos.
2. Crear un tenant de migración.
3. Mapear cada usuario y evidencia heredados a ese tenant.
4. Validar recuentos, relaciones, fotos y fechas.
5. Ejecutar migración en staging y probar rollback.
6. Cambiar producción solo tras aprobación y prueba de restauración.

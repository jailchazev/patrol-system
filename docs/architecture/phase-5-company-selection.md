# Fase 5 — selección de empresa por membresía

## Implementado

- Un usuario con una sola membresía activa entra directamente a esa empresa.
- Un usuario con varias membresías activas es enviado a la pantalla de selección antes de entrar a los módulos.
- La pantalla muestra únicamente empresas con membresía activa.
- La selección recibida del navegador se valida contra las membresías consultadas en el servidor; el navegador no puede inventar un `company_id` válido.
- La empresa seleccionada se guarda en la sesión firmada y se vuelve a validar en cada petición.
- El contexto PostgreSQL se establece de nuevo por transacción mediante `set_config(..., true)`.
- El usuario puede cambiar de empresa desde la navegación principal.
- El cierre de sesión limpia el contexto de empresa.

## Rutas

- `GET /companies/select`: pantalla de selección.
- `GET /api/companies`: empresas disponibles para el usuario autenticado.
- `POST /api/companies/select`: valida y establece la empresa activa.

## Pruebas

`tests/test_company_selection.py` comprueba el redireccionamiento inicial, la lista de empresas, el rechazo de una empresa sin membresía, el cambio entre empresas y que las consultas de evidencias cambian de tenant.

## Límite actual

La selección está conectada al modelo de usuario heredado (`users`) y a `company_memberships`. La autenticación global de `platform_users`, el superadministrador, la aprobación de solicitudes y la administración completa de empresas todavía requieren sus propios flujos y pruebas. No se debe considerar terminada la plataforma SaaS hasta completar esas etapas.

## Autorización y revocación por empresa

- Las decisiones de acceso usan `company_memberships.role_key`, no el campo global heredado `users.role`.
- La interfaz muestra el rol de la membresía activa.
- Quitar un trabajador de una empresa revoca solo esa membresía; no elimina la identidad global ni sus evidencias históricas ni las membresías que tenga en otras empresas.
- Las operaciones de administración se limitan a la membresía de la empresa seleccionada.

## Limitación de identidad pendiente

La tabla heredada `users` todavía almacena código, nombre y hash de contraseña globales. El flujo de restablecimiento de contraseña y la edición de perfil compartido deben migrarse a un servicio de identidad global antes de permitir que un mismo usuario comparta cuenta entre empresas en producción. No habilitar todavía usuarios multiempresa reales en producción sin completar esa separación.

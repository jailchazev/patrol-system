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

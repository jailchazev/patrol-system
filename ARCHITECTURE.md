# Patrol System — arquitectura objetivo

Patrol System evoluciona hacia una plataforma SaaS multiempresa (multi-tenant). Este documento describe la arquitectura objetivo; la estructura añadida en esta rama es un andamiaje documental y de paquetes, no una migración funcional todavía.

## Principios

1. **Aislamiento por empresa:** cada registro empresarial pertenece a un `company_id`; el servidor determina el tenant desde la identidad autenticada.
2. **Denegación por defecto:** ninguna consulta, archivo, exportación o acción opera fuera del alcance autorizado.
3. **Separación de plataforma y empresa:** las cuentas de plataforma y las identidades empresariales tienen responsabilidades y permisos distintos.
4. **Migraciones verificables:** conservar la aplicación heredada y sus datos; migrar mediante copias, validaciones y reversión.
5. **Auditoría:** registrar operaciones administrativas y accesos privilegiados.
6. **Configuración segura:** secretos y credenciales solo por variables de entorno/gestor de secretos.
7. **Evolución incremental:** Flask, SQLAlchemy y PostgreSQL siguen siendo la base inicial.

## Capas

- `app/platform/`: administración global, empresas, solicitudes y planes.
- `app/tenancy/`: resolución del tenant, contexto y políticas de aislamiento.
- `app/identity/`: autenticación, membresías, roles y permisos.
- `app/operations/`: clientes, sedes, puestos, turnos, patrullas, incidencias y evidencias.
- `app/audit/`: auditoría y trazabilidad.
- `app/billing/`: planes, suscripciones y límites comerciales.
- `app/api/`: contratos HTTP y serialización.
- `docs/architecture/`: decisiones, modelo de datos y plan de migración.

## Límites de confianza

- El navegador nunca decide el `company_id` efectivo.
- Las rutas de plataforma requieren privilegios globales explícitos.
- Los usuarios empresariales necesitan una membresía activa para entrar en una empresa.
- Las tareas en segundo plano deben recibir tenant explícito y validado.
- Los archivos de evidencia deben almacenarse en contenedores privados y autorizarse antes de servirlos.
- El soporte global no debe implicar acceso silencioso al contenido empresarial; cualquier acceso excepcional debe quedar auditado.

## Estado de esta rama

Esta rama prepara carpetas y documentación. No cambia rutas existentes, modelos actuales, tablas, autenticación ni despliegue. La implementación funcional vendrá en fases revisables y con migraciones explícitas.

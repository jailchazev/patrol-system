# Visión general del sistema

## Tipos de usuario

### Plataforma
- Superadministrador: administra el SaaS, empresas, solicitudes, planes y configuración global.
- Personal de soporte (futuro): permisos limitados y acceso excepcional auditado.

### Empresa
- Administrador de empresa.
- Gerente de operaciones.
- Supervisor.
- Coordinador.
- Agente de vigilancia.
- Cliente con acceso limitado a servicios e informes autorizados.

Los roles empresariales se asignan mediante membresías; un usuario puede tener más de una membresía si el producto lo permite en una fase posterior.

## Ciclo de vida de una empresa

Estados propuestos: `pending`, `trial`, `active`, `suspended`, `rejected`, `cancelled`.

- Solicitud: se crea un registro pendiente sin habilitar acceso operativo.
- Aprobación: el superadministrador valida la solicitud y habilita la creación del tenant y de su administrador inicial.
- Registro autónomo: se verifica el correo y se aplica la política configurada (aprobación previa o prueba limitada).
- Suspensión: bloquea nuevas sesiones y operaciones, pero conserva datos para auditoría y reactivación.
- Cancelación: inicia política de retención/exportación y no borra datos automáticamente.

## Dominios funcionales

1. Plataforma: empresas, solicitudes, planes, suscripciones y auditoría global.
2. Identidad: usuarios, membresías, roles, permisos y sesiones.
3. Administración empresarial: clientes, contratos, sedes, puestos y configuración.
4. Operaciones: turnos, asignaciones, patrullas, rutas, puntos de control y asistencia.
5. Incidencias: novedades, severidad, acciones y seguimiento.
6. Evidencias: fotografías, metadatos, ubicación, fecha/hora y cadena de trazabilidad.
7. Informes: consultas autorizadas, exportaciones PDF y métricas.
8. Portal cliente: únicamente servicios e información compartidos explícitamente.

## Convenciones

- IDs UUID para entidades nuevas.
- Fechas almacenadas en UTC y presentadas según zona horaria de la empresa.
- Estados mediante valores enumerados y transiciones validadas.
- Las tablas tenant-scoped tendrán `company_id` obligatorio e indexado.
- Las relaciones entre entidades tenant-scoped deben comprobar que ambos registros pertenecen al mismo tenant.

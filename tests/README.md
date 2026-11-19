# Pruebas

Las pruebas nuevas deben cubrir como mínimo:

- aislamiento entre dos empresas;
- acceso denegado cuando no existe contexto de tenant;
- autorización de superadministrador frente a administrador empresarial;
- integridad de relaciones entre registros del mismo tenant;
- permisos de descargas, PDF y evidencias;
- transición de estados de empresa;
- migración y rollback de datos heredados.

No añadir pruebas que dependan de datos reales de producción o credenciales.

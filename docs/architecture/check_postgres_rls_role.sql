-- Ejecutar conectado con el mismo usuario que utiliza Flask.
-- Este archivo es de solo lectura; no cambia roles, tablas ni datos.

SELECT
    current_user AS application_role,
    r.rolsuper AS is_superuser,
    r.rolbypassrls AS bypasses_rls
FROM pg_roles AS r
WHERE r.rolname = current_user;

SELECT
    n.nspname AS schema_name,
    c.relname AS protected_table,
    pg_get_userbyid(c.relowner) AS table_owner,
    pg_get_userbyid(c.relowner) = current_user AS app_role_owns_table,
    c.relrowsecurity AS rls_enabled,
    c.relforcerowsecurity AS rls_forced
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN (
      'patrol_evidences',
      'company_memberships',
      'company_roles',
      'audit_logs'
  )
ORDER BY c.relname;

-- Debe devolver cero evidencias sin empresa después de la migración.
SELECT COUNT(*) AS evidences_without_company
FROM patrol_evidences
WHERE company_id IS NULL;

-- Conteos para registrar antes y después de la migración.
SELECT
    (SELECT COUNT(*) FROM users) AS legacy_users,
    (SELECT COUNT(*) FROM patrol_evidences) AS legacy_evidences,
    (SELECT COUNT(*) FROM company_memberships) AS memberships,
    (SELECT COUNT(*) FROM companies) AS companies;

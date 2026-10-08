"""Trilha de auditoria é append-only no próprio banco (docs/domain/audit.md).

Nem código novo, nem script manual, nem o Django admin alteram ou apagam um registro. A única
exceção é a limpeza de retenção, que liga `audit.allow_purge` só na própria transação
(`SET LOCAL` via `set_config(..., true)`) — UPDATE continua proibido sempre.

`TRUNCATE` (limpeza de testes transacionais) não dispara triggers de linha.
"""

from django.db import migrations

FORWARD = """
CREATE FUNCTION audit_log_reject_change() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' AND current_setting('audit.allow_purge', true) = 'on' THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'audit_log is append-only (% rejected)', TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_append_only
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_reject_change();
"""

REVERSE = """
DROP TRIGGER IF EXISTS audit_log_append_only ON audit_log;
DROP FUNCTION IF EXISTS audit_log_reject_change();
"""


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]

    operations = [migrations.RunSQL(FORWARD, REVERSE)]

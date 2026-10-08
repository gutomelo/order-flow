"""O histórico de status é append-only no próprio banco (O9, docs/domain/orders.md).

Mesmo padrão de `inventory_stock_movement`: nem código novo, nem script manual, nem o admin
conseguem reescrever a trilha do pedido. `TRUNCATE` (limpeza de testes) não dispara o trigger.
"""

from django.db import migrations

FORWARD = """
CREATE FUNCTION orders_status_history_reject_change() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'orders_status_history is append-only (% rejected)', TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER orders_status_history_append_only
    BEFORE UPDATE OR DELETE ON orders_status_history
    FOR EACH ROW EXECUTE FUNCTION orders_status_history_reject_change();
"""

REVERSE = """
DROP TRIGGER IF EXISTS orders_status_history_append_only ON orders_status_history;
DROP FUNCTION IF EXISTS orders_status_history_reject_change();
"""


class Migration(migrations.Migration):
    dependencies = [("orders", "0001_initial")]

    operations = [migrations.RunSQL(FORWARD, REVERSE)]

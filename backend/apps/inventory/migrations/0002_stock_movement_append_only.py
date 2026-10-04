"""Movimentações de estoque são append-only no próprio banco (docs/domain/inventory.md).

O histórico é a trilha de auditoria do saldo: nem código novo, nem script manual, nem o Django
admin conseguem alterá-lo ou apagá-lo. Correções são feitas com novos movimentos (ADJUSTMENT).

`TRUNCATE` (usado pela limpeza de testes transacionais) não dispara triggers de linha.
"""

from django.db import migrations

FORWARD = """
CREATE FUNCTION inventory_stock_movement_reject_change() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'inventory_stock_movement is append-only (% rejected)', TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER inventory_stock_movement_append_only
    BEFORE UPDATE OR DELETE ON inventory_stock_movement
    FOR EACH ROW EXECUTE FUNCTION inventory_stock_movement_reject_change();
"""

REVERSE = """
DROP TRIGGER IF EXISTS inventory_stock_movement_append_only ON inventory_stock_movement;
DROP FUNCTION IF EXISTS inventory_stock_movement_reject_change();
"""


class Migration(migrations.Migration):
    dependencies = [("inventory", "0001_initial")]

    operations = [migrations.RunSQL(FORWARD, REVERSE)]

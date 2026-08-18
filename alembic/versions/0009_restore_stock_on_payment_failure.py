"""Restore physical product stock when an order payment fails or is cancelled.

Revision ID: 0009_restore_stock
Revises: 0008_digital_affiliate
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0009_restore_stock"
down_revision: Union[str, Sequence[str], None] = "0008_digital_affiliate"
branch_labels = None
depends_on = None


_TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION restore_order_stock_on_payment_failure()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status IN ('initiated', 'pending')
       AND NEW.status IN ('failed', 'cancelled') THEN
        UPDATE products AS p
        SET stock_quantity = p.stock_quantity + stock_totals.quantity
        FROM (
            SELECT product_id, SUM(quantity)::integer AS quantity
            FROM commerce_order_items
            WHERE order_id = NEW.order_id
            GROUP BY product_id
        ) AS stock_totals
        WHERE p.id = stock_totals.product_id
          AND p.product_type <> 'digital';
    END IF;
    RETURN NEW;
END;
$$;
"""


def upgrade() -> None:
    op.execute(_TRIGGER_FUNCTION)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_restore_stock_on_payment_failure ON payments;
    """)
    op.execute("""
        CREATE TRIGGER trg_restore_stock_on_payment_failure
        AFTER UPDATE OF status ON payments
        FOR EACH ROW
        WHEN (OLD.status IN ('initiated', 'pending')
              AND NEW.status IN ('failed', 'cancelled'))
        EXECUTE FUNCTION restore_order_stock_on_payment_failure();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS trg_restore_stock_on_payment_failure ON payments;
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS restore_order_stock_on_payment_failure();
    """)

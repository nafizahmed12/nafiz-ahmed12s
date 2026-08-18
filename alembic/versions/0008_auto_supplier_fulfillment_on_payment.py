"""Automatically create supplier fulfillment orders when payment becomes paid.

Revision ID: 0008_auto_supplier_fulfillment_on_payment
Revises: 0007_supplier_fulfillment
"""
from typing import Sequence, Union
from alembic import op

revision: str = "0008_auto_supplier_fulfillment_on_payment"
down_revision: Union[str, Sequence[str], None] = "0007_supplier_fulfillment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION create_supplier_fulfillment_on_payment()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE
        item RECORD;
        supplier_order_id INTEGER;
        line_cost NUMERIC(12,2);
        has_supplier_order BOOLEAN := FALSE;
    BEGIN
        IF NEW.status <> 'paid' OR OLD.status = 'paid' THEN
            RETURN NEW;
        END IF;

        FOR item IN
            SELECT oi.id AS order_item_id,
                   oi.quantity,
                   oi.supplier_product_id,
                   sp.supplier_id,
                   sp.cost_price,
                   sp.supplier_stock,
                   sp.is_active
            FROM commerce_order_items oi
            JOIN supplier_products sp ON sp.id = oi.supplier_product_id
            WHERE oi.order_id = NEW.order_id
              AND oi.supplier_product_id IS NOT NULL
            ORDER BY oi.id
        LOOP
            IF NOT item.is_active OR item.supplier_id IS NULL THEN
                CONTINUE;
            END IF;

            -- Reserve supplier stock atomically. If it is no longer available,
            -- leave the supplier item uncreated for admin intervention.
            UPDATE supplier_products
               SET supplier_stock = supplier_stock - item.quantity,
                   updated_at = NOW()
             WHERE id = item.supplier_product_id
               AND is_active = TRUE
               AND supplier_stock >= item.quantity;

            IF NOT FOUND THEN
                CONTINUE;
            END IF;

            SELECT id INTO supplier_order_id
              FROM supplier_orders
             WHERE order_id = NEW.order_id
               AND supplier_id = item.supplier_id
             ORDER BY id
             LIMIT 1;

            IF supplier_order_id IS NULL THEN
                INSERT INTO supplier_orders
                    (order_id, supplier_id, status, external_order_ref,
                     tracking_number, shipping_cost, cost_total, notes,
                     created_at, updated_at)
                VALUES
                    (NEW.order_id, item.supplier_id, 'pending', NULL,
                     NULL, 0, 0,
                     'Auto-created after successful payment.', NOW(), NOW())
                RETURNING id INTO supplier_order_id;
            END IF;

            -- Idempotency guard for repeated payment callbacks.
            IF NOT EXISTS (
                SELECT 1
                  FROM supplier_order_items soi
                 WHERE soi.supplier_order_id = supplier_order_id
                   AND soi.order_item_id = item.order_item_id
            ) THEN
                line_cost := COALESCE(item.cost_price, 0) * item.quantity;

                INSERT INTO supplier_order_items
                    (supplier_order_id, order_item_id, supplier_product_id,
                     quantity, cost_price, line_cost)
                VALUES
                    (supplier_order_id, item.order_item_id,
                     item.supplier_product_id, item.quantity,
                     COALESCE(item.cost_price, 0), line_cost);

                UPDATE supplier_orders
                   SET cost_total = cost_total + line_cost,
                       updated_at = NOW()
                 WHERE id = supplier_order_id;
            END IF;

            has_supplier_order := TRUE;
        END LOOP;

        IF has_supplier_order THEN
            UPDATE commerce_orders
               SET fulfillment_status = 'supplier_pending',
                   updated_at = NOW()
             WHERE id = NEW.order_id
               AND fulfillment_status = 'unfulfilled';
        END IF;

        RETURN NEW;
    END;
    $$;

    DROP TRIGGER IF EXISTS trg_payment_paid_supplier_fulfillment ON payments;

    CREATE TRIGGER trg_payment_paid_supplier_fulfillment
    AFTER UPDATE OF status ON payments
    FOR EACH ROW
    EXECUTE FUNCTION create_supplier_fulfillment_on_payment();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_payment_paid_supplier_fulfillment ON payments;")
    op.execute("DROP FUNCTION IF EXISTS create_supplier_fulfillment_on_payment();")

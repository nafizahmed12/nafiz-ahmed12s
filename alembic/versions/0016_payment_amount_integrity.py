"""Protect paid payments from amount or currency mismatches.

Revision ID: 0016_payment_amount_integrity
Revises: 0015_admin_credentials
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0016_payment_amount_integrity"
down_revision: Union[str, Sequence[str], None] = "0015_admin_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_paid_payment_integrity()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            order_amount NUMERIC(12, 2);
            order_currency VARCHAR(3);
        BEGIN
            IF NEW.status <> 'paid' THEN
                RETURN NEW;
            END IF;

            SELECT total_amount, currency
              INTO order_amount, order_currency
              FROM commerce_orders
             WHERE id = NEW.order_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION
                    'Cannot mark payment paid: order % does not exist', NEW.order_id
                    USING ERRCODE = 'foreign_key_violation';
            END IF;

            IF NEW.amount <> order_amount THEN
                RAISE EXCEPTION
                    'Payment amount mismatch for order %: payment=% order=%',
                    NEW.order_id, NEW.amount, order_amount
                    USING ERRCODE = 'check_violation';
            END IF;

            IF NEW.currency <> order_currency THEN
                RAISE EXCEPTION
                    'Payment currency mismatch for order %: payment=% order=%',
                    NEW.order_id, NEW.currency, order_currency
                    USING ERRCODE = 'check_violation';
            END IF;

            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_paid_payment_integrity ON payments;
        CREATE TRIGGER trg_paid_payment_integrity
        BEFORE INSERT OR UPDATE OF status, amount, currency, order_id ON payments
        FOR EACH ROW
        EXECUTE FUNCTION enforce_paid_payment_integrity();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_paid_payment_integrity ON payments;")
    op.execute("DROP FUNCTION IF EXISTS enforce_paid_payment_integrity();")

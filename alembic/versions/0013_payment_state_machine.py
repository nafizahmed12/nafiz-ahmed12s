"""Enforce valid payment status transitions at the database layer.

This protects payment records even if a future API endpoint accidentally
attempts an invalid status transition.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0013_payment_state"
down_revision: Union[str, Sequence[str], None] = "0012_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_payment_status_transition()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.status = OLD.status THEN
                RETURN NEW;
            END IF;

            IF OLD.status = 'pending'
               AND NEW.status IN ('initiated', 'paid', 'failed', 'cancelled') THEN
                RETURN NEW;
            END IF;

            IF OLD.status = 'initiated'
               AND NEW.status IN ('paid', 'failed', 'cancelled') THEN
                RETURN NEW;
            END IF;

            IF OLD.status = 'paid'
               AND NEW.status = 'refunded' THEN
                RETURN NEW;
            END IF;

            RAISE EXCEPTION
                'Invalid payment status transition: % -> %',
                OLD.status, NEW.status
                USING ERRCODE = 'check_violation';
        END;
        $$;
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_payment_status_transition ON payments;
        CREATE TRIGGER trg_payment_status_transition
        BEFORE UPDATE OF status ON payments
        FOR EACH ROW
        EXECUTE FUNCTION enforce_payment_status_transition();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_payment_status_transition ON payments;"
    )
    op.execute("DROP FUNCTION IF EXISTS enforce_payment_status_transition();")

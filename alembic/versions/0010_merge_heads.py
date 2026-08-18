"""Merge the supplier-fulfillment and digital/affiliate migration heads.

Revision ID: 0010_merge_heads
Revises: 0008_auto_supplier_fulfillment_on_payment, 0009_restore_stock
"""
from typing import Sequence, Union

revision: str = "0010_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0008_auto_supplier_fulfillment_on_payment",
    "0009_restore_stock",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""Merge the two 0016 migration heads."""

from typing import Sequence, Union

revision: str = "0017_merge_0016_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0016_payment_amount_integrity",
    "0016_seed_product_categories",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

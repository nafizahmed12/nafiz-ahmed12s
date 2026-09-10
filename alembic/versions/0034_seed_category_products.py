"""Seed customer-facing products for the built-in storefront categories.

Revision ID: 0034_seed_category_products
Revises: 0033_iphone_18pm_official_image
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0034_seed_category_products"
down_revision: Union[str, Sequence[str], None] = "0033_iphone_18pm_official_image"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRODUCTS = (
    ("fashion", "Classic Denim Jacket", "Classic blue denim jacket with a modern fit.", 2490.00, "NF-FASH-001", 25, "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?q=80&w=1000&auto=format&fit=crop"),
    ("fashion", "Premium Running Sneakers", "Lightweight everyday sneakers for training and casual wear.", 3290.00, "NF-FASH-002", 30, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=1000&auto=format&fit=crop"),
    ("fashion", "Minimal Leather Backpack", "Clean everyday backpack with a premium minimalist finish.", 2890.00, "NF-FASH-003", 18, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?q=80&w=1000&auto=format&fit=crop"),
    ("clothing", "Oxford Casual Shirt", "Breathable cotton Oxford shirt for work and weekend styling.", 1590.00, "NF-CLOT-001", 40, "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?q=80&w=1000&auto=format&fit=crop"),
    ("clothing", "Essential Cotton T-Shirt", "Soft heavyweight cotton T-shirt with a clean regular fit.", 790.00, "NF-CLOT-002", 60, "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?q=80&w=1000&auto=format&fit=crop"),
    ("clothing", "Slim Fit Chino Pants", "Versatile slim-fit chinos designed for everyday comfort.", 1790.00, "NF-CLOT-003", 35, "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?q=80&w=1000&auto=format&fit=crop"),
    ("beauty", "Hydrating Face Serum", "Lightweight daily serum formulated for a fresh hydrated finish.", 1290.00, "NF-BEAU-001", 22, "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?q=80&w=1000&auto=format&fit=crop"),
    ("beauty", "Gentle Face Cleanser", "Daily cleanser with a gentle, refreshing skincare feel.", 890.00, "NF-BEAU-002", 28, "https://images.unsplash.com/photo-1556229010-6c3f2c9ca5f8?q=80&w=1000&auto=format&fit=crop"),
    ("beauty", "Daily Moisturizer", "Lightweight moisturizer for a smooth everyday skincare routine.", 990.00, "NF-BEAU-003", 26, "https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?q=80&w=1000&auto=format&fit=crop"),
    ("accessories", "Classic Analog Watch", "Timeless analog watch with a clean everyday design.", 3490.00, "NF-ACC-001", 15, "https://images.unsplash.com/photo-1524805444758-089113d48a6d?q=80&w=1000&auto=format&fit=crop"),
    ("accessories", "Polarized Sunglasses", "Modern polarized sunglasses for daily outdoor use.", 1490.00, "NF-ACC-002", 32, "https://images.unsplash.com/photo-1511499767150-a48a237f0083?q=80&w=1000&auto=format&fit=crop"),
    ("accessories", "Premium Leather Wallet", "Slim leather wallet with practical everyday card storage.", 1190.00, "NF-ACC-003", 24, "https://images.unsplash.com/photo-1627123424574-724758594e93?q=80&w=1000&auto=format&fit=crop"),
)


def upgrade() -> None:
    bind = op.get_bind()
    category_stmt = text("SELECT id FROM product_categories WHERE LOWER(slug)=:slug LIMIT 1")
    exists_stmt = text("SELECT id FROM products WHERE slug=:slug LIMIT 1")
    insert_product = text("""
        INSERT INTO products
            (category_id,owner_id,name,slug,description,product_type,status,
             price,currency,sku,stock_quantity,created_at,updated_at)
        VALUES
            (:category_id,NULL,:name,:slug,:description,'physical','published',
             :price,'BDT',:sku,:stock,NOW(),NOW())
        RETURNING id
    """)
    insert_listing = text("""
        INSERT INTO product_listings
            (product_id,seller_id,supplier_product_id,listing_type,title,price,
             compare_at_price,currency,stock_quantity,status,featured,created_at,updated_at)
        VALUES
            (:product_id,NULL,NULL,'owned',:title,:price,NULL,'BDT',:stock,
             'published',FALSE,NOW(),NOW())
    """)
    insert_image = text("""
        INSERT INTO product_images(product_id,image_url,alt_text,sort_order,created_at)
        VALUES(:product_id,:image_url,:alt_text,0,NOW())
    """)

    for category_slug, name, description, price, sku, stock, image_url in PRODUCTS:
        category_id = bind.execute(category_stmt, {"slug": category_slug}).scalar_one_or_none()
        if category_id is None:
            continue
        slug = name.lower().replace(" ", "-")
        product_id = bind.execute(exists_stmt, {"slug": slug}).scalar_one_or_none()
        if product_id is None:
            product_id = bind.execute(insert_product, {
                "category_id": category_id, "name": name, "slug": slug,
                "description": description, "price": price, "sku": sku, "stock": stock,
            }).scalar_one()
        else:
            bind.execute(text("""
                UPDATE products SET category_id=:category_id,name=:name,
                    description=:description,product_type='physical',status='published',
                    price=:price,currency='BDT',sku=:sku,stock_quantity=:stock,updated_at=NOW()
                WHERE id=:product_id
            """), {
                "category_id": category_id, "name": name, "description": description,
                "price": price, "sku": sku, "stock": stock, "product_id": product_id,
            })

        listing_exists = bind.execute(text("SELECT id FROM product_listings WHERE product_id=:product_id LIMIT 1"), {"product_id": product_id}).scalar_one_or_none()
        if listing_exists is None:
            bind.execute(insert_listing, {"product_id": product_id, "title": name, "price": price, "stock": stock})
        image_exists = bind.execute(text("SELECT id FROM product_images WHERE product_id=:product_id LIMIT 1"), {"product_id": product_id}).scalar_one_or_none()
        if image_exists is None:
            bind.execute(insert_image, {"product_id": product_id, "image_url": image_url, "alt_text": name})


def downgrade() -> None:
    bind = op.get_bind()
    for _, name, *_ in PRODUCTS:
        slug = name.lower().replace(" ", "-")
        product_id = bind.execute(text("SELECT id FROM products WHERE slug=:slug LIMIT 1"), {"slug": slug}).scalar_one_or_none()
        if product_id is not None:
            bind.execute(text("DELETE FROM product_images WHERE product_id=:product_id"), {"product_id": product_id})
            bind.execute(text("DELETE FROM product_listings WHERE product_id=:product_id"), {"product_id": product_id})
            bind.execute(text("DELETE FROM products WHERE id=:product_id"), {"product_id": product_id})

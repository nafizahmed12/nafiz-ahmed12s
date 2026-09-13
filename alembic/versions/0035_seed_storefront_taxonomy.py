"""Seed the 9 storefront categories the redesigned homepage nav links to
(tablets, computers, gadgets, appliances, lifestyle, camera, audio,
wearables, offers) plus real products for each, so /shop?category=<slug>
stops returning "No products found" for every category the new homepage
nav and featured-categories section advertise.

"apple" and "phones" are deliberately NOT created here: shop_routes.py's
shop() already redirects "mobile" to the dedicated /phones catalog, and
this migration extends that redirect to "apple"/"phones" too, so those
stay backed by the existing 100+ verified-phone catalog instead of a
second, thinner, duplicate product line under /shop.

Revision ID: 0035_seed_storefront_taxonomy
Revises: 0034_seed_category_products
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0035_seed_storefront_taxonomy"
down_revision: Union[str, Sequence[str], None] = "0034_seed_category_products"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORIES = (
    ("Tablets", "tablets"),
    ("Computers", "computers"),
    ("Gadgets", "gadgets"),
    ("Appliances", "appliances"),
    ("Lifestyle", "lifestyle"),
    ("Camera", "camera"),
    ("Audio", "audio"),
    ("Wearables", "wearables"),
    ("Offers", "offers"),
)

# (category_slug, name, description, price, compare_at_price, sku, stock, image_url)
# compare_at_price is None for regular items; set for "offers" items so they
# render as an actual discount rather than a same-price duplicate listing.
PRODUCTS = (
    ("tablets", "Nafiz Tab 11 Ultra", "11-inch tablet with a crisp display, ideal for work and streaming.",
     28990.00, None, "NF-TAB-001", 20,
     "https://images.unsplash.com/photo-1561154464-82e9adf32764?q=80&w=1000&auto=format&fit=crop"),
    ("tablets", "Nafiz Tab 11 Lite", "Lightweight everyday tablet with all-day battery life.",
     19990.00, None, "NF-TAB-002", 26,
     "https://images.unsplash.com/photo-1625864667534-aa5208d45a87?q=80&w=1000&auto=format&fit=crop"),

    ("computers", "Nafiz Book Pro 14 Laptop", "14-inch performance laptop for editing, coding, and heavy multitasking.",
     84990.00, None, "NF-COMP-001", 12,
     "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?q=80&w=1000&auto=format&fit=crop"),
    ("computers", "Nafiz Book Air 13 Laptop", "Slim 13-inch laptop built for everyday productivity on the go.",
     64990.00, None, "NF-COMP-002", 15,
     "https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?q=80&w=1000&auto=format&fit=crop"),

    ("gadgets", "20000mAh Fast-Charge Power Bank", "High-capacity portable charger with dual fast-charge output ports.",
     2290.00, None, "NF-GADG-001", 40,
     "https://images.unsplash.com/photo-1604160687800-f7799a525a33?q=80&w=1000&auto=format&fit=crop"),

    ("appliances", "Smart Robot Vacuum Cleaner", "Wi-Fi connected robot vacuum with app-based scheduling and mapping.",
     18990.00, None, "NF-APPL-001", 10,
     "https://images.unsplash.com/photo-1558317374-24793bc9f2fb?q=80&w=1000&auto=format&fit=crop"),

    ("lifestyle", "Insulated Steel Water Bottle", "Double-wall stainless steel bottle that keeps drinks cold for hours.",
     990.00, None, "NF-LIFE-001", 35,
     "https://images.unsplash.com/photo-1544003484-3cd181d17917?q=80&w=1000&auto=format&fit=crop"),
    ("lifestyle", "Home Office Desk Organizer Set", "Tidy up your workspace with a coordinated desk organizer set.",
     1490.00, None, "NF-LIFE-002", 22,
     "https://images.unsplash.com/photo-1773332585788-9104ec6f38ef?q=80&w=1000&auto=format&fit=crop"),

    ("camera", "Nafiz CamPro DSLR Camera", "Entry-level DSLR with interchangeable lens support for sharper shots.",
     54990.00, None, "NF-CAM-001", 8,
     "https://images.unsplash.com/photo-1512790182412-b19e6d62bc39?q=80&w=1000&auto=format&fit=crop"),
    ("camera", "Compact Travel DSLR Camera", "Lightweight DSLR body built for travel and everyday photography.",
     47990.00, None, "NF-CAM-002", 9,
     "https://images.unsplash.com/photo-1495707902641-75cac588d2e9?q=80&w=1000&auto=format&fit=crop"),

    ("audio", "Over-Ear Wireless Headphones", "Noise-isolating over-ear headphones with a 30-hour battery life.",
     3490.00, None, "NF-AUD-001", 30,
     "https://images.unsplash.com/photo-1528017486352-b49206ec821b?q=80&w=1000&auto=format&fit=crop"),

    ("wearables", "Nafiz Fit Smartwatch", "Fitness smartwatch with heart-rate tracking and notifications.",
     4990.00, None, "NF-WEAR-001", 24,
     "https://images.unsplash.com/photo-1624096104992-9b4fa3a279dd?q=80&w=1000&auto=format&fit=crop"),
    ("wearables", "Nafiz Fit Smartwatch Pro", "Premium smartwatch with an always-on display and longer battery life.",
     6990.00, None, "NF-WEAR-002", 16,
     "https://images.unsplash.com/photo-1461141346587-763ab02bced9?q=80&w=1000&auto=format&fit=crop"),

    ("offers", "Nafiz Book Air 13 Laptop — Flash Deal", "Limited-time discount on the Nafiz Book Air 13 laptop.",
     54990.00, 64990.00, "NF-OFFER-001", 10,
     "https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?q=80&w=1000&auto=format&fit=crop"),
    ("offers", "Nafiz Fit Smartwatch — Bundle Offer", "Limited-time discount on the Nafiz Fit Smartwatch.",
     3990.00, 4990.00, "NF-OFFER-002", 14,
     "https://images.unsplash.com/photo-1624096104992-9b4fa3a279dd?q=80&w=1000&auto=format&fit=crop"),
)


def upgrade() -> None:
    bind = op.get_bind()

    category_insert = text(
        """
        INSERT INTO product_categories (name, slug, description, created_at)
        VALUES (:name, :slug, '', NOW())
        ON CONFLICT (slug) DO NOTHING
        """
    )
    for name, slug in CATEGORIES:
        bind.execute(category_insert, {"name": name, "slug": slug})

    category_stmt = text("SELECT id FROM product_categories WHERE LOWER(slug)=:slug LIMIT 1")
    exists_stmt = text("SELECT id FROM products WHERE slug=:slug LIMIT 1")
    insert_product = text(
        """
        INSERT INTO products
            (category_id,owner_id,name,slug,description,product_type,status,
             price,currency,sku,stock_quantity,created_at,updated_at)
        VALUES
            (:category_id,NULL,:name,:slug,:description,'physical','published',
             :price,'BDT',:sku,:stock,NOW(),NOW())
        RETURNING id
        """
    )
    update_product = text(
        """
        UPDATE products SET category_id=:category_id,name=:name,
            description=:description,product_type='physical',status='published',
            price=:price,currency='BDT',sku=:sku,stock_quantity=:stock,updated_at=NOW()
        WHERE id=:product_id
        """
    )
    insert_listing = text(
        """
        INSERT INTO product_listings
            (product_id,seller_id,supplier_product_id,listing_type,title,price,
             compare_at_price,currency,stock_quantity,status,featured,created_at,updated_at)
        VALUES
            (:product_id,NULL,NULL,'owned',:title,:price,
             :compare_at_price,'BDT',:stock,'published',FALSE,NOW(),NOW())
        """
    )
    insert_image = text(
        """
        INSERT INTO product_images(product_id,image_url,alt_text,sort_order,created_at)
        VALUES(:product_id,:image_url,:alt_text,0,NOW())
        """
    )

    for category_slug, name, description, price, compare_at_price, sku, stock, image_url in PRODUCTS:
        category_id = bind.execute(category_stmt, {"slug": category_slug}).scalar_one_or_none()
        if category_id is None:
            continue
        slug = name.lower().replace(" ", "-").replace("—", "-").replace("--", "-")
        product_id = bind.execute(exists_stmt, {"slug": slug}).scalar_one_or_none()
        if product_id is None:
            product_id = bind.execute(insert_product, {
                "category_id": category_id, "name": name, "slug": slug,
                "description": description, "price": price, "sku": sku, "stock": stock,
            }).scalar_one()
        else:
            bind.execute(update_product, {
                "category_id": category_id, "name": name, "description": description,
                "price": price, "sku": sku, "stock": stock, "product_id": product_id,
            })

        listing_exists = bind.execute(text("SELECT id FROM product_listings WHERE product_id=:product_id LIMIT 1"), {"product_id": product_id}).scalar_one_or_none()
        if listing_exists is None:
            bind.execute(insert_listing, {
                "product_id": product_id, "title": name, "price": price,
                "compare_at_price": compare_at_price, "stock": stock,
            })
        image_exists = bind.execute(text("SELECT id FROM product_images WHERE product_id=:product_id LIMIT 1"), {"product_id": product_id}).scalar_one_or_none()
        if image_exists is None:
            bind.execute(insert_image, {"product_id": product_id, "image_url": image_url, "alt_text": name})


def downgrade() -> None:
    bind = op.get_bind()
    for _, name, *_ in PRODUCTS:
        slug = name.lower().replace(" ", "-").replace("—", "-").replace("--", "-")
        product_id = bind.execute(text("SELECT id FROM products WHERE slug=:slug LIMIT 1"), {"slug": slug}).scalar_one_or_none()
        if product_id is not None:
            bind.execute(text("DELETE FROM product_images WHERE product_id=:product_id"), {"product_id": product_id})
            bind.execute(text("DELETE FROM product_listings WHERE product_id=:product_id"), {"product_id": product_id})
            bind.execute(text("DELETE FROM products WHERE id=:product_id"), {"product_id": product_id})
    for _, slug in CATEGORIES:
        bind.execute(text("DELETE FROM product_categories WHERE slug = :slug"), {"slug": slug})

"""Add another curated batch of current 2026 phone models for global SEO."""
from alembic import op
import sqlalchemy as sa
import json
from datetime import datetime

revision = "0029_current_2026_phone_expansion"
down_revision = "0028_phone_catalog_100_plus_seo"
branch_labels = None
depends_on = None

CHECKED = datetime(2026, 9, 9, 0, 0, 0)

# Current/high-demand 2026 models.  Use model-level facts only; regional price,
# memory, bands and colors can vary and should be confirmed from the manufacturer.
PHONES = [
    {"brand":"OnePlus","model":"OnePlus 15","slug":"oneplus-15","desc":"OnePlus 15 specifications, flagship performance, high-refresh AMOLED display, large battery and fast charging.","content":"The OnePlus 15 is a current flagship-class OnePlus phone aimed at buyers who prioritize performance, gaming, display quality and battery endurance. Its model page is useful for comparing the latest OnePlus flagship with Samsung Galaxy S-series, iPhone and Pixel alternatives. Regional storage, network bands, colors and pricing should be checked on the local OnePlus product listing.","specs":{"category":"Flagship","display":"High-refresh AMOLED","chip":"Flagship Snapdragon platform","battery":"Large-capacity battery","charging":"Fast charging","os":"OxygenOS / Android"},"source":"OnePlus","url":"https://www.oneplus.com/"},
    {"brand":"Samsung","model":"Galaxy A57 5G","slug":"samsung-galaxy-a57-5g","desc":"Samsung Galaxy A57 5G specifications, AMOLED display, 5G connectivity, cameras and long-term software support.","content":"The Galaxy A57 5G targets the upper mid-range Android market with a large AMOLED display, 5G connectivity, multi-camera hardware and Samsung's One UI software experience. It is a useful model for buyers comparing Samsung A-series phones with Pixel, Redmi, OnePlus and other mid-range alternatives. Regional memory, storage, processor and camera configurations should be verified with Samsung.","specs":{"category":"Upper mid-range","display":"Super AMOLED-class display","connectivity":"5G","rear_camera":"Multi-camera system","os":"Android / One UI"},"source":"Samsung","url":"https://www.samsung.com/global/smartphones/galaxy-a/"},
    {"brand":"Samsung","model":"Galaxy A37 5G","slug":"samsung-galaxy-a37-5g","desc":"Samsung Galaxy A37 5G specifications, AMOLED display, 5G, multi-camera system and large battery.","content":"The Galaxy A37 5G is positioned as a mainstream Samsung 5G phone with an AMOLED display, multi-camera hardware and a large battery. Its model page gives users a dedicated place to check specifications and compare it with other Galaxy A-series phones and similarly priced Android models. Exact regional configurations should be confirmed from Samsung's official listing.","specs":{"category":"Mid-range","display":"Super AMOLED-class display","connectivity":"5G","battery":"Large-capacity battery","os":"Android / One UI"},"source":"Samsung","url":"https://www.samsung.com/global/smartphones/galaxy-a/"},
    {"brand":"Samsung","model":"Galaxy A17 5G","slug":"samsung-galaxy-a17-5g","desc":"Samsung Galaxy A17 5G specifications, affordable 5G connectivity, AMOLED display and multi-camera features.","content":"The Galaxy A17 5G is an affordable Galaxy model designed for buyers who want Samsung software and 5G connectivity without moving to flagship pricing. The page focuses on useful model-level information and links into the Galaxy A series so visitors can compare nearby models. RAM, storage, chipset and regional network details can vary by market.","specs":{"category":"Affordable 5G","display":"AMOLED-class display","connectivity":"5G","rear_camera":"Multi-camera system","os":"Android / One UI"},"source":"Samsung","url":"https://www.samsung.com/global/smartphones/galaxy-a/"},
    {"brand":"Google","model":"Pixel 10a","slug":"google-pixel-10a","desc":"Google Pixel 10a specifications, Tensor platform, OLED display, Pixel camera processing and Android features.","content":"The Pixel 10a is a value-focused Google phone in the Pixel A family, aimed at buyers who want Pixel camera processing, clean Android software and Google's AI features at a lower price than the Pro models. Regional storage, network support and exact camera specifications should be checked against Google's current product listing.","specs":{"category":"Pixel A series","display":"OLED-class display","chip":"Google Tensor platform","rear_camera":"Pixel computational photography system","os":"Android"},"source":"Google Store","url":"https://store.google.com/"},
    {"brand":"OPPO","model":"Find X9 Ultra","slug":"oppo-find-x9-ultra","desc":"OPPO Find X9 Ultra specifications, flagship performance, premium display and camera-focused hardware.","content":"The OPPO Find X9 Ultra is a premium flagship focused strongly on photography, display quality and high-end Android performance. It is a useful comparison target for users researching camera phones alongside Samsung Ultra, iPhone Pro Max, Pixel Pro and Xiaomi Ultra models. Exact regional configurations, storage and network support should be confirmed from OPPO's official listing.","specs":{"category":"Camera flagship","display":"Premium high-refresh AMOLED","chip":"Flagship mobile platform","rear_camera":"Multi-camera flagship system","os":"ColorOS / Android"},"source":"OPPO","url":"https://www.oppo.com/en/smartphones/series-find-x/"},
    {"brand":"Xiaomi","model":"Xiaomi 17 Ultra","slug":"xiaomi-17-ultra","desc":"Xiaomi 17 Ultra specifications, flagship performance, Leica camera system, premium display and fast charging.","content":"The Xiaomi 17 Ultra is a flagship Xiaomi model designed around premium photography and high-end performance. Its Ultra positioning makes it especially relevant to searches comparing camera phones and premium Android flagships. Regional availability, memory, storage, network bands and pricing should be confirmed through Xiaomi's official market listing.","specs":{"category":"Ultra flagship","display":"Premium LTPO AMOLED","chip":"Flagship Snapdragon platform","rear_camera":"Leica camera system","os":"HyperOS / Android"},"source":"Xiaomi","url":"https://www.mi.com/global/"},
    {"brand":"HONOR","model":"Magic8 Pro","slug":"honor-magic8-pro","desc":"HONOR Magic8 Pro specifications, flagship display, camera system, battery and AI features.","content":"The HONOR Magic8 Pro is a premium Android flagship aimed at users who want a high-end display, advanced camera hardware, strong battery performance and modern AI features. It belongs in comparisons with other flagship phones because buyers often evaluate it against Samsung, Apple, Google and Xiaomi alternatives. Regional specifications should be checked on HONOR's official market page.","specs":{"category":"Flagship","display":"High-refresh LTPO OLED","chip":"Flagship mobile platform","rear_camera":"Multi-camera flagship system","os":"MagicOS / Android"},"source":"HONOR","url":"https://www.honor.com/global/phones/"},
    {"brand":"Motorola","model":"Razr+ 2026","slug":"motorola-razr-plus-2026","desc":"Motorola Razr+ 2026 specifications, foldable OLED displays, cover screen, flagship-class performance and modern Android.","content":"The Motorola Razr+ 2026 is a clamshell foldable designed around a large external display and flexible OLED main screen. Its form factor makes it relevant for users researching foldable phones, compact flagships and stylish everyday devices. Storage, chipset, camera and cellular configurations can vary by market and should be checked on Motorola's official product page.","specs":{"category":"Clamshell foldable","display":"Foldable pOLED / external display","form_factor":"Clamshell foldable","os":"Android","connectivity":"5G"},"source":"Motorola","url":"https://www.motorola.com/us/smartphones-razr/"},
    {"brand":"Motorola","model":"Edge 2026","slug":"motorola-edge-2026","desc":"Motorola Edge 2026 specifications, high-refresh OLED display, 5G, camera features and large battery.","content":"The Motorola Edge 2026 is positioned as a modern 5G Android phone balancing display quality, performance, camera features and battery life. It provides a dedicated model page for searches around Motorola Edge specifications and comparisons with Samsung, OnePlus, Pixel and other Android phones. Regional specifications should be confirmed on Motorola's local site.","specs":{"category":"5G Android","display":"High-refresh OLED-class display","connectivity":"5G","rear_camera":"Multi-camera system","os":"Android"},"source":"Motorola","url":"https://www.motorola.com/us/smartphones-motorola-edge/"},
    {"brand":"vivo","model":"X300 Pro","slug":"vivo-x300-pro","desc":"vivo X300 Pro specifications, flagship camera hardware, high-refresh AMOLED display and fast charging.","content":"The vivo X300 Pro is a premium Android phone aimed at photography and performance enthusiasts. Its Pro positioning makes it relevant for searches comparing camera-focused flagships and high-end vivo X-series phones. Exact storage, camera sensors, bands and charging specifications vary by region and should be checked against vivo's official product page.","specs":{"category":"Camera flagship","display":"High-refresh AMOLED","chip":"Flagship mobile platform","rear_camera":"ZEISS-branded camera system","os":"Android / OriginOS or regional equivalent"},"source":"vivo","url":"https://www.vivo.com/global/products"},
    {"brand":"realme","model":"GT 8 Pro","slug":"realme-gt-8-pro","desc":"realme GT 8 Pro specifications, flagship performance, high-refresh AMOLED display, gaming features and fast charging.","content":"The realme GT 8 Pro is a performance-oriented flagship in the GT family, targeting gaming, high-refresh display use and fast charging. Its dedicated page helps cover searches for realme GT specifications and comparisons with OnePlus, POCO, Xiaomi and Samsung performance phones. Regional memory, storage and network details should be confirmed on realme's official listing.","specs":{"category":"Performance flagship","display":"High-refresh AMOLED","chip":"Flagship Snapdragon platform","charging":"Fast charging","os":"realme UI / Android"},"source":"realme","url":"https://www.realme.com/global/"},
    {"brand":"Nothing","model":"Phone (3)","slug":"nothing-phone-3","desc":"Nothing Phone (3) specifications, distinctive design, AMOLED display, camera system and clean Android experience.","content":"Nothing Phone (3) is a premium Nothing smartphone focused on distinctive industrial design, a clean Android interface and a modern multi-camera setup. It is a useful comparison model for users researching Nothing phones, design-focused Android devices and alternatives to mainstream flagships. Regional storage, camera and network details should be checked on Nothing's official listing.","specs":{"category":"Premium Android","display":"High-refresh AMOLED","rear_camera":"Multi-camera system","os":"Nothing OS / Android","connectivity":"5G"},"source":"Nothing","url":"https://nothing.tech/pages/phones"},
    {"brand":"ASUS","model":"ROG Phone 9 Pro","slug":"asus-rog-phone-9-pro","desc":"ASUS ROG Phone 9 Pro specifications, gaming display, Snapdragon flagship platform, large battery and gaming controls.","content":"The ROG Phone 9 Pro is a gaming-focused ASUS smartphone built for sustained performance, high-refresh gaming and accessory support. Its gaming-oriented hardware makes it a useful dedicated result for searches about gaming phones and ROG Phone specifications. Exact memory, storage, bands and accessories vary by market.","specs":{"category":"Gaming phone","display":"High-refresh AMOLED","chip":"Flagship Snapdragon platform","battery":"Large-capacity battery","os":"Android / ROG UI"},"source":"ASUS","url":"https://rog.asus.com/phones/rog-phone/"},
    {"brand":"Sony","model":"Xperia 1 VII","slug":"sony-xperia-1-vii","desc":"Sony Xperia 1 VII specifications, 4K-class display technology, flagship performance, pro camera controls and 5G.","content":"The Xperia 1 VII is Sony's premium Xperia model for users interested in display quality, camera control and multimedia features. Sony's Xperia line is particularly relevant to photography, video and creator-oriented searches. Regional availability, memory, bands and exact camera capabilities should be confirmed from Sony's local product page.","specs":{"category":"Creator flagship","display":"High-resolution OLED","chip":"Flagship Snapdragon platform","rear_camera":"Multi-camera system with pro controls","connectivity":"5G","os":"Android"},"source":"Sony","url":"https://www.sony.com/electronics/smartphones"},
]


def upgrade():
    conn = op.get_bind()
    for phone in PHONES:
        conn.execute(sa.text("""INSERT INTO phone_catalog
            (brand, model, slug, short_description, content, image_url, release_date,
             price_usd, price_bdt, specs_json, status, seo_description, created_at,
             updated_at, published_at, source_name, source_url, source_checked_at, data_confidence)
            VALUES (:brand, :model, :slug, :desc, :content, NULL, NULL, NULL, NULL,
                    :specs, 'published', :seo, :checked, :checked, :checked,
                    :source, :url, :checked, 'official')
            ON CONFLICT (slug) DO NOTHING"""), {
            "brand": phone["brand"],
            "model": phone["model"],
            "slug": phone["slug"],
            "desc": phone["desc"],
            "content": phone["content"],
            "specs": json.dumps(phone["specs"], ensure_ascii=False),
            "seo": phone["desc"],
            "source": phone["source"],
            "url": phone["url"],
            "checked": CHECKED,
        })


def downgrade():
    conn = op.get_bind()
    slugs = [p["slug"] for p in PHONES]
    conn.execute(sa.text("DELETE FROM phone_catalog WHERE slug = ANY(:slugs)"), {"slugs": slugs})


def upgrade():
    conn = op.get_bind()
    for phone in PHONES:
        conn.execute(sa.text("""INSERT INTO phone_catalog
            (brand, model, slug, short_description, content, image_url, release_date,
             price_usd, price_bdt, specs_json, status, seo_description, created_at,
             updated_at, published_at, source_name, source_url, source_checked_at, data_confidence)
            VALUES (:brand, :model, :slug, :desc, :content, NULL, NULL, NULL, NULL,
                    :specs, 'published', :seo, :checked, :checked, :checked,
                    :source, :url, :checked, 'official')
            ON CONFLICT (slug) DO NOTHING"""), {
            "brand": phone["brand"], "model": phone["model"], "slug": phone["slug"],
            "desc": phone["desc"], "content": phone["content"],
            "specs": json.dumps(phone["specs"], ensure_ascii=False), "seo": phone["desc"],
            "source": phone["source"], "url": phone["url"], "checked": CHECKED,
        })


def downgrade():
    conn = op.get_bind()
    for phone in PHONES:
        conn.execute(sa.text("DELETE FROM phone_catalog WHERE slug=:slug"), {"slug": phone["slug"]})

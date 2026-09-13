"""Seed original evergreen technology articles for the public blog.

Revision ID: 0036_seed_editorial_blog
Revises: 0035_seed_storefront_taxonomy
"""
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import text

revision = "0036_seed_editorial_blog"
down_revision = "0035_seed_storefront_taxonomy"
branch_labels = None
depends_on = None

ARTICLES = [
    {
        "title": "How to Choose a Smartphone in 2026: A Practical Checklist",
        "slug": "how-to-choose-a-smartphone-2026",
        "excerpt": "A practical checklist for choosing a smartphone by budget, display, performance, camera, battery and software support.",
        "category": "Buying Guides",
        "content": "Choosing a smartphone is easier when you separate the features you need from specifications that only look impressive. Start with a realistic budget, then identify the tasks you do most often.\n\nSet your budget and priorities first. Include accessories, warranty and storage needs in the total cost. A balanced mid-range phone can be better value than a premium model if you do not need flagship hardware.\n\nFor performance, consider the processor, storage speed, RAM and thermal behavior together. Gaming and heavy multitasking need more sustained performance than messaging, browsing and streaming.\n\nFor the display, compare panel type, brightness, refresh rate and size. For cameras, look beyond megapixels and check sensor quality, stabilization, autofocus, lenses and image processing.\n\nBattery capacity is only part of endurance. Display efficiency, chipset efficiency, software and network conditions also matter. Finally, check software support, warranty, network compatibility and the exact model number before buying.",
    },
    {
        "title": "AMOLED vs LCD Phone Displays: What Actually Matters?",
        "slug": "amoled-vs-lcd-phone-displays",
        "excerpt": "Understand the practical differences between AMOLED and LCD displays, including contrast, brightness and refresh rate.",
        "category": "Display",
        "content": "AMOLED and LCD are both capable phone-display technologies, but they work differently. AMOLED pixels emit their own light, allowing individual pixels to turn off for very deep blacks and strong contrast. LCD panels use a backlight and can still provide sharp, bright and accurate images.\n\nRefresh rate is separate from panel type. Both LCD and OLED phones can use high refresh rates, which can make scrolling and supported games feel smoother. Higher refresh rates may also increase power use, although adaptive systems can reduce that cost.\n\nOutdoor readability depends on more than a peak brightness number. Sustained brightness, reflections, automatic brightness behavior and the display surface all matter. Choose AMOLED when deep blacks and premium contrast are priorities; a well-tuned LCD can still be excellent at a lower price.",
    },
    {
        "title": "How Much RAM and Storage Does a Phone Need?",
        "slug": "how-much-phone-ram-and-storage-do-you-need",
        "excerpt": "RAM and storage solve different problems. Learn how to choose enough of each for apps, gaming, photos and long-term use.",
        "category": "Buying Guides",
        "content": "RAM helps the operating system keep active apps available, while storage holds apps, photos, videos and files. They should not be treated as the same specification.\n\nFor everyday users, overall software quality and processor efficiency matter more than simply choosing the largest RAM number. Gamers and heavy multitaskers can benefit from additional physical RAM, but extra RAM cannot compensate for weak hardware or poor optimization.\n\nStorage deserves attention because photos, videos, games and offline downloads grow over time. If a phone has no microSD slot, choose an internal capacity that can cover several years of use. Also verify whether advertised memory includes virtual RAM, which is not equivalent to physical RAM.",
    },
    {
        "title": "How to Choose a Phone With Good Battery Life",
        "slug": "how-to-choose-phone-good-battery-life",
        "excerpt": "Battery capacity is useful, but real endurance also depends on the display, chipset, software and network conditions.",
        "category": "Battery",
        "content": "A large battery does not automatically make a phone long-lasting. Capacity should be considered together with display size, brightness, refresh rate and processor efficiency.\n\nModern chipsets can deliver more performance per watt than older designs. Software optimization also affects standby time and everyday endurance. Weak cellular signals can increase power consumption because the phone works harder to maintain communication.\n\nFast charging is valuable if you often need a quick top-up. Check supported charging standards and whether the required charger is included. When comparing phones, use independent endurance tests where possible instead of relying on battery capacity alone.",
    },
    {
        "title": "5G Phone Buying Guide: Check These Things Before You Buy",
        "slug": "5g-phone-buying-guide",
        "excerpt": "A 5G label is not enough. Check the exact model, supported bands, SIM configuration and regional compatibility.",
        "category": "Connectivity",
        "content": "A phone can support 5G and still be a poor match for a particular carrier or region. Imported devices deserve extra attention.\n\nStart with the exact model number and compare its 5G and LTE bands with the networks you use. LTE support remains important because a phone does not stay on 5G all the time. Check SIM and eSIM support as well because regional variants can differ.\n\nImported phones can also have different firmware, warranty coverage and regional features. Verify the complete configuration before paying, especially when a foreign listing is much cheaper than local alternatives.",
    },
    {
        "title": "Flagship vs Mid-Range Phones: Which Should You Buy?",
        "slug": "flagship-vs-mid-range-phones",
        "excerpt": "Flagships offer premium hardware, while strong mid-range phones can deliver better value for everyday use.",
        "category": "Comparisons",
        "content": "Flagship phones usually lead in processor performance, camera systems, display quality, materials and premium features. They can be worth the extra cost for demanding gaming, photography or long-term premium ownership.\n\nMid-range phones can be better value for browsing, messaging, streaming, casual gaming and normal photography. Many provide excellent displays, capable cameras and strong battery life without paying for hardware you may never use.\n\nMake the decision from your actual priorities. If advanced cameras, sustained performance or premium build quality are essential, a flagship may justify its price. Otherwise, a well-chosen mid-range model can provide a more efficient use of your budget.",
    },
    {
        "title": "Phone Camera Buying Guide: Look Beyond Megapixels",
        "slug": "phone-camera-buying-guide",
        "excerpt": "Sensor size, stabilization, lenses, autofocus, zoom and image processing all affect smartphone camera quality.",
        "category": "Cameras",
        "content": "Megapixels describe image resolution, not overall camera quality. The main sensor, lens quality, aperture, autofocus and stabilization often have a larger practical impact.\n\nOptical image stabilization can reduce camera shake and help produce sharper low-light photos. A useful telephoto camera can be more valuable for distant subjects than a very high megapixel count, while an ultrawide camera helps with landscapes and groups.\n\nFor video, compare stabilization, autofocus, frame rates, resolution and consistency between cameras. Computational photography also matters because exposure, HDR, color and night processing can make two phones with similar hardware produce very different results.",
    },
    {
        "title": "Phone Buying Mistakes That Are Easy to Avoid",
        "slug": "common-phone-buying-mistakes",
        "excerpt": "Avoid common smartphone shopping mistakes such as chasing specifications and ignoring regional variants or software support.",
        "category": "Buying Advice",
        "content": "One common mistake is buying by a single specification such as megapixels or RAM. A large number does not guarantee a better camera or faster experience.\n\nAnother mistake is ignoring the exact model number. Regional variants can have different network bands, SIM options, storage configurations and warranties. Storage is another frequent problem: a phone that feels spacious today can become restrictive after years of photos and videos.\n\nCheck software-support expectations, warranty terms, repair options and the real local price. Finally, verify important specifications using manufacturer information and reputable independent reviews rather than trusting every specification page.",
    },
    {
        "title": "How to Compare Phones Without Getting Lost in Specifications",
        "slug": "how-to-compare-phones-effectively",
        "excerpt": "Use a consistent framework for comparing phones by display, performance, cameras, battery, software and value.",
        "category": "Comparisons",
        "content": "A useful phone comparison answers a buying question rather than producing the longest specification table. Start with phones that fit the same realistic budget.\n\nCompare displays by panel type, size, brightness and refresh rate. Compare performance using the processor, storage speed, RAM and sustained behavior. For cameras, evaluate the main sensor, stabilization, zoom, ultrawide quality and video rather than simply counting cameras.\n\nThen compare battery endurance, charging, software support and warranty. Finish by explaining trade-offs: one phone may be best for gaming, another for photography, another for battery life. A clear comparison helps readers choose according to their priorities.",
    },
    {
        "title": "Phone Storage, Cloud Backup and Photo Management Tips",
        "slug": "phone-storage-and-photo-management-tips",
        "excerpt": "Keep phone storage manageable with practical habits for photos, videos, downloads, apps and backups.",
        "category": "Phone Tips",
        "content": "Storage problems usually build gradually. Start with the phone's storage settings and identify the categories using the most space. Large videos, downloads and messaging-media folders are often major contributors.\n\nRemove old downloads carefully and review large files before deleting them. If you use cloud photo backup, confirm that important files are actually backed up before removing local copies. Backup is protection against loss, not a reason to delete files blindly.\n\nLeave reasonable free space for system updates and new recordings. If you regularly record high-resolution video, install large games or keep files offline, choose a higher internal-storage configuration when you buy the phone.",
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    exists_stmt = text("SELECT id FROM blog_articles WHERE slug=:slug LIMIT 1")
    insert_stmt = text("""INSERT INTO blog_articles
        (title,slug,excerpt,content,category,featured_image_url,seo_description,status,created_at,updated_at,published_at)
        VALUES (:title,:slug,:excerpt,:content,:category,NULL,:seo_description,'published',:now,:now,:now)""")
    for article in ARTICLES:
        if bind.execute(exists_stmt, {"slug": article["slug"]}).scalar_one_or_none() is not None:
            continue
        bind.execute(insert_stmt, {
            **article,
            "seo_description": article["excerpt"],
            "now": now,
        })


def downgrade() -> None:
    bind = op.get_bind()
    for article in ARTICLES:
        bind.execute(
            text("DELETE FROM blog_articles WHERE slug=:slug"),
            {"slug": article["slug"]},
        )

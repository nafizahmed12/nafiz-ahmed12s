"""Seed a small set of original evergreen technology articles.

Revision ID: 0032_seed_editorial_blog
Revises: 0031_iphone_18_pro_max
"""
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import text

revision = "0032_seed_editorial_blog"
down_revision = "0031_iphone_18_pro_max"
branch_labels = None
depends_on = None

ARTICLES = [
    {
        "title": "How to Choose a Smartphone in 2026: A Practical Checklist",
        "slug": "how-to-choose-a-smartphone-2026",
        "excerpt": "A practical checklist for choosing a smartphone by budget, display, performance, camera, battery, software support and network compatibility.",
        "category": "Buying Guides",
        "content": "Choosing a smartphone is easier when you separate the features you need from the specifications that simply look impressive. Start with a realistic budget, then identify the tasks you do most often.\n\nBudget and priorities\nSet a maximum comfortable price before comparing models. If you need a case, charger or extra storage, include those costs in the budget. For most people, a balanced mid-range phone is better value than a device that spends the entire budget on one premium feature.\n\nPerformance\nFor messaging, browsing, video and normal apps, a modern mid-range processor is usually sufficient. Gaming, video editing and heavy multitasking benefit from a faster chipset and better thermal management. RAM matters, but processor efficiency, storage speed and software optimization matter too.\n\nDisplay\nConsider panel type, brightness, refresh rate and size. OLED can provide strong contrast and deep blacks, while a high refresh rate can make scrolling feel smoother. Outdoor brightness is especially important if you use navigation or social apps outside.\n\nCamera\nDo not judge a camera by megapixels alone. Sensor size, stabilization, autofocus, lens quality and image processing all affect results. If you frequently photograph distant subjects, check whether a useful telephoto camera is included.\n\nBattery and charging\nBattery capacity is only one part of endurance. Display power use, chipset efficiency, software and network conditions also affect battery life. Fast charging is useful for people who regularly need a quick top-up.\n\nLong-term ownership\nCheck software support, repair options, storage capacity and regional network compatibility. If you plan to keep the phone for several years, these factors can be more important than a small benchmark advantage.\n\nFinal checklist\nBefore buying, verify the exact model number, storage configuration, local price, warranty terms, network bands and current software-support policy. Product specifications and prices can change, so confirm the latest details before checkout.",
    },
    {
        "title": "AMOLED vs LCD Phone Displays: What Actually Matters?",
        "slug": "amoled-vs-lcd-phone-displays",
        "excerpt": "Understand the practical differences between AMOLED and LCD displays, including contrast, brightness, refresh rate, battery use and viewing comfort.",
        "category": "Display",
        "content": "The display is one of the parts of a phone you use constantly. AMOLED and LCD are both capable technologies, but they behave differently and can suit different budgets and priorities.\n\nHow AMOLED works\nAMOLED displays use self-emitting pixels. A pixel can be turned off to produce very deep blacks, which gives OLED screens strong contrast. This can also make dark interfaces look particularly good.\n\nHow LCD works\nLCD panels use a backlight behind the display layer. They can still deliver sharp, bright and accurate images, and they remain common on lower-cost devices. Black areas usually appear less deep because the backlight remains active.\n\nRefresh rate\nRefresh rate is separate from panel type. Both LCD and OLED phones can offer high refresh rates. A higher rate can make supported scrolling and games feel smoother, although it can increase power use. Adaptive refresh behavior can reduce that cost.\n\nBrightness\nDo not compare phones using a peak-brightness number alone. Real-world outdoor readability depends on sustained brightness, automatic brightness behavior, reflections and the display surface.\n\nWhich should you choose?\nIf you value deep blacks, high contrast and a premium viewing experience, AMOLED is often attractive. If your budget is tighter, a well-tuned LCD can still be an excellent everyday display. The best choice depends on the whole phone rather than the panel label alone.",
    },
    {
        "title": "How Much RAM and Storage Does a Phone Need?",
        "slug": "how-much-phone-ram-and-storage-do-you-need",
        "excerpt": "RAM and storage solve different problems. Learn how to choose enough of each for everyday apps, gaming, photos and long-term use.",
        "category": "Buying Guides",
        "content": "RAM and storage are often discussed together, but they do different jobs. RAM helps the operating system keep active apps available, while storage holds apps, photos, videos and files.\n\nRAM for everyday users\nPeople who mainly browse, message, stream and use social apps should focus on overall software quality rather than buying a phone solely because it has a large RAM number. Memory management varies between operating systems and manufacturers.\n\nRAM for gaming and multitasking\nHeavy multitaskers and gamers can benefit from additional memory, especially when switching between large apps or games. However, a fast and efficient processor is still essential. More RAM cannot compensate for weak hardware or poor software optimization.\n\nStorage\nStorage becomes important when you keep many photos, videos, games or offline downloads. High-resolution video can consume space quickly. If a phone does not support a microSD card, choose enough internal storage for the years you expect to keep it.\n\nA simple rule\nReview your current storage usage and imagine adding another year or two of photos, videos and apps. Buying enough storage at the start is often better than trying to manage a nearly full phone later.\n\nBefore buying\nCheck the exact storage configuration because the same phone may be sold with different capacities in different markets. Also check whether the advertised RAM includes virtual or extended memory, which is not equivalent to physical RAM.",
    },
    {
        "title": "How to Choose a Phone With Good Battery Life",
        "slug": "how-to-choose-phone-good-battery-life",
        "excerpt": "Battery capacity is useful, but endurance also depends on the display, chipset, software and network conditions.",
        "category": "Battery",
        "content": "A large battery does not automatically make a phone long-lasting. Battery life is the result of several components working together.\n\nBattery capacity\nCapacity is normally listed in mAh. A larger number can provide more reserve, but it should be considered alongside screen size, brightness and processor efficiency.\n\nDisplay power\nLarge bright screens and high refresh rates can consume more energy. Adaptive refresh rates can help by reducing the refresh rate when a high rate is unnecessary.\n\nProcessor efficiency\nModern chipsets can deliver more performance per watt than older designs. This matters during video playback, navigation, mobile data use and demanding games.\n\nNetwork conditions\nWeak cellular signals can increase power consumption because the phone works harder to maintain communication. Battery results therefore vary between users and locations.\n\nCharging\nFast charging is valuable if you often need a quick top-up. Check the charging standard, supported wattage and whether the required charger is included. Battery-health features can also matter if you plan to keep the phone for several years.\n\nWhat to compare\nUse battery capacity as a starting point, then look for independent endurance testing and reviews. A phone with slightly less capacity can last longer if its display and processor are significantly more efficient.",
    },
    {
        "title": "5G Phone Buying Guide: Check These Things Before You Buy",
        "slug": "5g-phone-buying-guide",
        "excerpt": "A 5G label is not enough. Check the exact model, supported bands, SIM configuration and regional compatibility before buying.",
        "category": "Connectivity",
        "content": "A phone can support 5G and still be a poor match for a particular carrier or region. Imported devices are especially worth checking carefully.\n\nExact model number\nManufacturers can sell different regional variants under the same product family name. The exact model number is more reliable than a generic product name when checking compatibility.\n\n5G and LTE bands\nCompare the phone's supported bands with those used by your carrier. LTE compatibility also matters because phones do not operate on 5G all the time.\n\nSIM and eSIM\nCheck whether the version you are buying supports the SIM arrangement you need. eSIM availability can vary by market and carrier even when the hardware family is the same.\n\nWi-Fi and Bluetooth\nNewer connectivity standards can improve speed and reliability, but compatibility with your router, headphones, car system and other accessories is also important.\n\nBuying from another market\nImported phones may have different firmware, warranty coverage, network support or regional features. Verify these details before paying, especially when a foreign listing looks unusually inexpensive.",
    },
    {
        "title": "Flagship vs Mid-Range Phones: Which Should You Buy?",
        "slug": "flagship-vs-mid-range-phones",
        "excerpt": "Flagships offer premium hardware, while mid-range phones can deliver better value for everyday use. Compare the features you will actually use.",
        "category": "Comparisons",
        "content": "The most expensive phone is not automatically the best phone for every buyer. Flagships and mid-range devices make different trade-offs.\n\nWhere flagships usually lead\nPremium models often offer faster processors, more advanced camera systems, brighter displays, stronger materials and newer connectivity. Some also receive longer software support.\n\nWhere mid-range phones can win\nA good mid-range phone can provide an excellent display, capable cameras, strong battery life and smooth everyday performance at a much lower price. For browsing, messaging, streaming and casual gaming, expensive flagship hardware may not provide a noticeable benefit.\n\nCamera differences\nFlagships commonly invest more in stabilization, telephoto cameras, sensors and image processing. If photography is a priority, these upgrades can justify the extra cost.\n\nPerformance differences\nFor demanding games and creative work, a flagship processor can provide more headroom. For normal apps, the difference may be less important than software stability and battery efficiency.\n\nMake the decision by usage\nList the three things you care about most. If none requires flagship hardware, a strong mid-range phone may be the better value. If you need advanced cameras, sustained gaming performance or premium build quality, the flagship premium can make more sense.",
    },
    {
        "title": "Phone Camera Buying Guide: Look Beyond Megapixels",
        "slug": "phone-camera-buying-guide",
        "excerpt": "Learn how sensor size, stabilization, lenses, zoom, autofocus and video features affect smartphone camera performance.",
        "category": "Cameras",
        "content": "Megapixels describe image resolution, not overall camera quality. A good smartphone camera combines hardware and software to produce consistent photos and video.\n\nMain sensor\nThe main camera is usually the most important. Sensor size, lens quality, aperture, autofocus and stabilization affect low-light performance, motion and detail.\n\nOptical stabilization\nOIS can reduce camera shake and help produce sharper photos in lower light. It can also make handheld video easier to stabilize, although electronic stabilization and processing contribute too.\n\nTelephoto and ultrawide cameras\nA telephoto camera is useful for distant subjects and portraits. An ultrawide camera is useful for landscapes, architecture and group shots. Check the quality of these secondary cameras rather than assuming that having more cameras automatically means better results.\n\nVideo\nFor video, check stabilization, autofocus, frame rates, resolution and whether quality remains consistent when switching between cameras. Storage and microphone quality also matter for frequent recording.\n\nImage processing\nComputational photography can dramatically affect exposure, color, HDR and night images. Two phones with similar hardware can therefore produce different results. When possible, compare real-world samples from independent reviews.",
    },
    {
        "title": "Phone Buying Mistakes That Are Easy to Avoid",
        "slug": "common-phone-buying-mistakes",
        "excerpt": "Avoid common smartphone shopping mistakes such as chasing specifications, ignoring regional variants and forgetting long-term costs.",
        "category": "Buying Advice",
        "content": "Smartphone shopping becomes harder when specifications are treated as a scoreboard. A few simple checks can prevent expensive mistakes.\n\nMistake 1: buying by megapixels or RAM alone\nA large number does not guarantee a better experience. Camera sensors, processing, lenses and software matter, while RAM works together with the processor and operating system.\n\nMistake 2: ignoring the exact model\nRegional variants can have different network bands, SIM options, storage configurations and warranties. Always verify the exact model number.\n\nMistake 3: forgetting storage growth\nA phone that has enough space today may become restrictive after years of photos, videos and games. Estimate future storage needs before choosing the cheapest configuration.\n\nMistake 4: ignoring software support\nA phone is a long-term purchase. Check how long security and operating-system updates are expected to continue.\n\nMistake 5: comparing only launch price\nConsider warranty, accessories, repair options and the actual local price. A lower initial price is not always the lower total cost.\n\nMistake 6: trusting every specification page\nSpecifications can contain regional differences or errors. For important decisions, compare manufacturer information with reputable independent reviews and verify the exact configuration sold by the retailer.",
    },
    {
        "title": "How to Compare Phones Without Getting Lost in Specifications",
        "slug": "how-to-compare-phones-effectively",
        "excerpt": "A simple comparison framework for evaluating phones by display, performance, cameras, battery, software and value.",
        "category": "Comparisons",
        "content": "A phone comparison is useful when it answers a buying question, not when it produces the longest specification table. Use a consistent framework for every model.\n\nStart with the same budget\nComparing phones at very different prices can make the more expensive device look better simply because it has a larger hardware budget. Start with models that are realistic alternatives for the same buyer.\n\nCompare the display\nCheck panel type, size, resolution, refresh rate and brightness. Decide which of these matters most for your usage.\n\nCompare performance\nLook at the chipset, storage technology, RAM and thermal behavior. For gaming, sustained performance is more useful than a short benchmark peak.\n\nCompare cameras\nCompare the main sensor, stabilization, zoom, ultrawide quality and video features. Do not count cameras; evaluate what each camera can actually do.\n\nCompare battery and support\nLook at capacity, charging and independent endurance tests. Then check software support and warranty because these affect long-term value.\n\nFinish with trade-offs\nThe best comparison does not need a single winner. Explain which phone is better for gaming, photography, battery life, portability or value so the reader can choose according to their priorities.",
    },
    {
        "title": "Phone Storage, Cloud Backup and Photo Management Tips",
        "slug": "phone-storage-and-photo-management-tips",
        "excerpt": "Keep your phone storage manageable with practical habits for photos, videos, downloads, apps and backups.",
        "category": "Phone Tips",
        "content": "Storage problems often appear gradually. Photos, videos, downloads and large apps can turn a comfortable phone into a nearly full device.\n\nReview the biggest categories\nStart with the phone's storage settings and identify what consumes the most space. Large videos and downloaded media are often bigger contributors than individual apps.\n\nClean downloads safely\nRemove old files that you no longer need, but check important documents before deleting them. Messaging apps may also keep duplicate media files.\n\nUse photo backups carefully\nA reputable cloud backup can protect important photos, but backup is not the same as an archive you can delete without checking. Confirm that files are actually backed up before removing local copies.\n\nKeep enough free space\nVery full storage can make everyday management harder and can leave little room for system updates or new recordings. Leaving a reasonable amount of free space makes the phone easier to use.\n\nPlan before buying\nIf you record lots of 4K video, install large games or keep files offline, choose a higher storage configuration from the start. A larger internal drive can be more convenient than constantly managing space.",
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    for article in ARTICLES:
        exists = bind.execute(
            text("SELECT id FROM blog_articles WHERE slug=:slug LIMIT 1"),
            {"slug": article["slug"]},
        ).scalar_one_or_none()
        if exists is not None:
            continue
        bind.execute(
            text("""INSERT INTO blog_articles
                (title,slug,excerpt,content,category,featured_image_url,seo_description,status,created_at,updated_at,published_at)
                VALUES (:title,:slug,:excerpt,:content,:category,NULL,:seo_description,'published',:now,:now,:now)"""),
            {
                **article,
                "seo_description": article["excerpt"],
                "now": now,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    slugs = [article["slug"] for article in ARTICLES]
    bind.execute(text("DELETE FROM blog_articles WHERE slug IN :slugs"), {"slugs": tuple(slugs)})

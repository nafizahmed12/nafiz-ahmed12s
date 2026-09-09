"""Editorial SEO context for phone brand landing pages."""

BRAND_SEO = {
    "Apple": ("Explore Apple iPhone models with specifications, release information, pricing context and comparison-friendly details. Use the catalog to compare generations and choose the model that fits your needs.", "Apple phone pages focus on published model specifications and practical comparisons rather than simply repeating marketing claims."),
    "Samsung": ("Browse Samsung Galaxy phones across flagship, foldable and mid-range families. Compare core specifications, release information and related models in one catalog.", "Samsung models can differ by region, chipset and network configuration, so check the exact model and source information before buying."),
    "Google": ("Explore Google Pixel phones with key specifications, release information and related comparisons. Evaluate cameras, performance, battery and software-focused devices.", "Pixel availability and specifications can vary by market, so regional model details should be checked before purchase."),
    "OnePlus": ("Compare OnePlus smartphones by performance, display, camera hardware, battery and pricing context. Find related OnePlus models and cross-brand alternatives.", "OnePlus specifications and network support may vary between regional versions, especially for imported phones."),
    "Xiaomi": ("Browse Xiaomi phones and related Redmi and POCO models in a searchable catalog. Compare performance, cameras, displays, battery and other core features.", "Xiaomi family names can cover different regional variants, so verify the exact model number and supported network bands."),
}


def brand_seo_context(brand):
    intro, faq = BRAND_SEO.get(brand, (
        f"Browse published {brand} smartphones with specifications, release information, pricing context and useful comparisons. Explore individual models and discover related phones across the wider catalog.",
        "Phone specifications, prices and network compatibility can vary by market and configuration. Check the cited source and exact regional model before making a purchase decision.",
    ))
    return {"intro": intro, "faq": faq}

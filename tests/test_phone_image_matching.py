"""Regression tests for strict Wikimedia Commons phone-model matching."""

from scripts.fetch_real_phone_images import _is_exact_commons_title_match


def test_accepts_exact_iphone_variant():
    assert _is_exact_commons_title_match(
        "Apple", "iPhone 15 Pro Max", "File:Cosmic Orange iPhone 15 Pro Max.jpg"
    )


def test_rejects_sibling_iphone_variant():
    assert not _is_exact_commons_title_match(
        "Apple", "iPhone 15 Pro", "File:Apple iPhone 15 Pro Max.jpg"
    )


def test_rejects_wrong_motorola_model_number():
    assert not _is_exact_commons_title_match(
        "Motorola", "Edge 50 Pro", "File:Motorola Edge 60 Pro.jpg"
    )


def test_rejects_samsung_ultra_for_base_model():
    assert not _is_exact_commons_title_match(
        "Samsung", "Galaxy S24", "File:Samsung Galaxy S24 Ultra.jpg"
    )


def test_rejects_family_or_series_image():
    assert not _is_exact_commons_title_match(
        "Samsung", "Galaxy S24", "File:Samsung Galaxy S24 series.jpg"
    )


def test_rejects_partial_model_token():
    assert not _is_exact_commons_title_match(
        "Samsung", "Galaxy S24", "File:Samsung Galaxy S240 case.jpg"
    )


def test_accepts_exact_oneplus_model_with_split_brand_spelling():
    assert _is_exact_commons_title_match(
        "OnePlus", "13", "File:One Plus 13 smartphone.jpg"
    )

from django.db import migrations


INITIAL_PROPERTY_TYPES = [
    (
        "House and Lot",
        "house-and-lot",
        [
            "bedrooms",
            "bathrooms",
            "parking_spaces",
            "floor_area_sqm",
            "lot_area_sqm",
            "furnishing",
        ],
    ),
    (
        "House",
        "house",
        ["bedrooms", "bathrooms", "parking_spaces", "floor_area_sqm", "furnishing"],
    ),
    (
        "Condominium",
        "condominium",
        ["bedrooms", "bathrooms", "parking_spaces", "floor_area_sqm", "furnishing"],
    ),
    ("Vacant Lot", "vacant-lot", ["lot_area_sqm"]),
    (
        "Townhouse",
        "townhouse",
        [
            "bedrooms",
            "bathrooms",
            "parking_spaces",
            "floor_area_sqm",
            "lot_area_sqm",
            "furnishing",
        ],
    ),
    (
        "Apartment",
        "apartment",
        ["bedrooms", "bathrooms", "parking_spaces", "floor_area_sqm", "furnishing"],
    ),
    ("Commercial", "commercial", ["parking_spaces", "floor_area_sqm", "lot_area_sqm"]),
    ("Office", "office", ["parking_spaces", "floor_area_sqm"]),
    ("Warehouse", "warehouse", ["parking_spaces", "floor_area_sqm", "lot_area_sqm"]),
    ("Agricultural Land", "agricultural-land", ["lot_area_sqm"]),
    ("Memorial Lot", "memorial-lot", ["lot_area_sqm", "memorial_capacity"]),
    ("Memorial Estate", "memorial-estate", ["lot_area_sqm", "memorial_capacity"]),
    ("Other", "other", []),
]


def seed_property_types(apps, schema_editor):
    property_type = apps.get_model("properties", "PropertyType")
    for sort_order, (name, slug, applicable_fields) in enumerate(INITIAL_PROPERTY_TYPES):
        property_type.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "applicable_fields": applicable_fields,
                "sort_order": sort_order,
                "active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("properties", "0001_initial")]

    operations = [migrations.RunPython(seed_property_types, migrations.RunPython.noop)]

from django.db import migrations


def normalize_locations(apps, schema_editor):
    Location = apps.get_model("properties", "Location")
    city_names = {
        "Bacolod": "City of Bacolod",
        "Bacolod City": "City of Bacolod",
        "Silay City": "City of Silay",
        "Talisay City": "City of Talisay",
    }
    for location in Location.objects.filter(province="Negros Occidental"):
        location.region = "Negros Island Region (NIR)"
        location.city_municipality = city_names.get(
            location.city_municipality, location.city_municipality
        )
        if location.city_municipality == "City of Bacolod":
            location.province = ""
        location.save(update_fields=["region", "province", "city_municipality"])


class Migration(migrations.Migration):
    dependencies = [("properties", "0003_location_properties_location_private_coordinates_pair_and_more")]
    operations = [migrations.RunPython(normalize_locations, migrations.RunPython.noop)]

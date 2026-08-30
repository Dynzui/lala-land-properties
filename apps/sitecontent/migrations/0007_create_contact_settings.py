from django.db import migrations


def create_contact_settings(apps, schema_editor):
    SiteContactSettings = apps.get_model("sitecontent", "SiteContactSettings")
    SiteContactSettings.objects.get_or_create(pk=1)


def remove_contact_settings(apps, schema_editor):
    SiteContactSettings = apps.get_model("sitecontent", "SiteContactSettings")
    SiteContactSettings.objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0006_sitecontactsettings")]

    operations = [migrations.RunPython(create_contact_settings, remove_contact_settings)]

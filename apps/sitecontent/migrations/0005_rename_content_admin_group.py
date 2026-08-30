from django.db import migrations


OLD_NAME = "Lala Land Article Admins"
NEW_NAME = "Lala Land Content Admins"


def rename_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    old_group = Group.objects.filter(name=OLD_NAME).first()
    if old_group is not None and not Group.objects.filter(name=NEW_NAME).exists():
        old_group.name = NEW_NAME
        old_group.save(update_fields=["name"])


def restore_group_name(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    new_group = Group.objects.filter(name=NEW_NAME).first()
    if new_group is not None and not Group.objects.filter(name=OLD_NAME).exists():
        new_group.name = OLD_NAME
        new_group.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0004_create_about_page")]

    operations = [migrations.RunPython(rename_group, restore_group_name)]

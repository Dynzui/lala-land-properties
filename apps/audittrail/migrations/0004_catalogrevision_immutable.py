from django.db import migrations


def add_revision_immutability_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        CREATE TRIGGER catalog_revision_no_update
        BEFORE UPDATE ON audittrail_catalogrevision
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_mutation();
        """
    )
    schema_editor.execute(
        """
        CREATE TRIGGER catalog_revision_no_delete
        BEFORE DELETE ON audittrail_catalogrevision
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_mutation();
        """
    )


def remove_revision_immutability_triggers(apps, schema_editor):
    schema_editor.execute("DROP TRIGGER IF EXISTS catalog_revision_no_update")
    schema_editor.execute("DROP TRIGGER IF EXISTS catalog_revision_no_delete")


class Migration(migrations.Migration):
    dependencies = [("audittrail", "0003_catalogrevision")]

    operations = [
        migrations.RunPython(
            add_revision_immutability_triggers,
            remove_revision_immutability_triggers,
        )
    ]

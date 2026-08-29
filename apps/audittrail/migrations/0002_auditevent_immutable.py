from django.db import migrations


def add_immutability_triggers(apps, schema_editor):
    table = "audittrail_auditevent"
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_audit_event_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'Audit events are immutable';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        schema_editor.execute(
            f"""
            CREATE TRIGGER audit_event_no_update
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_mutation();
            """
        )
        schema_editor.execute(
            f"""
            CREATE TRIGGER audit_event_no_delete
            BEFORE DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_mutation();
            """
        )
def remove_immutability_triggers(apps, schema_editor):
    schema_editor.execute("DROP TRIGGER IF EXISTS audit_event_no_update")
    schema_editor.execute("DROP TRIGGER IF EXISTS audit_event_no_delete")
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP FUNCTION IF EXISTS prevent_audit_event_mutation()")


class Migration(migrations.Migration):
    dependencies = [("audittrail", "0001_initial")]

    operations = [migrations.RunPython(add_immutability_triggers, remove_immutability_triggers)]

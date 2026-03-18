from django.db import migrations


def ensure_feedback_email_sent_column(apps, schema_editor):
    table_name = "fergusonbequest_booking"
    column_name = "feedback_email_sent"

    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(cursor, table_name)
        existing_columns = {col.name for col in description}

    if column_name not in existing_columns:
        schema_editor.execute(
            "ALTER TABLE fergusonbequest_booking "
            "ADD COLUMN feedback_email_sent bool NOT NULL DEFAULT 0"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("fergusonbequest", "0026_alter_emailtemplate_type"),
    ]

    operations = [
        migrations.RunPython(ensure_feedback_email_sent_column, migrations.RunPython.noop),
    ]

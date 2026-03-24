from django.db import migrations


def repair_converted_booking_column(apps, schema_editor):
    table_name = "fergusonbequest_ticketdrawbooking"
    column_name = "converted_booking_id"

    existing_tables = set(schema_editor.connection.introspection.table_names())
    if table_name not in existing_tables:
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = {row[1] for row in cursor.fetchall()}

        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} bigint NULL"
            )

        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "fergusonbequest_ticketdrawbooking_converted_booking_id_key "
            f"ON {table_name} ({column_name})"
        )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("fergusonbequest", "0031_booking_feedback_email_sent_at_and_more"),
    ]

    operations = [
        migrations.RunPython(repair_converted_booking_column, noop_reverse),
    ]

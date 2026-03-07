from django.db import migrations


def repair_attraction_waitlist_schema(apps, schema_editor):
    AttractionWaitlistEntry = apps.get_model("fergusonbequest", "AttractionWaitlistEntry")
    table = AttractionWaitlistEntry._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info('{table}')")
        existing_columns = {row[1] for row in cursor.fetchall()}

    if "cancelled" not in existing_columns:
        schema_editor.add_field(
            AttractionWaitlistEntry,
            AttractionWaitlistEntry._meta.get_field("cancelled"),
        )

    if "notified" not in existing_columns:
        schema_editor.add_field(
            AttractionWaitlistEntry,
            AttractionWaitlistEntry._meta.get_field("notified"),
        )

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"PRAGMA index_list('{table}')")
        indexes = cursor.fetchall()

        for _, index_name, is_unique, *_ in indexes:
            if not is_unique:
                continue

            cursor.execute(f"PRAGMA index_info('{index_name}')")
            index_columns = [row[2] for row in cursor.fetchall()]

            if index_columns == ["user_id", "attraction_id"] and index_name != "unique_active_attraction_waitlist":
                cursor.execute(f'DROP INDEX IF EXISTS "{index_name}"')

        qn = schema_editor.quote_name
        cursor.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {qn('unique_active_attraction_waitlist')} "
            f"ON {qn(table)} ({qn('user_id')}, {qn('attraction_id')}) "
            f"WHERE {qn('cancelled')} = 0"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("fergusonbequest", "0020_attractionwaitlistentry"),
    ]

    operations = [
        migrations.RunPython(repair_attraction_waitlist_schema, migrations.RunPython.noop),
    ]

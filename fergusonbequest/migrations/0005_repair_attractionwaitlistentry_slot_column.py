from django.db import migrations

def ensure_waitlist_slot_column(apps, schema_editor):
    table_name = "fergusonbequest_attractionwaitlistentry"
    column_name = "slot_id"
    
    with schema_editor.connection.cursor() as cursor:
        existing_tables = set(schema_editor.connection.introspection.table_names(cursor))
    
    if table_name not in existing_tables:
        return 
    
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(cursor, table_name)
        existing_columns = {col.name for col in description}
        
    if column_name in existing_columns:
        return
    
    schema_editor.execute(
        "ALTER TABLE fergusonbequest_attractionwaitlistentry "
        "ADD COLUMN slot_id bigint NULL"
    )

class Migration(migrations.Migration):

    dependencies = [
        ("fergusonbequest", "0004_bookingticket_ticket_code"),
    ]

    operations = [
        migrations.RunPython(ensure_waitlist_slot_column, migrations.RunPython.noop),
    ]

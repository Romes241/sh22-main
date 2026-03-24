from django.db import migrations


def repair_bookingticket_table(apps, schema_editor):
    BookingTicket = apps.get_model("fergusonbequest", "BookingTicket")
    table_name = BookingTicket._meta.db_table

    existing_tables = set(schema_editor.connection.introspection.table_names())
    if table_name not in existing_tables:
        schema_editor.create_model(BookingTicket)


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("fergusonbequest", "0032_repair_ticketdrawbooking_converted_booking_column"),
    ]

    operations = [
        migrations.RunPython(repair_bookingticket_table, noop_reverse),
    ]

from django.db import migrations

def seed_feedback_email_defaults(apps, schema_editor):
    EmailTemplate = apps.get_model("fergusonbequest", "EmailTemplate")
    FeedbackEmailTemplate = apps.get_model("fergusonbequest", "FeedbackEmailTemplate")
    
    feedback_singleton, _ = FeedbackEmailTemplate.objects.get_or_create(pk=1)
    feedback_templates = EmailTemplate.objects.filter(type="feedback").order_by("id")
    
    if not feedback_templates.exists():
        EmailTemplate.objects.create(
        type="feedback",
        name="Feedback Template",
        subject=feedback_singleton.subject,
        body=feedback_singleton.body,
        is_default=True
        )
        return
    
    if not feedback_templates.filter(is_default=True).exists():
        first_template = feedback_templates.first()
        first_template.is_default = True
        first_template.save(update_fields=["is_default"])


def keep_previous_data(apps, schema_editor):
    # Keep existing data on reverse migrations.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("fergusonbequest", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_feedback_email_defaults, keep_previous_data),
    ]

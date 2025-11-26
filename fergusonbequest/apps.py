from django.apps import AppConfig


class FergusonbequestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fergusonbequest"

    def ready(self):
        import fergusonbequest.signals
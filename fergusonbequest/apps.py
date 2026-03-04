from django.apps import AppConfig
import os
import sys

class FergusonbequestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fergusonbequest"

    def ready(self):
        import fergusonbequest.signals  # noqa

        if "runserver" in sys.argv:
            from .scheduler import start_scheduler
            
            if os.environ.get('RUN_MAIN') or not os.environ.get('DJANGO_AUTORELOAD'):
                start_scheduler()

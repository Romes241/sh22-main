from django.core.management.base import BaseCommand
from fergusonbequest.scheduler import start_scheduler
import time


class Command(BaseCommand):
    help = "Run the APScheduler background scheduler for Ferguson Bequest."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Ferguson Bequest scheduler..."))
        start_scheduler()

        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Scheduler stopped."))
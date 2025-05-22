from django.core.management.base import BaseCommand
import main.vrr


class Command(BaseCommand):
    help = "Update VRR tickets"

    def handle(self, *args, **options):
        main.vrr.update_all.delay()

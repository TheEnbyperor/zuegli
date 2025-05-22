from django.core.management.base import BaseCommand
import main.raileasy


class Command(BaseCommand):
    help = "Update Raileasy tickets"

    def handle(self, *args, **options):
        main.raileasy.update_all.delay()

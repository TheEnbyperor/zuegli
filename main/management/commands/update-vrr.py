import logging
from django.core.management.base import BaseCommand
import main.vrr


class Command(BaseCommand):
    help = "Update VRR tickets"

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO)
        main.vrr.update_all()

import logging
from django.core.management.base import BaseCommand
import main.avv


class Command(BaseCommand):
    help = "Update AVV tickets"

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO)
        main.avv.update_all()

import logging
from django.core.management.base import BaseCommand
import main.saarvv


class Command(BaseCommand):
    help = "Update SaarVV tickets"

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO)
        main.saarvv.update_all()

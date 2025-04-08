import logging
from django.core.management.base import BaseCommand
import main.db_bc


class Command(BaseCommand):
    help = "Update DB BahnCards"

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO)
        main.db_bc.update_all()

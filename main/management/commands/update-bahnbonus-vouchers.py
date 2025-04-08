import logging
from django.core.management.base import BaseCommand
import main.bahnbonus_vouchers


class Command(BaseCommand):
    help = "Update BahnBonus vouchers"

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO)
        main.bahnbonus_vouchers.update_all()

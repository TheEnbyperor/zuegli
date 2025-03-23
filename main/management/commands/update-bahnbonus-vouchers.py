from django.core.management.base import BaseCommand
import main.bahnbonus_vouchers


class Command(BaseCommand):
    help = "Update BahnBonus vouchers"

    def handle(self, *args, **options):
        main.bahnbonus_vouchers.update_all()

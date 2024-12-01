from django.core.management.base import BaseCommand
import main.db_ticket


class Command(BaseCommand):
    help = "Update DB tickets"

    def handle(self, *args, **options):
        main.db_ticket.update_all()

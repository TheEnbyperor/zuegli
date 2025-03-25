from django.core.management.base import BaseCommand
import main.sbahn_berlin


class Command(BaseCommand):
    help = "Update S-Bahn Berlin tickets"

    def handle(self, *args, **options):
        main.sbahn_berlin.update_all()

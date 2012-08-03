from django.core.management.base import BaseCommand
from logistics_project.apps.malawi import loader

class Command(BaseCommand):
    help = "Initialize static data for malawi"

    def handle(self, *args, **options):
        loader.init_static_data(log_to_console=True)
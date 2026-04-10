from django.core.management.base import BaseCommand, CommandError

from datamining.services import sync_batches_from_pigmldata_csv


class Command(BaseCommand):
    help = 'Sync batch summaries from the latest PigMLData CSV row per batch_code.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            default='datamining/generated/synthetic_pigmldata.csv',
            help='Path to the PigMLData CSV file to sync from.',
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']

        try:
            counts = sync_batches_from_pigmldata_csv(csv_path=csv_path)
        except (FileNotFoundError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                (
                    'Processed {processed} batches: updated {updated}, skipped {skipped}, '
                    'already synced {already_synced}, missing batches {missing_batches}, '
                    'missing growth stages {missing_growth_stages}.'
                ).format(**counts)
            )
        )

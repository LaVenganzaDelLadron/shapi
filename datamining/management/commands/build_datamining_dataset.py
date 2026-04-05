from django.core.management.base import BaseCommand, CommandError

from datamining.services import build_pig_ml_dataset


class Command(BaseCommand):
    help = 'Builds the denormalized pig ML dataset from record, feeding, pen, growth, and device data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--window-days',
            type=int,
            default=1,
            help='Number of days before each record date to include feeding events.',
        )
        parser.add_argument(
            '--refresh-snapshots',
            action='store_true',
            help='Recompute snapshot fields such as pen metadata for existing dataset rows.',
        )

    def handle(self, *args, **options):
        window_days = options['window_days']
        if window_days <= 0:
            raise CommandError('--window-days must be greater than zero.')

        counts = build_pig_ml_dataset(
            window_days=window_days,
            refresh_snapshots=options['refresh_snapshots'],
        )
        self.stdout.write(
            self.style.SUCCESS(
                'Processed {processed} records: created {created}, updated {updated}.'.format(**counts)
            )
        )

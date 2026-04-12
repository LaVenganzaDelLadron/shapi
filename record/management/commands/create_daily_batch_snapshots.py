from django.core.management.base import BaseCommand

from record.services import create_daily_snapshot_records


class Command(BaseCommand):
    help = 'Create one immutable daily snapshot record per active batch using UTC day boundaries.'

    def handle(self, *args, **options):
        counts = create_daily_snapshot_records()
        self.stdout.write(
            self.style.SUCCESS(
                'Processed {processed} active batches: created {created}, skipped {skipped} for UTC day {snapshot_day}.'.format(
                    **counts
                )
            )
        )

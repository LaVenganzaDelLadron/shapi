from django.db.models import IntegerField, Sum, Value
from django.db.models.functions import Coalesce

from pen.models import Pen


def sync_pen_statuses(pen_codes=None):
    pens = Pen.objects.all()
    if pen_codes is not None:
        pen_codes = set(pen_codes)
        if not pen_codes:
            return 0
        pens = pens.filter(pen_code__in=pen_codes)

    pens = pens.annotate(
        total_pigs=Coalesce(
            Sum('batches__no_of_pigs'),
            Value(0),
            output_field=IntegerField(),
        )
    )

    pens_to_update = []
    for pen in pens:
        next_status = 'occupied' if pen.total_pigs >= pen.capacity else 'available'
        if pen.status != next_status:
            pen.status = next_status
            pens_to_update.append(pen)

    if pens_to_update:
        Pen.objects.bulk_update(pens_to_update, ['status'])

    return len(pens_to_update)

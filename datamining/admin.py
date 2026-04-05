from django.contrib import admin

from datamining.models import PigMLData


@admin.register(PigMLData)
class PigMLDataAdmin(admin.ModelAdmin):
    list_display = (
        'record_code',
        'batch_code',
        'pen_code',
        'sample_date',
        'avg_weight',
        'feeding_count',
        'window_days',
    )
    search_fields = ('record_code', 'batch_code', 'pen_code', 'growth_stage')
    list_filter = ('pen_status', 'growth_stage', 'window_days')

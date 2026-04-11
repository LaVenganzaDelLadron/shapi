import hashlib
import json
from collections import defaultdict
from datetime import datetime, time, timedelta

from django.core.cache import cache
from django.db.models import Avg, Count, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce, TruncDay, TruncWeek
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from batch.models import PigBatches
from dashboard.serializers import (
    FeedConsumptionQuerySerializer,
    FeedDispensedTodayQuerySerializer,
    GrowthTrendsQuerySerializer,
    NextFeedingScheduleQuerySerializer,
)
from datamining.models import PigMLData
from feeding.models import Feeding
from record.models import Record


WEEKDAY_ALIASES = {
    'mon': 0,
    'monday': 0,
    'tue': 1,
    'tues': 1,
    'tuesday': 1,
    'wed': 2,
    'wednesday': 2,
    'thu': 3,
    'thur': 3,
    'thurs': 3,
    'thursday': 3,
    'fri': 4,
    'friday': 4,
    'sat': 5,
    'saturday': 5,
    'sun': 6,
    'sunday': 6,
}


class DashboardBaseView(APIView):
    cache_timeout = 30

    def success_response(self, results, http_status=status.HTTP_200_OK):
        return Response({'status': 'success', 'results': results}, status=http_status)

    def error_response(self, message, http_status=status.HTTP_400_BAD_REQUEST):
        return Response({'status': 'error', 'message': message}, status=http_status)

    def validate_query(self, serializer_class, request):
        serializer = serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def build_cache_key(self, request, suffix):
        raw_params = dict(sorted(request.query_params.items()))
        encoded = json.dumps(raw_params, sort_keys=True)
        digest = hashlib.md5(encoded.encode('utf-8')).hexdigest()
        return f'dashboard:{suffix}:{digest}'

    def cached_payload(self, request, suffix, builder):
        cache_key = self.build_cache_key(request, suffix)
        cached = cache.get(cache_key)
        if cached is not None:
            return self.success_response(cached)

        payload = builder()
        cache.set(cache_key, payload, self.cache_timeout)
        return self.success_response(payload)


def _date_bounds(start_date=None, end_date=None):
    current_tz = timezone.get_current_timezone()
    range_start = None
    range_end = None

    if start_date:
        range_start = timezone.make_aware(datetime.combine(start_date, time.min), current_tz)
    if end_date:
        range_end = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min), current_tz)

    return range_start, range_end


def _apply_datetime_filters(queryset, field_name, start_date=None, end_date=None):
    range_start, range_end = _date_bounds(start_date=start_date, end_date=end_date)
    if range_start:
        queryset = queryset.filter(**{f'{field_name}__gte': range_start})
    if range_end:
        queryset = queryset.filter(**{f'{field_name}__lt': range_end})
    return queryset


def _parse_repeat_days(repeat_days):
    value = str(repeat_days or '').strip().lower()
    if not value or value in {'everyday', 'every day', 'daily', 'all'}:
        return None

    normalized = value.replace('/', ',').replace('|', ',')
    tokens = [token.strip() for token in normalized.split(',') if token.strip()]
    allowed_days = {WEEKDAY_ALIASES[token] for token in tokens if token in WEEKDAY_ALIASES}
    return allowed_days or None


def _adjust_to_repeat_schedule(candidate_time, repeat_days):
    allowed_days = _parse_repeat_days(repeat_days)
    if not allowed_days:
        return candidate_time

    adjusted = candidate_time
    for _ in range(7):
        if adjusted.weekday() in allowed_days:
            return adjusted
        adjusted += timedelta(days=1)
    return candidate_time


class DashboardGrowthTrendsView(DashboardBaseView):
    def get(self, request):
        try:
            params = self.validate_query(GrowthTrendsQuerySerializer, request)
        except Exception as exc:
            return self.error_response(str(exc))

        def build_results():
            queryset = Record.objects.select_related('batch_code').order_by('batch_code__batch_code', 'date', 'record_code')

            batch_code = params.get('batch_code')
            if batch_code:
                queryset = queryset.filter(batch_code__batch_code=batch_code)
            queryset = _apply_datetime_filters(
                queryset,
                'date',
                start_date=params.get('start_date'),
                end_date=params.get('end_date'),
            )

            grouped = defaultdict(list)
            for row in queryset.values('batch_code__batch_code', 'date', 'avg_weight', 'pig_age_days'):
                grouped[row['batch_code__batch_code']].append(
                    {
                        'sample_date': row['date'].isoformat(),
                        'avg_weight': round(float(row['avg_weight']), 2),
                        'pig_age_days': int(row['pig_age_days']),
                    }
                )

            return [
                {
                    'batch_code': grouped_batch_code,
                    'series': series,
                }
                for grouped_batch_code, series in grouped.items()
            ]

        return self.cached_payload(request, 'growth-trends', build_results)


class DashboardFeedConsumptionView(DashboardBaseView):
    def get(self, request):
        try:
            params = self.validate_query(FeedConsumptionQuerySerializer, request)
        except Exception as exc:
            return self.error_response(str(exc))

        def build_results():
            queryset = Feeding.objects.select_related('batch_code')
            batch_code = params.get('batch_code')
            if batch_code:
                queryset = queryset.filter(batch_code__batch_code=batch_code)
            queryset = _apply_datetime_filters(
                queryset,
                'feed_time',
                start_date=params.get('start_date'),
                end_date=params.get('end_date'),
            )

            group_by = params.get('group_by', 'none')
            if group_by == 'none':
                aggregated = (
                    queryset.values('batch_code__batch_code')
                    .annotate(total_feed_quantity=Coalesce(Sum('feed_quantity'), Value(0.0)))
                    .order_by('batch_code__batch_code')
                )
                return [
                    {
                        'batch_code': row['batch_code__batch_code'],
                        'total_feed_quantity': round(float(row['total_feed_quantity']), 2),
                    }
                    for row in aggregated
                ]

            trunc_expression = TruncDay('feed_time') if group_by == 'day' else TruncWeek('feed_time')
            aggregated = (
                queryset.annotate(period=trunc_expression)
                .values('batch_code__batch_code', 'period')
                .annotate(total_feed_quantity=Coalesce(Sum('feed_quantity'), Value(0.0)))
                .order_by('batch_code__batch_code', 'period')
            )

            grouped = defaultdict(list)
            for row in aggregated:
                grouped[row['batch_code__batch_code']].append(
                    {
                        'period': row['period'].isoformat() if row['period'] else None,
                        'total_feed_quantity': round(float(row['total_feed_quantity']), 2),
                    }
                )

            return [
                {
                    'batch_code': grouped_batch_code,
                    'series': series,
                }
                for grouped_batch_code, series in grouped.items()
            ]

        return self.cached_payload(request, 'feed-consumption', build_results)


class DashboardNextFeedingScheduleView(DashboardBaseView):
    def get(self, request):
        try:
            params = self.validate_query(NextFeedingScheduleQuerySerializer, request)
        except Exception as exc:
            return self.error_response(str(exc))

        def build_results():
            latest_feeding = Feeding.objects.filter(batch_code=OuterRef('pk')).order_by('-feed_time', '-feed_code')
            latest_interval = PigMLData.objects.filter(batch_code=OuterRef('batch_code')).order_by(
                '-sample_date',
                '-record_code',
            )

            queryset = PigBatches.objects.annotate(
                last_feed_time=Subquery(latest_feeding.values('feed_time')[:1]),
                feed_type=Subquery(latest_feeding.values('feed_type')[:1]),
                device_code=Subquery(latest_feeding.values('device_code__device_code')[:1]),
                repeat_days=Subquery(latest_feeding.values('repeat_days')[:1]),
                avg_feeding_interval_hours=Subquery(latest_interval.values('avg_feeding_interval_hours')[:1]),
            ).filter(last_feed_time__isnull=False).order_by('batch_code')

            batch_code = params.get('batch_code')
            if batch_code:
                queryset = queryset.filter(batch_code=batch_code)

            results = []
            for row in queryset.values(
                'batch_code',
                'last_feed_time',
                'feed_type',
                'device_code',
                'repeat_days',
                'avg_feeding_interval_hours',
            ):
                next_feeding_time = None
                if row['avg_feeding_interval_hours'] is not None:
                    candidate = row['last_feed_time'] + timedelta(hours=float(row['avg_feeding_interval_hours']))
                    next_feeding_time = _adjust_to_repeat_schedule(candidate, row['repeat_days'])

                results.append(
                    {
                        'batch_code': row['batch_code'],
                        'last_feed_time': row['last_feed_time'].isoformat(),
                        'next_feeding_time': next_feeding_time.isoformat() if next_feeding_time else None,
                        'feed_type': row['feed_type'],
                        'device_code': row['device_code'],
                        'repeat_days': row['repeat_days'],
                    }
                )

            return results

        return self.cached_payload(request, 'next-feeding-schedule', build_results)


class DashboardFeedDispensedTodayView(DashboardBaseView):
    def get(self, request):
        try:
            params = self.validate_query(FeedDispensedTodayQuerySerializer, request)
        except Exception as exc:
            return self.error_response(str(exc))

        def build_results():
            today = timezone.localdate()
            range_start, range_end = _date_bounds(start_date=today, end_date=today)
            queryset = Feeding.objects.filter(feed_time__gte=range_start, feed_time__lt=range_end)

            batch_code = params.get('batch_code')
            if batch_code:
                queryset = queryset.filter(batch_code__batch_code=batch_code)

            if params.get('per_batch'):
                aggregated = (
                    queryset.values('batch_code__batch_code')
                    .annotate(total_feed_quantity=Coalesce(Sum('feed_quantity'), Value(0.0)))
                    .order_by('batch_code__batch_code')
                )
                return [
                    {
                        'batch_code': row['batch_code__batch_code'],
                        'total_feed_quantity': round(float(row['total_feed_quantity']), 2),
                    }
                    for row in aggregated
                ]

            total_feed_quantity = queryset.aggregate(
                total_feed_quantity=Coalesce(Sum('feed_quantity'), Value(0.0))
            )['total_feed_quantity']
            return {
                'date': today.isoformat(),
                'total_feed_quantity': round(float(total_feed_quantity), 2),
            }

        return self.cached_payload(request, 'feed-dispensed-today', build_results)


class DashboardOverviewView(DashboardBaseView):
    def get(self, request):
        def build_results():
            today = timezone.localdate()
            range_start, range_end = _date_bounds(start_date=today, end_date=today)

            batch_totals = PigBatches.objects.aggregate(
                total_pigs=Coalesce(Sum('no_of_pigs'), Value(0)),
                active_batches=Count('id', filter=Q(no_of_pigs__gt=0)),
            )
            feeding_totals = Feeding.objects.filter(
                feed_time__gte=range_start,
                feed_time__lt=range_end,
            ).aggregate(
                total_feed_today=Coalesce(Sum('feed_quantity'), Value(0.0)),
            )
            record_totals = Record.objects.filter(
                date__gte=range_start,
                date__lt=range_end,
            ).aggregate(
                avg_weight_today=Coalesce(Avg('avg_weight'), Value(0.0)),
            )

            return {
                'total_pigs': int(batch_totals['total_pigs'] or 0),
                'active_batches': int(batch_totals['active_batches'] or 0),
                'total_feed_today': round(float(feeding_totals['total_feed_today'] or 0.0), 2),
                'avg_weight_today': round(float(record_totals['avg_weight_today'] or 0.0), 2),
            }

        return self.cached_payload(request, 'overview', build_results)

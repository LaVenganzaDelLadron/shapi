import hashlib
import json

from django.core.cache import cache
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.serializers import (
    FeedConsumptionQuerySerializer,
    FeedDispensedTodayQuerySerializer,
    GrowthTrendsQuerySerializer,
    NextFeedingScheduleQuerySerializer,
    ReportPreviewQuerySerializer,
)
from dashboard.services import (
    get_dashboard_overview,
    get_feed_consumption,
    get_feed_dispensed_today,
    get_growth_trends,
    get_next_feeding_schedule,
    get_report_preview,
)


class DashboardBaseView(APIView):
    cache_timeout = 0

    def success_response(self, results, http_status=status.HTTP_200_OK):
        return Response({'status': 'success', 'results': results}, status=http_status)

    def error_response(self, message, http_status=status.HTTP_400_BAD_REQUEST):
        return Response({'status': 'error', 'message': message}, status=http_status)

    def validate_query(self, serializer_class, request):
        serializer = serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def build_cache_key(self, request, suffix):
        raw_payload = {
            'path': request.path,
            'params': dict(sorted(request.query_params.items())),
        }
        encoded = json.dumps(raw_payload, sort_keys=True)
        digest = hashlib.md5(encoded.encode('utf-8')).hexdigest()
        return f'dashboard:{suffix}:{digest}'

    def cached_payload(self, request, suffix, builder):
        if self.cache_timeout <= 0:
            return self.success_response(builder())

        cache_key = self.build_cache_key(request, suffix)
        cached = cache.get(cache_key)
        if cached is not None:
            return self.success_response(cached)

        payload = builder()
        cache.set(cache_key, payload, self.cache_timeout)
        return self.success_response(payload)


class DashboardQueryView(DashboardBaseView):
    serializer_class = None
    cache_suffix = ''

    def get_query_params(self, request):
        if self.serializer_class is None:
            return {}
        return self.validate_query(self.serializer_class, request)

    def build_results(self, params):
        raise NotImplementedError

    def get(self, request):
        try:
            params = self.get_query_params(request)
        except ValidationError as exc:
            return self.error_response(str(exc))

        return self.cached_payload(request, self.cache_suffix, lambda: self.build_results(params))


class DashboardGrowthTrendsView(DashboardQueryView):
    serializer_class = GrowthTrendsQuerySerializer
    cache_suffix = 'growth-trends'

    def build_results(self, params):
        return get_growth_trends(params)


class DashboardFeedConsumptionView(DashboardQueryView):
    serializer_class = FeedConsumptionQuerySerializer
    cache_suffix = 'feed-consumption'

    def build_results(self, params):
        return get_feed_consumption(params)


class DashboardNextFeedingScheduleView(DashboardQueryView):
    serializer_class = NextFeedingScheduleQuerySerializer
    cache_suffix = 'next-feeding-schedule'

    def build_results(self, params):
        return get_next_feeding_schedule(params)


class DashboardFeedDispensedTodayView(DashboardQueryView):
    serializer_class = FeedDispensedTodayQuerySerializer
    cache_suffix = 'feed-dispensed-today'

    def build_results(self, params):
        return get_feed_dispensed_today(params)


class DashboardOverviewView(DashboardQueryView):
    cache_suffix = 'overview'

    def build_results(self, params):
        return get_dashboard_overview()


class DashboardReportPreviewView(DashboardQueryView):
    serializer_class = ReportPreviewQuerySerializer
    cache_suffix = 'report-preview'

    def build_results(self, params):
        return get_report_preview(params)

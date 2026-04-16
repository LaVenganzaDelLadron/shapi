from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from reports.serializers import RecentActivityQuerySerializer, ReportsQuerySerializer
from reports.services import (
    build_recent_activity,
    build_report_packets,
    build_reports_summary,
    build_volume_trend,
)


class ReportsBaseView(APIView):
    def success_response(self, results, http_status=status.HTTP_200_OK):
        return Response({'status': 'success', 'results': results}, status=http_status)

    def error_response(self, message, http_status=status.HTTP_400_BAD_REQUEST):
        return Response({'status': 'error', 'message': message}, status=http_status)

    def validate_query(self, serializer_class, request):
        serializer = serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class ReportsSummaryView(ReportsBaseView):
    def get(self, request):
        try:
            params = self.validate_query(ReportsQuerySerializer, request)
        except ValidationError as exc:
            return self.error_response(str(exc))

        packets = build_report_packets(
            start_date=params.get('start_date'),
            end_date=params.get('end_date'),
            batch_code=params.get('batch_code'),
            limit=params.get('limit', 50),
        )
        return self.success_response(build_reports_summary(packets))


class ReportsPacketsView(ReportsBaseView):
    def get(self, request):
        try:
            params = self.validate_query(ReportsQuerySerializer, request)
        except ValidationError as exc:
            return self.error_response(str(exc))

        packets = build_report_packets(
            start_date=params.get('start_date'),
            end_date=params.get('end_date'),
            batch_code=params.get('batch_code'),
            limit=params.get('limit', 50),
        )
        return self.success_response(packets)


class ReportsPacketDetailView(ReportsBaseView):
    def get(self, request, report_id):
        try:
            params = self.validate_query(ReportsQuerySerializer, request)
        except ValidationError as exc:
            return self.error_response(str(exc))

        packets = build_report_packets(
            start_date=params.get('start_date'),
            end_date=params.get('end_date'),
            batch_code=params.get('batch_code'),
            limit=200,
        )
        packet = next((item for item in packets if item['report_id'] == report_id), None)
        if packet is None:
            return self.error_response(f'Report packet "{report_id}" not found', status.HTTP_404_NOT_FOUND)
        return self.success_response(packet)


class ReportsVolumeTrendView(ReportsBaseView):
    def get(self, request):
        try:
            params = self.validate_query(ReportsQuerySerializer, request)
        except ValidationError as exc:
            return self.error_response(str(exc))

        packets = build_report_packets(
            start_date=params.get('start_date'),
            end_date=params.get('end_date'),
            batch_code=params.get('batch_code'),
            limit=params.get('limit', 50),
        )
        return self.success_response(build_volume_trend(packets))


class ReportsRecentActivityView(ReportsBaseView):
    def get(self, request):
        try:
            params = self.validate_query(RecentActivityQuerySerializer, request)
        except ValidationError as exc:
            return self.error_response(str(exc))

        return self.success_response(build_recent_activity(limit=params.get('limit', 10)))

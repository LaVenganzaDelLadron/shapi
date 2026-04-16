from django.urls import path

from reports.views import (
    ReportsPacketDetailView,
    ReportsPacketsView,
    ReportsRecentActivityView,
    ReportsSummaryView,
    ReportsVolumeTrendView,
)


urlpatterns = [
    path('summary/', ReportsSummaryView.as_view(), name='reportsSummary'),
    path('packets/', ReportsPacketsView.as_view(), name='reportsPackets'),
    path('packets/<str:report_id>/', ReportsPacketDetailView.as_view(), name='reportsPacketDetail'),
    path('volume-trend/', ReportsVolumeTrendView.as_view(), name='reportsVolumeTrend'),
    path('recent-activity/', ReportsRecentActivityView.as_view(), name='reportsRecentActivity'),
]

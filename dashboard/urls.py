from django.urls import path

from dashboard.views import (
    DashboardFeedConsumptionView,
    DashboardFeedDispensedTodayView,
    DashboardGrowthTrendsView,
    DashboardNextFeedingScheduleView,
    DashboardOverviewView,
)


urlpatterns = [
    path('growth-trends/', DashboardGrowthTrendsView.as_view(), name='dashboardGrowthTrends'),
    path('feed-consumption/', DashboardFeedConsumptionView.as_view(), name='dashboardFeedConsumption'),
    path('next-feeding-schedule/', DashboardNextFeedingScheduleView.as_view(), name='dashboardNextFeedingSchedule'),
    path('feed-dispensed-today/', DashboardFeedDispensedTodayView.as_view(), name='dashboardFeedDispensedToday'),
    path('overview/', DashboardOverviewView.as_view(), name='dashboardOverview'),
]


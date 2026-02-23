from django.urls import path

from .controller.feeding_controller import (
    FeedingController,
    GetFeedingController,
    DeleteFeedingController,
    UpdateFeedingController,
)

urlpatterns = [
    path('add/', FeedingController.as_view(), name='addFeeding'),
    path('all/', GetFeedingController.as_view(), name='getAllFeedings'),
    path('delete/<str:feed_code>/', DeleteFeedingController.as_view(), name='deleteFeeding'),
    path('update/<str:feed_code>/', UpdateFeedingController.as_view(), name='updateFeeding'),
]

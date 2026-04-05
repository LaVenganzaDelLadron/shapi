from django.urls import path

from datamining.controller.datamining_controller import (
    GetPigMLDataController,
    GetSpecificPigMLDataController,
)

urlpatterns = [
    path('all/', GetPigMLDataController.as_view(), name='getAllPigMLData'),
    path('get/<str:record_code>/', GetSpecificPigMLDataController.as_view(), name='getPigMLData'),
]

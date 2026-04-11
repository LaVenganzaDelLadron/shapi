from django.urls import path

from datamining.controller.datamining_controller import (
    ClassifyRiskController,
    GetPigMLDataController,
    GetSpecificPigMLDataController,
    PredictWeightController,
    SuggestFeedingController,
)

urlpatterns = [
    path('all/', GetPigMLDataController.as_view(), name='getAllPigMLData'),
    path('get/<str:record_code>/', GetSpecificPigMLDataController.as_view(), name='getPigMLData'),
    path('predict-weight/', PredictWeightController.as_view(), name='predictWeight'),
    path('classify-risk/', ClassifyRiskController.as_view(), name='classifyRisk'),
    path('suggest-feeding/', SuggestFeedingController.as_view(), name='suggestFeeding'),
]

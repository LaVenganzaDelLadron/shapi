from django.urls import path
from .controller.growth_stage_controller import (
    GrowthStageController,
    GetGrowthStagesController,
    DeleteGrowthStageController,
    UpdateGrowthStageController,
)

urlpatterns = [
    path('add/', GrowthStageController.as_view(), name='addGrowthStage'),
    path('all/', GetGrowthStagesController.as_view(), name='allGrowthStage'),
    path('delete/<str:growth_code>/', DeleteGrowthStageController.as_view(), name='deleteGrowthStage'),
    path('update/<str:growth_code>/', UpdateGrowthStageController.as_view(), name='updateGrowthStage'),
]

from django.urls import path

from .controller.decision_controller import (
    DmLoadDatasetController,
    DmPredictGrowthStageController,
    DmTrainDecisionTreeController,
)

urlpatterns = [
    path("load/", DmLoadDatasetController.as_view(), name="dmLoadTrainingDataset"),
    path("decision/", DmTrainDecisionTreeController.as_view(), name="dmTrainDecisionTree"),
    path("growth/", DmPredictGrowthStageController.as_view(), name="dmPredictGrowth"),
]

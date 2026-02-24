from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from dm.controller.tree_based import (
    load_training_dataset,
    predict_growth_stage,
    train_decision_tree_from_database,
)

_MODEL_CACHE = {
    "model": None,
    "label_encoder": None,
}


class DmLoadDatasetController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request):
        try:
            x_data, y_data = load_training_dataset()
            return Response(
                {
                    "message": "Training dataset loaded",
                    "total_records": len(x_data),
                    "feature_names": ["pig_age_days", "avg_weight"],
                    "target_preview": y_data[:5],
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class DmTrainDecisionTreeController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        test_size = float(request.data.get("test_size", 0.2))
        random_state = int(request.data.get("random_state", 42))
        max_depth_raw = request.data.get("max_depth")
        max_depth = int(max_depth_raw) if max_depth_raw not in (None, "") else None
        min_samples_leaf = int(request.data.get("min_samples_leaf", 1))

        try:
            result = train_decision_tree_from_database(
                test_size=test_size,
                random_state=random_state,
                max_depth=max_depth,
                min_samples_leaf=min_samples_leaf,
            )
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        _MODEL_CACHE["model"] = result["model"]
        _MODEL_CACHE["label_encoder"] = result["label_encoder"]

        return Response(
            {
                "message": "Decision tree trained",
                "feature_names": result["feature_names"],
                "class_names": result["class_names"],
                "metrics": result["metrics"],
            },
            status=status.HTTP_200_OK,
        )


class DmPredictGrowthStageController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        model = _MODEL_CACHE.get("model")
        label_encoder = _MODEL_CACHE.get("label_encoder")
        if model is None or label_encoder is None:
            return Response(
                {"message": "Model is not trained yet. Train first at /dm/decision."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pig_age_days = float(request.data["pig_age_days"])
            avg_weight = float(request.data["avg_weight"])
        except KeyError as exc:
            return Response(
                {"message": f"Missing required field: {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (TypeError, ValueError):
            return Response(
                {"message": "pig_age_days and avg_weight must be numeric values."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        predicted_stage = predict_growth_stage(
            model=model,
            label_encoder=label_encoder,
            pig_age_days=pig_age_days,
            avg_weight=avg_weight,
        )
        return Response(
            {
                "message": "Prediction generated",
                "predicted_growth_stage": predicted_stage,
            },
            status=status.HTTP_200_OK,
        )

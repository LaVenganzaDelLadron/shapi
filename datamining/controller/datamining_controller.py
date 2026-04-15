from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from datamining.models import PigMLData
from datamining.serializers import (
    ClassifyRiskSerializer,
    PigMLDataSerializer,
    PredictWeightSerializer,
    SuggestFeedingSerializer,
)
from datamining.services import classify_risk, predict_weight, suggest_feeding_adjustments


class GetPigMLDataController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request):
        dataset = PigMLData.objects.all()
        data = PigMLDataSerializer(dataset, many=True).data
        return Response(
            {
                'message': 'Pig ML dataset fetched successfully',
                'count': len(data),
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class GetSpecificPigMLDataController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request, record_code):
        row = PigMLData.objects.filter(record_code=record_code).first()
        if not row:
            return Response(
                {'message': f'Pig ML dataset row with record_code "{record_code}" not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                'message': f'Pig ML dataset row "{record_code}" fetched successfully',
                'data': PigMLDataSerializer(row).data,
            },
            status=status.HTTP_200_OK,
        )


class DataminingMLBaseController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def success_response(self, results, http_status=status.HTTP_200_OK):
        return Response({'status': 'success', 'results': results}, status=http_status)

    def error_response(self, message, http_status=status.HTTP_400_BAD_REQUEST, errors=None):
        payload = {'status': 'error', 'message': message}
        if errors:
            payload['errors'] = errors
        return Response(payload, status=http_status)


class PredictWeightController(DataminingMLBaseController):
    def post(self, request):
        serializer = PredictWeightSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response('Invalid input', status.HTTP_400_BAD_REQUEST, serializer.errors)

        try:
            results = predict_weight(serializer.validated_data)
        except ValueError as exc:
            return self.error_response(str(exc), status.HTTP_400_BAD_REQUEST)
        except Exception:
            return self.error_response('Unable to generate prediction right now.', status.HTTP_500_INTERNAL_SERVER_ERROR)

        return self.success_response(results)


class ClassifyRiskController(DataminingMLBaseController):
    def post(self, request):
        serializer = ClassifyRiskSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response('Invalid input', status.HTTP_400_BAD_REQUEST, serializer.errors)

        try:
            results = classify_risk(serializer.validated_data)
        except ValueError as exc:
            return self.error_response(str(exc), status.HTTP_400_BAD_REQUEST)
        except Exception:
            return self.error_response('Unable to classify risk right now.', status.HTTP_500_INTERNAL_SERVER_ERROR)

        return self.success_response(results)


class SuggestFeedingController(DataminingMLBaseController):
    def post(self, request):
        serializer = SuggestFeedingSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response('Invalid input', status.HTTP_400_BAD_REQUEST, serializer.errors)

        try:
            results = suggest_feeding_adjustments(**serializer.validated_data)
        except ValueError as exc:
            return self.error_response(str(exc), status.HTTP_400_BAD_REQUEST)
        except Exception:
            return self.error_response('Unable to suggest feeding adjustments right now.', status.HTTP_500_INTERNAL_SERVER_ERROR)

        return self.success_response(results)

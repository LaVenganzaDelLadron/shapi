from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from datamining.models import PigMLData
from datamining.serializers import PigMLDataSerializer


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

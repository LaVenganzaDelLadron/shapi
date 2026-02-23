from json import JSONDecodeError
from rest_framework import status
from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from growth.models import GrowthStage
import json
from growth.serializers import GrowthStageSerializer


class GrowthStageController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        try:
            payload = request.data
        except UnsupportedMediaType:
            try:
                payload = json.loads(request.body.decode('utf-8'))
            except (UnicodeDecodeError, JSONDecodeError):
                return Response(
                    {
                        "message": "Unsupported media type. Send JSON with Content-Type: application/json."
                    },
                    status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                )

        serializer = GrowthStageSerializer(data=payload)
        if serializer.is_valid():
            growth_stage = serializer.save()
            return Response(
                {
                    'message': "Growth Stage Successfully Created",
                    'growth_code': growth_stage.growth_code,
                    'growth_name': growth_stage.growth_name,
                },
                status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetGrowthStagesController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_all_growthstages(self):
        growth_stage = GrowthStage.objects.all().order_by('id')
        return GrowthStageSerializer(growth_stage, many=True).data

    def get(self, request):
        data = self.get_all_growthstages()
        return Response(
            {
                'message': 'Growth Stage fetched successfully',
                'count': len(data),
                'data': data,
            },
            status=status.HTTP_200_OK
        )


class DeleteGrowthStageController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def delete(self, request, growth_code):
        growth_code = GrowthStage.objects.filter(growth_code=growth_code).first()
        if not growth_code:
            return Response(
                {'message': f'Growth Stage "{growth_code}" not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        growth_code.delete()
        return Response(
            {'message': f'Growth Stage "{growth_code}" deleted successfully'},
            status=status.HTTP_200_OK,
        )

class UpdateGrowthStageController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def put(self, request, growth_code):
        growth_code = GrowthStage.objects.filter(growth_code=growth_code).first()
        if not growth_code:
            return Response(
                {'message': f'Growth Stage "{growth_code}" not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = GrowthStageSerializer(data=request.data, instance=growth_code)
        if serializer.is_valid():
            growth_stage = serializer.save()
            return Response(
                {
                    'message': f'Growth Stage "{growth_code}" Successfully Updated',
                    'data': GrowthStageSerializer(growth_stage).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, growth_code):
        growth_code = GrowthStage.objects.filter(growth_code=growth_code).first()
        if not growth_code:
            return Response(
                {'message': f'Growth Stage "{growth_code}" not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = GrowthStageSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            updated_growthstage = serializer.save()
            return Response(
                {
                    'message': f'Growth Stage "{growth_code}" updated successfully',
                    'data': GrowthStageSerializer(updated_growthstage).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


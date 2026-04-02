from rest_framework import status
from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from datamining.models import DataMining
import json
from json import JSONDecodeError
from datamining.serializers import DataMiningSerializer


class DataMiningController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        try:
            payload = request.data
        except UnsupportedMediaType:
            try:
                payload = json.loads(request.body.decode("utf-8"))
            except (UnicodeDecodeError, JSONDecodeError):
                return Response(
                    {
                        "message": "Unsupported media type. Send JSON with Content-Type: application/json."
                    },
                    status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                )

        serializer = DataMiningSerializer(data=payload)
        if serializer.is_valid():
            data_mining = serializer.save()
            return Response(
                {
                    'message': "Data Mining Successfully Created",
                    'data_mining_code': data_mining.data_mining_code,
                    'pig_age_days': data_mining.pig_age_days,
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetDataMiningController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_all_data_mining(self):
        data_mining_records = DataMining.objects.all().order_by('data_mining_code')
        return DataMiningSerializer(data_mining_records, many=True).data

    def get(self, request):
        data = self.get_all_data_mining()
        return Response(
            {
                'message': 'Data Mining records fetched successfully',
                'count': len(data),
                'data': data,
            },
            status=status.HTTP_200_OK,
        )
    
class GetSpecificDataMiningController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_specific_data_mining(self, data_mining_code):
        try:
            data_mining_record = DataMining.objects.get(data_mining_code=data_mining_code)
            return DataMiningSerializer(data_mining_record).data
        except DataMining.DoesNotExist:
            return None

    def get(self, request, data_mining_code):
        data = self.get_specific_data_mining(data_mining_code)
        if data is not None:
            return Response(
                {
                    'message': 'Data Mining record fetched successfully',
                    'data': data,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    'message': f'Data Mining record with code {data_mining_code} not found.',
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        
class DeleteDataMiningController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def delete(self, request, data_mining_code):
        try:
            data_mining_record = DataMining.objects.get(data_mining_code=data_mining_code)
            data_mining_record.delete()
            return Response(
                {
                    'message': f'Data Mining record with code {data_mining_code} deleted successfully.',
                },
                status=status.HTTP_200_OK,
            )
        except DataMining.DoesNotExist:
            return Response(
                {
                    'message': f'Data Mining record with code {data_mining_code} not found.',
                },
                status=status.HTTP_404_NOT_FOUND,
            )
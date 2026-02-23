import json
from json import JSONDecodeError
from rest_framework import status
from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from device.models import Device
from device.serializers import DeviceSerializer


class DeviceController(APIView):
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

        payload = dict(payload)
        if 'pen_code' not in payload and 'pen_code_id' in payload:
            payload['pen_code'] = payload.pop('pen_code_id')

        serializer = DeviceSerializer(data=payload)
        if serializer.is_valid():
            device = serializer.save()
            return Response(
                {
                    "message": "Device created",
                    "device": device.device_code,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetDeviceController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_all_devices(self):
        devices = Device.objects.all().order_by('device_code')
        return DeviceSerializer(devices, many=True).data

    def get(self, request):
        data = self.get_all_devices()
        return Response({
            'message': 'Devices fetched successfully',
            'count': len(data),
            'data': data,
        },
        status=status.HTTP_200_OK,
        )

class DeleteDeviceController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def delete(self, request, device_code):
        device = Device.objects.filter(device_code=device_code).first()
        if not device:
            return Response(
                {
                    "message": "Device with device code {} not found".format(device_code),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        device.delete()
        return Response(
            {
                "message": "Device with device code {} not found".format(device_code),
            },
            status=status.HTTP_200_OK,
        )

class UpdateDeviceController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def put(self, request, device_code):
        device = Device.objects.filter(device_code=device_code).first()
        if not device:
            return Response(
                {
                    "message": "Device with device code {} not found".format(device_code),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DeviceSerializer(device, data=request.data)
        if serializer.is_valid():
            update_device = serializer.save()
            return Response(
                {
                    'message': f'Device "{device_code}" updated successfully',
                    'data': DeviceSerializer(update_device).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, device_code):
        device = Device.objects.filter(device_code=device_code).first()
        if not device:
            return Response(
                {
                    "message": "Device with device code {} not found".format(device_code),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = DeviceSerializer(device, data=request.data, partial=True)
        if serializer.is_valid():
            update_device = serializer.save()
            return Response(
                {
                    'message': f'Device "{device_code}" updated successfully',
                    'data': DeviceSerializer(update_device).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


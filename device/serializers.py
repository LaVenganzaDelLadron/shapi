from rest_framework import serializers
from pen.models import Pen
from device.models import Device


class DeviceSerializer(serializers.ModelSerializer):
    pen_code = serializers.SlugRelatedField(
        slug_field='pen_code',
        queryset=Pen.objects.all(),
    )

    class Meta:
        model = Device
        fields = ('device_code', 'device_type', 'pen_code', 'date')



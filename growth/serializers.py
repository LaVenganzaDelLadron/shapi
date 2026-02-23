from rest_framework import serializers
from growth.models import GrowthStage

class GrowthStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrowthStage
        fields = ('growth_code', 'growth_name', 'date')

    def create(self, validated_data):
        return GrowthStage.objects.create(**validated_data)
    
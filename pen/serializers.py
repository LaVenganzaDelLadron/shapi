from rest_framework import serializers
from pen.models import Pen


class PenSerializer(serializers.ModelSerializer):
    status = serializers.CharField()

    class Meta:
        model = Pen
        fields = ('pen_code', 'pen_name', 'capacity', 'status', 'notes', 'date')

    def create(self, validated_data):
        return Pen.objects.create(**validated_data)

    def validate_status(self, value):
        normalized = value.lower().strip()
        allowed_statuses = {choice[0] for choice in Pen.pen_status}
        if normalized not in allowed_statuses:
            raise serializers.ValidationError(
                f"Invalid status '{value}'. Allowed values: {', '.join(sorted(allowed_statuses))}."
            )
        return normalized

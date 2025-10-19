from rest_framework import serializers
from django.conf import settings
from urllib.parse import urljoin

class VideoSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ['id', 'title', 'description', 'category', 'thumbnail_url', 'created_at']

    def get_thumbnail_url(self, obj):
        if obj.thumbnail_url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail_url.url)
            return urljoin(settings.MEDIA_URL, obj.thumbnail_url.url)
        return None

    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("The title must contain at least 3 characters.")
        return value

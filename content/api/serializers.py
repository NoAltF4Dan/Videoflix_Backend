from rest_framework import serializers
from django.conf import settings
from urllib.parse import urljoin
from ..models import Video

#--------------
# VideoSerializer
# Purpose:
#   Expose key Video fields and derive an absolute thumbnail URL suitable for clients.
#
# Fields (output):
#   - id, title, description, category, created_at
#   - thumbnail_url (read-only; computed via get_thumbnail_url)
#
# Thumbnail resolution:
#   - If a DRF request is present in serializer context, builds a fully-qualified URL
#     using request.build_absolute_uri(<file.url>).
#   - Otherwise, falls back to joining MEDIA_URL with the file's relative URL.
#   - Returns None when no thumbnail is set.
#
# Validation:
#   - title: must contain at least 3 non-whitespace characters.
#
# Notes:
#   - Ensure the view passes {"request": request} into serializer context to get absolute URLs.
#   - MEDIA_URL should be configured correctly for non-request contexts.
#--------------
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

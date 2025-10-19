from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework import status
from django.http import HttpResponse
from django.conf import settings

from .serializers import VideoSerializer
from ..models import Video

import os

#--------------
# VideoListView
# Purpose:
#   List all videos that have finished processing ("completed") for authenticated users.
#
# Permissions:
#   - IsAuthenticated (JWT/session required).
#
# Serializer context:
#   - Injects the current request into the serializer context so that
#     serializer methods can build absolute URLs (e.g., thumbnail_url).
#
# Notes:
#   - Queryset filters only completed videos to hide in-progress assets.
#--------------
class VideoListView(generics.ListAPIView):
    """API endpoint to list all videos that have been processed and marked as completed."""
    queryset = Video.objects.filter(processing_status='completed')
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        """Adds the current request to the serializer context to allow building absolute URLs."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
#--------------
# video_manifest
# Purpose:
#   Serve the HLS master/variant playlist (index.m3u8) for a specific video and resolution.
#
# Route params:
#   - movie_id: primary key of the Video.
#   - resolution: one of {"480p", "720p", "1080p"} mapped to stored HLS paths.
#
# Behavior:
#   - Ensures the Video exists and is completed.
#   - Maps requested resolution to its HLS directory and reads 'index.m3u8'.
#   - Returns 404 if the video/resolution/manifest file is missing.
#
# Permissions:
#   - IsAuthenticated.
#
# Response:
#   - Content-Type: application/vnd.apple.mpegurl
#   - Content-Disposition: inline
#--------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def video_manifest(request, movie_id, resolution):
    """Returns the HLS manifest file for a completed video at the specified resolution."""
    # Fetch video with completed status
    try:
        video = Video.objects.get(id=movie_id, processing_status='completed')
    except Video.DoesNotExist:
        return Response({"detail": "Video not found or not yet processed"}, status=status.HTTP_404_NOT_FOUND)

    # Map resolution to HLS path
    resolution_map = {
        '480p': video.hls_480p_path,
        '720p': video.hls_720p_path,
        '1080p': video.hls_1080p_path,
    }

    hls_path = resolution_map.get(resolution)
    if not hls_path:
        return Response({"detail": f"Resolution {resolution} not available"}, status=status.HTTP_404_NOT_FOUND)

    # Construct manifest file path
    manifest_file = os.path.join(settings.MEDIA_ROOT, hls_path, 'index.m3u8')

    # Check if manifest file exists
    if not os.path.exists(manifest_file):
        return Response({"detail": "Manifest file not found"}, status=status.HTTP_404_NOT_FOUND)

    # Serve the manifest file
    with open(manifest_file, 'r') as file:
        content = file.read()
    return HttpResponse(
        content,
        content_type='application/vnd.apple.mpegurl',
        headers={'Content-Disposition': 'inline'}
    )

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.conf import settings
from .models import Video
import os

#--------------
# video_segment
# Purpose:
#   Serve a specific HLS media segment (e.g., .ts) for a video at the given resolution.
#
# Route params:
#   - movie_id: primary key of the Video.
#   - resolution: one of {"480p", "720p", "1080p"} mapped to stored HLS paths.
#   - segment: filename of the requested segment (e.g., "segment_00001.ts").
#
# Behavior:
#   - Ensures the Video exists and is completed.
#   - Resolves the segment file on disk and streams it.
#   - Returns 404 if the video/resolution/segment is missing.
#
# Permissions:
#   - IsAuthenticated.
#
# Response:
#   - Content-Type: video/MP2T
#   - Content-Disposition: inline
#--------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def video_segment(request, movie_id, resolution, segment):
    """Serves a specific .ts video segment for a completed video at the requested resolution."""
    try:
        video = Video.objects.get(id=movie_id, processing_status='completed')
    except Video.DoesNotExist:
        return Response({"detail": "Video not found or not yet processed"}, status=status.HTTP_404_NOT_FOUND)

    resolution_map = {
        '480p': video.hls_480p_path,
        '720p': video.hls_720p_path,
        '1080p': video.hls_1080p_path,
    }

    hls_path = resolution_map.get(resolution)
    if not hls_path:
        return Response({"detail": f"Resolution {resolution} not available"}, status=status.HTTP_404_NOT_FOUND)

    segment_file = os.path.join(settings.MEDIA_ROOT, hls_path, segment)

    if not os.path.exists(segment_file):
        return Response({"detail": "Segment file not found"}, status=status.HTTP_404_NOT_FOUND)

    with open(segment_file,
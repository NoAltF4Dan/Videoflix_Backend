from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.conf import settings
from .models import Video
import os

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
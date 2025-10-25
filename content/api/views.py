from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings
import os
from .serializers import VideoSerializer
from .models import Video


#--------------
# VideoListView
# Purpose:
#   Fetches a list of videos marked as fully processed for authenticated users.
#
# Access:
#   - Requires authentication via JWT or session (IsAuthenticated).
#
# Serializer Context:
#   - Includes the current request to enable absolute URL construction (e.g., for thumbnails).
#
# Notes:
#   - Only videos with "completed" status are included, excluding those still processing.
#--------------
class VideoListView(generics.ListAPIView):
    """
    Endpoint to retrieve all videos that are fully processed and ready.
    """
    permission_classes = [IsAuthenticated]
    queryset = Video.objects.filter(processing_status='completed')
    serializer_class = VideoSerializer

    def get_serializer_context(self):
        """
        Adds the request to the serializer context for absolute URL generation.
        """
        context = super().get_serializer_context()
        context['req'] = self.request
        return context


#--------------
# video_manifest
# Purpose:
#   Delivers the HLS master playlist (index.m3u8) for a video at a given resolution.
#
# Parameters:
#   - movie_id: The Video model's primary key.
#   - resolution: Resolution type ("480p", "720p", "1080p") mapped to HLS paths.
#
# Behavior:
#   - Checks if the video exists and is fully processed.
#   - Resolves the HLS path for the requested resolution and serves index.m3u8.
#   - Returns 404 if video, resolution, or manifest file is unavailable.
#
# Access:
#   - Requires authentication (IsAuthenticated).
#
# Response:
#   - Content-Type: application/vnd.apple.mpegurl
#   - Content-Disposition: inline
#--------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def video_manifest(request, movie_id, resolution):
    """
    Serves the HLS manifest for a processed video at the specified resolution.
    """
    try:
        video = Video.objects.get(id=movie_id, processing_status='completed')
    except Video.DoesNotExist:
        return Response({"error": "Video not found or not processed"}, status=status.HTTP_404_NOT_FOUND)

    quality_map = {
        '480p': video.hls_480p_path,
        '720p': video.hls_720p_path,
        '1080p': video.hls_1080p_path,
    }

    selected_hls_path = quality_map.get(resolution)
    if not selected_hls_path:
        return Response({"error": f"Resolution {resolution} not supported"}, status=status.HTTP_404_NOT_FOUND)

    playlist_path = os.path.join(settings.MEDIA_ROOT, selected_hls_path, 'index.m3u8')

    if not os.path.exists(playlist_path):
        return Response({"error": "Playlist file not found"}, status=status.HTTP_404_NOT_FOUND)

    with open(playlist_path, 'r') as playlist:
        content = playlist.read()
    return HttpResponse(
        content,
        content_type='application/vnd.apple.mpegurl',
        headers={'Content-Disposition': 'inline'}
    )


#--------------
# video_segment
# Purpose:
#   Serves a specific HLS media segment (e.g., .ts file) for a video at the given resolution.
#
# Parameters:
#   - movie_id: The Video model's primary key.
#   - resolution: Resolution type ("480p", "720p", "1080p") mapped to HLS paths.
#   - segment: Name of the requested segment (e.g., "segment_00001.ts").
#
# Behavior:
#   - Verifies the video exists and is fully processed.
#   - Locates and streams the requested segment file.
#   - Returns 404 if video, resolution, or segment file is missing.
#
# Access:
#   - Requires authentication (IsAuthenticated).
#
# Response:
#   - Content-Type: video/MP2T
#   - Content-Disposition: inline
#--------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def video_segment(request, movie_id, resolution, segment):
    """
    Delivers a specific HLS segment for a processed video at the given resolution.
    """
    try:
        video = Video.objects.get(id=movie_id, processing_status='completed')
    except Video.DoesNotExist:
        return Response({"error": "Video not found or not processed"}, status=status.HTTP_404_NOT_FOUND)

    quality_map = {
        '480p': video.hls_480p_path,
        '720p': video.hls_720p_path,
        '1080p': video.hls_1080p_path,
    }

    selected_hls_path = quality_map.get(resolution)
    if not selected_hls_path:
        return Response({"error": f"Resolution {resolution} not supported"}, status=status.HTTP_404_NOT_FOUND)

    segment_path = os.path.join(settings.MEDIA_ROOT, selected_hls_path, segment)

    if not os.path.exists(segment_path):
        return Response({"error": "Segment file not found"}, status=status.HTTP_404_NOT_FOUND)

    with open(segment_path, 'rb') as segment_file:
        content = segment_file.read()
    return HttpResponse(
        content,
        content_type='video/MP2T',
        headers={'Content-Disposition': 'inline'}
    )
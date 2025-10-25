from django.urls import path

from .views import VideoListView, video_manifest, video_segment

urlpatterns = [
    path('video/', VideoListView.as_view(), name='video-list'),
    path('video/<int:movie_id>/<str:resolution>/index.m3u8', video_manifest, name='video-manifest'),
    path('video/<int:movie_id>/<str:resolution>/<str:segment>/', video_segment, name='video-segment'),
]

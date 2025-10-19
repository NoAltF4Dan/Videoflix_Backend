from django.db import models
from django_rq import get_queue
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower
from django.core.validators import FileExtensionValidator
from .utils import video_upload_path, validate_video_size, thumbnail_upload_path


class Video(models.Model):
    """
    Represent a video entity with metadata, category, processing status, HLS output paths, thumbnail,

    and automatic background processing upon creation, enforcing a case-insensitive unique title constraint.
    """

    CATEGORY_CHOICES = [
        ('Action', 'Action'),
        ('Comedy', 'Comedy'),
        ('Drama', 'Drama'),
        ('Horror', 'Horror'),
        ('Romance', 'Romance'),
        ('Thriller', 'Thriller'),
        ('Documentary', 'Documentary'),
        ('Animation', 'Animation'),
    ]

    PROCESSING_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    title = models.CharField(max_length=200, unique=True, blank=False, null=False)
    description = models.TextField(blank=False, null=False)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=False, null=False)
    original_video = models.FileField(
        upload_to=video_upload_path,
        validators=[
            FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov', 'mkv']),
            validate_video_size
        ], blank=False, null=False
    )
    thumbnail_url = models.ImageField(upload_to=thumbnail_upload_path, blank=False, null=False)
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hls_480p_path = models.CharField(max_length=500, blank=True, null=True)
    hls_720p_path = models.CharField(max_length=500, blank=True, null=True)
    hls_1080p_path = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            UniqueConstraint(Lower("title"), name="unique_title_case_insensitive")
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and self.original_video:
            from .tasks import process_video
            queue = get_queue("default")
            queue.enqueue(process_video, self.id)

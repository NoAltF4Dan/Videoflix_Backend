import uuid

from django.core.exceptions import ValidationError


def validate_video_size(file):
    max_size = 10.5 * 1024 * 1024  # 10MB in bytes
    if file.size > max_size:
        raise ValidationError(f'Die Datei ist zu groß. Maximum: 10MB, Aktuell: {file.size / 1024 / 1024:.2f}MB')


def video_upload_path(instance, filename):
    return f'videos/original/{instance.id}/{filename}'


def thumbnail_upload_path(instance, filename):
    identifier = instance.id if instance.id else uuid.uuid4().hex
    return f'videos/thumbnails/{identifier}/{filename}'

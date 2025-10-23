from pathlib import Path
import subprocess
import tempfile
from typing import Dict

from django.conf import settings
from django.core.files import File
from django_rq import job

from .models import Video


def _media_path(*parts: str) -> Path:
    return Path(settings.MEDIA_ROOT).joinpath(*parts)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _run_ffmpeg(cmd: list) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}):\n{stderr[:4000]}")


def _transcode_to_hls(input_path: Path, out_dir: Path, *, width: int, height: int, v_bitrate: str) -> None:
    _ensure_dir(out_dir)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-vf",
        f"scale={width}:{height}",
        "-b:v",
        v_bitrate,
        "-b:a",
        "128k",
        "-hls_time",
        "10",
        "-hls_list_size",
        "0",
        "-hls_segment_filename",
        str(out_dir / "%03d.ts"),
        "-f",
        "hls",
        str(out_dir / "index.m3u8"),
    ]
    _run_ffmpeg(cmd)


def _make_thumbnail(input_path: Path, thumb_abs_path: Path) -> None:
    _ensure_dir(thumb_abs_path.parent)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        tmp = Path(temp_file.name)
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-ss",
            "00:00:03",
            "-vframes",
            "1",
            "-vf",
            "scale=320:180",
            str(tmp),
        ]
        _run_ffmpeg(cmd)
        tmp.replace(thumb_abs_path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass


@job("default", timeout=7200)
def process_video(video_id: int) -> None:
    try:
        video = Video.objects.get(pk=video_id)
    except Video.DoesNotExist:
        return

    video.processing_status = "processing"
    video.save(update_fields=["processing_status"])

    try:
        if not hasattr(video, "original_video") or not video.original_video:
            raise RuntimeError("missing original_video")

        input_path = Path(video.original_video.path)
        if not input_path.exists():
            raise RuntimeError(f"missing file: {input_path}")

        base_rel = Path("videos") / "processed" / str(video.id)
        base_abs = _media_path(base_rel)
        _ensure_dir(base_abs)

        profiles: Dict[str, Dict[str, str | int]] = {
            "480p": {"width": 854, "height": 480, "vbr": "1000k"},
            "720p": {"width": 1280, "height": 720, "vbr": "2500k"},
            "1080p": {"width": 1920, "height": 1080, "vbr": "5000k"},
        }

        for name, p in profiles.items():
            out_rel = base_rel / name
            out_abs = base_abs / name
            _transcode_to_hls(
                input_path=input_path,
                out_dir=out_abs,
                width=int(p["width"]),
                height=int(p["height"]),
                v_bitrate=str(p["vbr"]),
            )
            rel_str = str(out_rel.as_posix())
            if name == "480p" and hasattr(video, "hls_480p_path"):
                video.hls_480p_path = rel_str
            elif name == "720p" and hasattr(video, "hls_720p_path"):
                video.hls_720p_path = rel_str
            elif name == "1080p" and hasattr(video, "hls_1080p_path"):
                video.hls_1080p_path = rel_str

        thumb_rel = Path("videos") / "thumbnails" / f"{video.id}.jpg"
        thumb_abs = _media_path(thumb_rel)
        _make_thumbnail(input_path, thumb_abs)

        if hasattr(video, "thumbnail") and video.thumbnail:
            with open(thumb_abs, "rb") as f:
                video.thumbnail.save(f"{video.id}.jpg", File(f), save=False)
            try:
                thumb_abs.unlink()
            except Exception:
                pass
        elif hasattr(video, "thumbnail_url"):
            video.thumbnail_url = str(thumb_rel.as_posix())

        video.processing_status = "completed"
        video.save()
    except Exception as exc:
        print(f"[process_video] video {video_id}: {exc}")
        video.processing_status = "failed"
        video.save(update_fields=["processing_status"])

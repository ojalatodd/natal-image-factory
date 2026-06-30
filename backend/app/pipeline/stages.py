"""The six pipeline stages — Phase 1 implementation.

Stage 1: Transcribe audio via Whisper API (graceful fallback if no API key)
Stage 2: Semantic segmentation via GPT-4o (graceful fallback)
Stage 3: Search public-domain sources via source adapters
Stage 4: Rank candidates via GPT-4o Vision (graceful fallback)
Stage 5: Download, normalize, and upload still images
Stage 6: Package ZIP with numbered files + manifest.txt
"""
from __future__ import annotations

import asyncio
import io
import logging
import tempfile
import zipfile
from datetime import timedelta
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app import progress, storage
from app.ai import generate_image, rank_candidates, segment_text, transcribe_audio
from app.models import (
    AiSettings,
    Asset,
    AssetStatus,
    MediaMix,
    MediaType,
    Project,
    Segment,
    SourceAdapterConfig,
)
from app.visual_styles import get_visual_style_prompt

# Import adapters so they register on import
from app.pipeline.adapters import wikimedia, loc, internet_archive, met, smithsonian  # noqa: F401
from app.pipeline.adapters import wikimedia_video  # noqa: F401
from app.pipeline.adapters import internet_archive_video  # noqa: F401
from app.pipeline.adapters import pexels  # noqa: F401
from app.pipeline.adapters.base import CandidateAsset, get_adapters
from app.pipeline.image_utils import image_to_bytes, thumbnail_to_bytes
from app.pipeline.media import (
    extract_thumbnail,
    ffmpeg_available,
    ken_burns_from_still,
    probe_duration,
    trim_and_normalize,
)

logger = logging.getLogger("natal")


# ---- Stage 1: Transcribe & align (Whisper) ----
def transcribe(db: Session, project: Project) -> dict:
    progress.publish(project.id, "transcribe", 10, "Transcribing voiceover…")

    if not project.source_audio_key:
        progress.publish(project.id, "transcribe", 25, "No voiceover uploaded — skipping transcription")
        return {"duration_s": 0.0, "words": []}

    audio_bytes = storage.download_bytes(project.source_audio_key)
    filename = Path(project.source_audio_key).name

    result = transcribe_audio(audio_bytes, filename=filename)

    # Update project audio duration if we got a better measurement
    if result["duration_s"] and result["duration_s"] > 0:
        project.audio_duration_s = result["duration_s"]
        db.commit()

    progress.publish(project.id, "transcribe", 25, f"Transcribed {len(result['words'])} words")
    return result


# ---- Stage 2: Semantic segmentation (GPT-4o) ----
def segment(db: Session, project: Project, transcript: dict) -> list[Segment]:
    progress.publish(project.id, "segment", 30, "Finding thematic segments…")

    # Load article text from Spaces
    article_text = ""
    if project.source_text_key:
        try:
            raw = storage.download_bytes(project.source_text_key)
            article_text = raw.decode("utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Could not load article text: %s", exc)

    ai_config = _get_ai_config(db, project)
    seg_data = segment_text(article_text, transcript, ai_config=ai_config)

    # Clear old segments for re-runs
    db.query(Segment).filter(Segment.project_id == project.id).delete()
    db.commit()

    segments: list[Segment] = []
    for s in seg_data:
        seg = Segment(
            project_id=project.id,
            index=s["index"],
            start_s=s["start_s"],
            end_s=s["end_s"],
            duration_s=s["duration_s"],
            theme_label=s["theme_label"],
            summary=s["summary"],
            search_query=s["search_query"],
        )
        db.add(seg)
        db.commit()
        db.refresh(seg)
        segments.append(seg)

    progress.publish(project.id, "segment", 45, f"Created {len(segments)} segments")
    return segments


def _select_adapters(db: Session, project: Project):
    """Return registered adapters filtered and ordered by the project owner's
    SourceAdapterConfig. If the user has no saved config, return all adapters.
    """
    all_adapters = get_adapters()
    configs = (
        db.query(SourceAdapterConfig)
        .filter(SourceAdapterConfig.user_id == project.user_id)
        .all()
    )
    if not configs:
        return all_adapters

    # Map (name, media_type_str) -> config for enabled lookup and priority ordering
    by_key = {(c.source_name, c.media_type.value): c for c in configs}

    selected = []
    for adapter in all_adapters:
        cfg = by_key.get((adapter.name, adapter.media_type))
        # Only include adapters explicitly enabled in the user's config
        if cfg and cfg.enabled:
            selected.append((cfg.priority, adapter))

    selected.sort(key=lambda pair: pair[0])
    return [adapter for _, adapter in selected]


def _get_ai_config(db: Session, project: Project) -> AiSettings | None:
    return db.query(AiSettings).filter(AiSettings.user_id == project.user_id).first()


# ---- Stage 3: Media search (stills + video) ----
def search_media(db: Session, project: Project, segments: list[Segment]) -> None:
    progress.publish(project.id, "search", 50, "Searching public-domain sources…")

    # Determine which media type to search for
    media_mix = project.media_mix
    search_types: list[MediaType] = []
    if media_mix == MediaMix.stills:
        search_types = [MediaType.still]
    elif media_mix == MediaMix.video:
        search_types = [MediaType.video]
    elif media_mix == MediaMix.balanced:
        search_types = [MediaType.still, MediaType.video]
    else:  # ai_judgement
        search_types = [MediaType.still, MediaType.video]

    # Get registered adapters, filtered/ordered by the user's saved source config
    adapters = _select_adapters(db, project)
    still_adapters = [a for a in adapters if a.media_type == "still"]
    video_adapters = [a for a in adapters if a.media_type == "video"]

    ai_config = _get_ai_config(db, project)

    for seg in segments:
        # Clear old assets for re-runs
        db.query(Asset).filter(Asset.segment_id == seg.id).delete()
        db.commit()

        query = seg.search_query or seg.theme_label or project.name
        style = get_visual_style_prompt(project.visual_style)

        types_to_search = search_types

        for mtype in types_to_search:
            adapter_list = still_adapters if mtype == MediaType.still else video_adapters
            for adapter in adapter_list:
                try:
                    results = asyncio.run(
                        adapter.search(query, style=style, min_duration_s=seg.duration_s, limit=5)
                    )
                    for c in results:
                        asset = Asset(
                            segment_id=seg.id,
                            media_type=mtype,
                            source_name=c.source_name,
                            source_url=c.source_url,
                            download_url=c.download_url,
                            license=c.license,
                            attribution=c.attribution,
                            thumbnail_url=c.thumbnail_url,
                            width=c.width,
                            height=c.height,
                            duration_s=c.duration_s,
                            status=AssetStatus.candidate,
                        )
                        db.add(asset)
                except Exception as exc:
                    logger.warning("Adapter %s failed for segment %d: %s", adapter.name, seg.index, exc)

        db.commit()

        # DALL-E fallback: if no candidates and AI images enabled, generate one
        asset_count = db.query(Asset).filter(Asset.segment_id == seg.id).count()
        if asset_count == 0 and project.ai_images_enabled and MediaType.still in types_to_search:
            logger.info("Segment %d: no candidates, trying DALL-E fallback", seg.index)
            ai_bytes = generate_image(query, style=style, ai_config=ai_config)
            if ai_bytes:
                # DALL-E returns PNG; normalize through Pillow to real JPEG + dimensions
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(ai_bytes)
                    tmp_path = Path(tmp.name)
                try:
                    normalized_bytes, width, height = image_to_bytes(tmp_path)
                    thumb_bytes = thumbnail_to_bytes(tmp_path)
                finally:
                    tmp_path.unlink(missing_ok=True)

                media_key = f"media/{project.id}/{seg.index:02d}_ai.jpg"
                thumb_key = f"thumbs/{project.id}/ai_{seg.id}.jpg"
                storage.upload_bytes(media_key, normalized_bytes, "image/jpeg")
                storage.upload_bytes(thumb_key, thumb_bytes, "image/jpeg")
                thumb_url = storage.public_url(thumb_key)

                asset = Asset(
                    segment_id=seg.id,
                    media_type=MediaType.still,
                    source_name="DALL-E 3 (AI Generated)",
                    source_url=None,
                    license="AI Generated",
                    attribution="Generated by OpenAI DALL-E 3",
                    thumbnail_url=thumb_url,
                    thumbnail_key=thumb_key,
                    spaces_key=media_key,
                    width=width,
                    height=height,
                    status=AssetStatus.processed,
                    is_chosen=True,
                )
                db.add(asset)
                db.commit()
                seg.chosen_asset_id = asset.id
                seg.chosen_media_type = MediaType.still
                db.commit()
                logger.info("Segment %d: DALL-E fallback image generated", seg.index)

        logger.info("Segment %d: search complete", seg.index)

    progress.publish(project.id, "search", 60, "Search complete")


# ---- Stage 4: Rank & match (GPT-4o Vision) ----
def rank_match(db: Session, project: Project, segments: list[Segment]) -> None:
    progress.publish(project.id, "rank", 65, "Ranking candidate media…")

    ai_config = _get_ai_config(db, project)

    for seg in segments:
        # Skip if already chosen (e.g., DALL-E fallback in search stage)
        if seg.chosen_asset_id:
            continue

        assets = db.query(Asset).filter(Asset.segment_id == seg.id).all()
        if not assets:
            seg.chosen_media_type = MediaType.still
            continue

        # Build candidate list for Vision API
        candidates_with_urls = [
            {
                "url": a.thumbnail_url or a.source_url or "",
                "title": a.attribution or "",
                "media_type": a.media_type.value if a.media_type else "still",
                "duration_s": a.duration_s,
            }
            for a in assets
            if a.thumbnail_url or a.source_url
        ]

        if candidates_with_urls:
            scored = rank_candidates(
                seg.summary or "",
                seg.search_query or "",
                candidates_with_urls,
                ai_config=ai_config,
            )

            # Map scores back to assets by URL
            for score_entry in scored:
                url = score_entry["url"]
                for a in assets:
                    if (a.thumbnail_url or a.source_url) == url:
                        a.relevance_score = score_entry["relevance_score"]
                        break

            # Pick the best one
            best = max(assets, key=lambda a: a.relevance_score or 0.0)
            best.is_chosen = True
            seg.chosen_asset_id = best.id
            seg.chosen_media_type = best.media_type
        else:
            assets[0].is_chosen = True
            seg.chosen_asset_id = assets[0].id
            seg.chosen_media_type = assets[0].media_type

        db.commit()

    progress.publish(project.id, "rank", 75, "Ranking complete")


# ---- Stage 5: Acquire, trim & normalize ----
def acquire_process(db: Session, project: Project, segments: list[Segment]) -> None:
    progress.publish(project.id, "process", 80, "Preparing media (download/normalize)…")

    for seg in segments:
        if not seg.chosen_asset_id:
            continue

        asset = db.get(Asset, seg.chosen_asset_id)
        if not asset:
            continue

        # Skip if already processed (e.g., DALL-E fallback)
        if asset.status == AssetStatus.processed:
            continue

        try:
            if asset.media_type == MediaType.still:
                _process_still(db, project, seg, asset)
            else:
                _process_video(db, project, seg, asset)

            db.commit()
        except Exception as exc:
            asset.status = AssetStatus.failed
            db.commit()
            logger.error("Failed to process asset %d: %s", asset.id, exc)

    progress.publish(project.id, "process", 90, "Media preparation complete")


def _process_still(db: Session, project: Project, seg: Segment, asset: Asset) -> None:
    """Download a still image, normalize it, upload to Spaces, and generate a thumbnail."""
    adapters = get_adapters(media_type="still")
    adapter = None
    for a in adapters:
        if a.name == asset.source_name:
            adapter = a
            break

    if not adapter or not asset.thumbnail_url:
        resp = httpx.get(asset.thumbnail_url or asset.source_url or "", timeout=60, follow_redirects=True)
        resp.raise_for_status()
        raw_bytes = resp.content
    else:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            candidate = CandidateAsset(
                source_name=asset.source_name,
                media_type="still",
                source_url=asset.source_url or "",
                thumbnail_url=asset.thumbnail_url,
                download_url=asset.download_url,
                license=asset.license,
                attribution=asset.attribution,
            )
            asyncio.run(adapter.fetch(candidate, tmp_path))
            raw_bytes = tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)

    # Save raw to temp file for Pillow processing
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = Path(tmp.name)

    try:
        # Normalize image and get bytes + dimensions
        normalized_bytes, width, height = image_to_bytes(tmp_path)
        thumb_bytes = thumbnail_to_bytes(tmp_path)

        # Upload to Spaces
        media_key = f"media/{project.id}/{seg.index:02d}_{asset.id}.jpg"
        thumb_key = f"thumbs/{project.id}/{asset.id}.jpg"

        storage.upload_bytes(media_key, normalized_bytes, "image/jpeg")
        storage.upload_bytes(thumb_key, thumb_bytes, "image/jpeg")

        # Update asset
        asset.spaces_key = media_key
        asset.thumbnail_key = thumb_key
        asset.width = width
        asset.height = height
        asset.status = AssetStatus.processed
    finally:
        tmp_path.unlink(missing_ok=True)


def _process_video(db: Session, project: Project, seg: Segment, asset: Asset) -> None:
    """Download a video, trim to segment duration, normalize, and upload to Spaces."""
    adapters = get_adapters(media_type="video")
    adapter = None
    for a in adapters:
        if a.name == asset.source_name:
            adapter = a
            break

    # Download the source video to a temp file
    raw_path = Path(tempfile.mktemp(suffix="_src.mp4"))
    norm_path = Path(tempfile.mktemp(suffix="_norm.mp4"))
    thumb_path = Path(tempfile.mktemp(suffix="_thumb.jpg"))

    try:
        if adapter and asset.download_url:
            candidate = CandidateAsset(
                source_name=asset.source_name,
                media_type="video",
                source_url=asset.source_url or "",
                thumbnail_url=asset.thumbnail_url,
                download_url=asset.download_url,
                license=asset.license,
                attribution=asset.attribution,
                duration_s=asset.duration_s,
            )
            asyncio.run(adapter.fetch(candidate, raw_path))
        else:
            resp = httpx.get(asset.download_url or asset.source_url or "", timeout=120, follow_redirects=True)
            resp.raise_for_status()
            raw_path.write_bytes(resp.content)

        # Probe actual duration if not already known
        actual_duration = asset.duration_s or 0.0
        if not actual_duration and ffmpeg_available():
            try:
                actual_duration = probe_duration(raw_path)
            except Exception as exc:
                logger.warning("Could not probe duration for asset %d: %s", asset.id, exc)

        # Determine trim parameters
        seg_duration = max(seg.duration_s, 2.0)
        if actual_duration and actual_duration > 0:
            # Use the video from the start, trim to segment duration
            trim_start = 0.0
            trim_duration = min(seg_duration, actual_duration)
        else:
            trim_start = 0.0
            trim_duration = seg_duration

        # Trim and normalize to 1080p H.264
        trim_and_normalize(
            raw_path,
            norm_path,
            start_s=trim_start,
            duration_s=trim_duration,
        )

        # Extract thumbnail from the normalized clip
        thumb_at = min(1.0, trim_duration / 2)
        extract_thumbnail(norm_path, thumb_path, at_s=thumb_at)

        # Upload normalized video and thumbnail to Spaces
        media_key = f"media/{project.id}/{seg.index:02d}_{asset.id}.mp4"
        thumb_key = f"thumbs/{project.id}/{asset.id}.jpg"

        storage.upload_bytes(media_key, norm_path.read_bytes(), "video/mp4")
        storage.upload_bytes(thumb_key, thumb_path.read_bytes(), "image/jpeg")

        # Update asset
        asset.spaces_key = media_key
        asset.thumbnail_key = thumb_key
        asset.duration_s = trim_duration
        asset.status = AssetStatus.processed

        logger.info(
            "Processed video asset %d: %s (trimmed %.1fs from %.1fs source)",
            asset.id, media_key, trim_duration, actual_duration,
        )
    finally:
        raw_path.unlink(missing_ok=True)
        norm_path.unlink(missing_ok=True)
        thumb_path.unlink(missing_ok=True)


# ---- Stage 5b: Ken Burns motion (optional) ----
def apply_ken_burns(db: Session, project: Project, segments: list[Segment]) -> None:
    """Generate Ken Burns pan/zoom MP4 clips from chosen still assets.

    Only runs when project.ai_video_motion is True and ffmpeg is available.
    Skips assets that already have a video_key (re-runs).
    """
    if not project.ai_video_motion:
        return

    if not ffmpeg_available():
        logger.warning("Ken Burns requested but ffmpeg not available — skipping")
        return

    progress.publish(project.id, "ken_burns", 92, "Generating Ken Burns motion…")

    for seg in segments:
        if not seg.chosen_asset_id:
            continue

        asset = db.get(Asset, seg.chosen_asset_id)
        if not asset or asset.media_type != MediaType.still:
            continue
        if not asset.spaces_key:
            continue
        if asset.video_key:
            continue

        try:
            still_bytes = storage.download_bytes(asset.spaces_key)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_in:
                tmp_in.write(still_bytes)
                src_path = Path(tmp_in.name)

            dest_path = src_path.with_suffix(".mp4")
            try:
                ken_burns_from_still(
                    src_path,
                    dest_path,
                    duration_s=max(seg.duration_s, 2.0),
                )
                video_bytes = dest_path.read_bytes()
            finally:
                src_path.unlink(missing_ok=True)
                dest_path.unlink(missing_ok=True)

            video_key = f"video/{project.id}/{seg.index:02d}_{asset.id}.mp4"
            storage.upload_bytes(video_key, video_bytes, "video/mp4")
            asset.video_key = video_key
            db.commit()

            logger.info("Segment %d: Ken Burns clip generated (%.1fs)",
                        seg.index, seg.duration_s)
        except Exception as exc:
            logger.warning("Ken Burns failed for segment %d: %s", seg.index, exc)

    progress.publish(project.id, "ken_burns", 95, "Ken Burns motion complete")


# ---- Stage 6: Package ZIP + manifest ----
def package(db: Session, project: Project, segments: list[Segment]) -> str:
    progress.publish(project.id, "package", 95, "Packaging download…")

    buf = io.BytesIO()
    manifest_lines: list[str] = []

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        file_index = 0
        for seg in segments:
            if not seg.chosen_asset_id:
                continue

            asset = db.get(Asset, seg.chosen_asset_id)
            if not asset or asset.status != AssetStatus.processed or not asset.spaces_key:
                continue

            file_index += 1
            ext = "jpg" if asset.media_type == MediaType.still else "mp4"
            filename = f"{file_index:02d}.{ext}"

            # Download from Spaces and add to ZIP
            media_bytes = storage.download_bytes(asset.spaces_key)
            zf.writestr(filename, media_bytes)

            # If Ken Burns video exists, include it alongside the still
            if asset.video_key:
                file_index += 1
                video_filename = f"{file_index:02d}_motion.mp4"
                video_bytes = storage.download_bytes(asset.video_key)
                zf.writestr(video_filename, video_bytes)

            # Format timestamps
            start_ts = _format_timestamp(seg.start_s)
            end_ts = _format_timestamp(seg.end_s)

            manifest_lines.append(
                f"{filename}\t{start_ts} - {end_ts}\t{seg.theme_label or 'Segment ' + str(seg.index)}\t"
                f"Source: {asset.source_name}\tLicense: {asset.license or 'Unknown'}\t"
                f"Attribution: {asset.attribution or 'N/A'}"
            )

            if asset.video_key:
                manifest_lines.append(
                    f"{video_filename}\t{start_ts} - {end_ts}\t"
                    f"Ken Burns motion (pan/zoom)\tSource: {asset.source_name}\t"
                    f"License: {asset.license or 'Unknown'}\t"
                    f"Attribution: {asset.attribution or 'N/A'}"
                )

        # Write manifest
        manifest_content = "Natal Image Factory - Manifest\n"
        manifest_content += f"Project: {project.name}\n"
        manifest_content += f"Files: {file_index}\n"
        manifest_content += f"{'=' * 60}\n\n"
        if file_index == 0:
            manifest_content += (
                "WARNING: No media files were packaged.\n"
                "All assets failed to download during processing.\n"
                "Please re-generate this project to retry.\n"
            )
            logger.warning("Package stage: project %d produced 0 media files — all assets failed", project.id)
        else:
            manifest_content += "\n".join(manifest_lines)
        manifest_content += "\n"
        zf.writestr("manifest.txt", manifest_content)

    # Upload ZIP to Spaces
    zip_key = f"output/project_{project.id}.zip"
    storage.upload_bytes(zip_key, buf.getvalue(), "application/zip")

    progress.publish(project.id, "package", 100, f"Packaged {file_index} files")
    return zip_key


def _format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

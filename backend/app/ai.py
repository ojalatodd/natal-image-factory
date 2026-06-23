"""OpenAI API helpers for transcription, segmentation, and vision ranking.

All functions gracefully degrade when OPENAI_API_KEY is not set, returning
placeholder data so the pipeline can still be exercised end-to-end.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from app.config import settings

logger = logging.getLogger("natal")

_client: OpenAI | None = None


def _get_client() -> OpenAI | None:
    global _client
    if _client is not None:
        return _client
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — AI stages will use placeholder data")
        return None
    _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.mp3") -> dict[str, Any]:
    """Transcribe audio via Whisper API and return word-level timeline.

    Returns: {"duration_s": float, "words": [{"word": str, "start_s": float, "end_s": float}]}
    """
    client = _get_client()
    if client is None:
        return {"duration_s": 0.0, "words": []}

    import io

    response = client.audio.transcriptions.with_response_format(
        response_format="verbose_json"
    ).create(
        file=(filename, io.BytesIO(audio_bytes)),
        model="whisper-1",
        timestamp_granularities=["word"],
    )

    words: list[dict[str, Any]] = []
    raw_words = getattr(response, "words", None) or []
    for w in raw_words:
        words.append(
            {
                "word": w.get("word", w.get("text", "")),
                "start_s": float(w.get("start", 0.0)),
                "end_s": float(w.get("end", 0.0)),
            }
        )

    duration = float(getattr(response, "duration", 0.0))
    return {"duration_s": duration, "words": words}


def segment_text(
    article_text: str,
    transcript: dict[str, Any],
    *,
    target_segment_s: float = 30.0,
    max_segments: int = 40,
) -> list[dict[str, Any]]:
    """Use GPT-4o to split the narration into thematic segments.

    Returns: [{"index": int, "start_s": float, "end_s": float, "duration_s": float,
               "theme_label": str, "summary": str, "search_query": str}]
    """
    client = _get_client()
    if client is None:
        duration = transcript.get("duration_s", 0.0)
        return [
            {
                "index": 1,
                "start_s": 0.0,
                "end_s": duration,
                "duration_s": duration,
                "theme_label": "Full narration",
                "summary": article_text[:500] if article_text else "",
                "search_query": "historical illustration",
            }
        ]

    word_list = transcript.get("words", [])
    word_summary = " ".join([w["word"] for w in word_list[:200]])

    system_prompt = (
        "You are a video editor assistant. Given an article and a narration transcript, "
        "split the narration into thematic segments. Each segment should be roughly "
        f"{target_segment_s} seconds long (but can vary based on content). "
        "For each segment, provide: start_s, end_s (in seconds from the audio), "
        "theme_label (short title), summary (1-2 sentences), and search_query "
        "(a concise query to find relevant public-domain images). "
        f"Return at most {max_segments} segments. "
        "Return JSON: {\"segments\": [{\"index\": int, \"start_s\": float, \"end_s\": float, "
        "\"theme_label\": str, \"summary\": str, \"search_query\": str}]}"
    )

    user_content = (
        f"ARTICLE TEXT:\n{article_text[:4000]}\n\n"
        f"TRANSCRIPT (first 200 words):\n{word_summary}\n\n"
        f"Audio duration: {transcript.get('duration_s', 0.0)} seconds"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    content = response.choices[0].message.content or "{}"
    parsed = json.loads(content)
    segments_raw = parsed.get("segments", [])

    segments: list[dict[str, Any]] = []
    for i, seg in enumerate(segments_raw):
        start = float(seg.get("start_s", 0.0))
        end = float(seg.get("end_s", start + target_segment_s))
        segments.append(
            {
                "index": i + 1,
                "start_s": start,
                "end_s": end,
                "duration_s": end - start,
                "theme_label": seg.get("theme_label", f"Segment {i + 1}"),
                "summary": seg.get("summary", ""),
                "search_query": seg.get("search_query", seg.get("theme_label", "")),
            }
        )

    if not segments:
        duration = transcript.get("duration_s", 0.0)
        segments.append(
            {
                "index": 1,
                "start_s": 0.0,
                "end_s": duration,
                "duration_s": duration,
                "theme_label": "Full narration",
                "summary": article_text[:500] if article_text else "",
                "search_query": "historical illustration",
            }
        )

    return segments


def rank_candidates(
    segment_summary: str,
    search_query: str,
    candidates: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Use GPT-4o Vision to rank candidate images for a segment.

    Args:
        segment_summary: What the segment is about.
        search_query: The query used to find images.
        candidates: List of {"url": str, "title": str} dicts (thumbnail URLs).

    Returns: List of {"url": str, "relevance_score": float} sorted by score desc.
    """
    client = _get_client()
    if client is None or not candidates:
        return [{"url": c["url"], "relevance_score": 0.5} for c in candidates]

    try:
        content_parts: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    f"Segment summary: {segment_summary}\n"
                    f"Search query: {search_query}\n\n"
                    "Rate each image's relevance to the segment on a scale of 0.0 to 1.0. "
                    "Return JSON: {\"rankings\": [{\"index\": int, \"score\": float}]}"
                ),
            }
        ]
        for i, c in enumerate(candidates[:10]):
            content_parts.append(
                {"type": "image_url", "image_url": {"url": c["url"]}}
            )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": content_parts},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=500,
        )

        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        rankings = parsed.get("rankings", [])

        scored: list[dict[str, Any]] = []
        for r in rankings:
            idx = int(r.get("index", 0))
            if 0 <= idx < len(candidates):
                scored.append(
                    {
                        "url": candidates[idx]["url"],
                        "relevance_score": float(r.get("score", 0.5)),
                    }
                )

        if not scored:
            scored = [{"url": c["url"], "relevance_score": 0.5} for c in candidates]

        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored

    except Exception as exc:
        logger.warning("Vision ranking failed, using default scores: %s", exc)
        return [{"url": c["url"], "relevance_score": 0.5} for c in candidates]


def generate_image(prompt: str, style: str = "") -> bytes | None:
    """Generate an image via DALL-E 3 and return PNG bytes.

    Returns None if no API key or generation fails.
    """
    client = _get_client()
    if client is None:
        return None

    style_suffix = ""
    if style and style != "ai_judgement":
        style_map = {
            "classical_antiquity": "in the style of classical antiquity, marble fresco",
            "medieval": "in the style of medieval illuminated manuscripts",
            "renaissance": "in the style of Renaissance oil paintings",
            "modern": "in a modern photographic style",
        }
        style_suffix = f", {style_map.get(style, style)}"

    full_prompt = f"{prompt}{style_suffix}"

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1792x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        if not image_url:
            return None

        import httpx

        resp = httpx.get(image_url, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        logger.warning("DALL-E image generation failed: %s", exc)
        return None

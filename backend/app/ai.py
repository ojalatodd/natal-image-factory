"""AI helpers for transcription, segmentation, ranking, and image generation.

Supports multiple providers (OpenAI, Anthropic, Gemini, DeepSeek) for
text-based stages (segmentation, text ranking). Whisper transcription,
Vision-based image ranking, and DALL-E image generation are OpenAI-only.
All functions gracefully degrade when keys are missing.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from openai import OpenAI

from app.config import settings
from app.pipeline.adapters.base import HEADERS

logger = logging.getLogger("natal")

_client: OpenAI | None = None


def _safe_json_loads(text: str) -> dict[str, Any] | None:
    """Parse JSON from text that may be wrapped in markdown fences or prose."""
    import re

    # Strip markdown code fences: ```json\n...\n``` or ```\n...\n```
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    # Try to extract the first {...} block if surrounding prose
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        text = brace_match.group(0)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


@dataclass(frozen=True)
class AiModelConfig:
    provider: str
    model: str
    vision_model: str | None = None
    image_model: str | None = None


DEFAULT_AI_CONFIG = AiModelConfig(
    provider="openai",
    model="gpt-4o-mini",
    vision_model="gpt-4o",
    image_model="dall-e-3",
)


def _get_client() -> OpenAI | None:
    global _client
    if _client is not None:
        return _client
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — AI stages will use placeholder data")
        return None
    _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def _resolve_config(config: AiModelConfig | Any | None) -> AiModelConfig:
    if config is None:
        return DEFAULT_AI_CONFIG
    provider = getattr(config, "provider", DEFAULT_AI_CONFIG.provider)
    if hasattr(provider, "value"):
        provider = provider.value
    model = getattr(config, "model", DEFAULT_AI_CONFIG.model)
    vision_model = getattr(config, "vision_model", DEFAULT_AI_CONFIG.vision_model)
    image_model = getattr(config, "image_model", DEFAULT_AI_CONFIG.image_model)
    return AiModelConfig(
        provider=str(provider).lower(),
        model=str(model),
        vision_model=str(vision_model) if vision_model else None,
        image_model=str(image_model) if image_model else None,
    )


def _openai_json_chat(
    system_prompt: str,
    user_content: str,
    *,
    model: str,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any] | None:
    client = _get_client()
    if client is None:
        return None
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)


def _anthropic_json_chat(
    system_prompt: str,
    user_content: str,
    *,
    model: str,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any] | None:
    if not settings.anthropic_api_key:
        return None
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
    }
    resp = httpx.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    text = (data.get("content") or [{}])[0].get("text", "{}")
    return _safe_json_loads(text)


def _gemini_json_chat(
    system_prompt: str,
    user_content: str,
    *,
    model: str,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any] | None:
    if not settings.gemini_api_key:
        return None
    prompt = f"{system_prompt}\n\n{user_content}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.gemini_api_key}"
    )
    resp = httpx.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    text = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "{}")
    )
    return _safe_json_loads(text)


def _deepseek_json_chat(
    system_prompt: str,
    user_content: str,
    *,
    model: str,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any] | None:
    if not settings.deepseek_api_key:
        return None
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {settings.deepseek_api_key}"}
    payload["response_format"] = {"type": "json_object"}
    resp = httpx.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    return _safe_json_loads(text)


def _chat_json(
    config: AiModelConfig,
    system_prompt: str,
    user_content: str,
    *,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any] | None:
    provider = config.provider
    try:
        if provider == "openai":
            return _openai_json_chat(
                system_prompt,
                user_content,
                model=config.model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        if provider == "anthropic":
            return _anthropic_json_chat(
                system_prompt,
                user_content,
                model=config.model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        if provider == "gemini":
            return _gemini_json_chat(
                system_prompt,
                user_content,
                model=config.model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        if provider == "deepseek":
            return _deepseek_json_chat(
                system_prompt,
                user_content,
                model=config.model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
    except Exception as exc:
        logger.warning("AI provider %s failed: %s", provider, exc)

    # Fallback to OpenAI if configured
    if provider != "openai":
        try:
            return _openai_json_chat(
                system_prompt,
                user_content,
                model=DEFAULT_AI_CONFIG.model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            logger.warning("OpenAI fallback failed: %s", exc)
    return None


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.mp3") -> dict[str, Any]:
    """Transcribe audio via Whisper API and return word-level timeline.

    Returns: {"duration_s": float, "words": [{"word": str, "start_s": float, "end_s": float}]}
    """
    client = _get_client()
    if client is None:
        return {"duration_s": 0.0, "words": []}

    import io

    response = client.audio.transcriptions.create(
        file=(filename, io.BytesIO(audio_bytes)),
        model="whisper-1",
        response_format="verbose_json",
        timestamp_granularities=["word"],
    )

    words: list[dict[str, Any]] = []
    raw_words = getattr(response, "words", None) or []
    for w in raw_words:
        words.append(
            {
                "word": getattr(w, "word", "") or getattr(w, "text", ""),
                "start_s": float(getattr(w, "start", 0.0)),
                "end_s": float(getattr(w, "end", 0.0)),
            }
        )

    duration = float(getattr(response, "duration", 0.0))
    return {"duration_s": duration, "words": words}


_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at", "for",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "it", "its", "this", "that", "these", "those", "their", "them", "they", "he",
    "she", "his", "her", "we", "our", "you", "your", "i", "my", "me", "which",
    "who", "whom", "whose", "what", "when", "where", "why", "how", "all", "across",
    "into", "over", "under", "after", "before", "during", "while", "about",
}


def _derive_query_from_text(article_text: str, *, max_words: int = 6) -> str:
    """Extract a topical search query from article text as a fallback.

    Picks the most frequent meaningful (non-stopword) words, preserving the
    order of first appearance. Falls back to a generic term only when the
    text is empty.
    """
    if not article_text or not article_text.strip():
        return "historical archival footage"

    import re
    from collections import Counter

    tokens = re.findall(r"[A-Za-z][A-Za-z'-]+", article_text)
    meaningful = [t for t in tokens if t.lower() not in _STOPWORDS and len(t) > 2]
    if not meaningful:
        return "historical archival footage"

    # Rank by frequency, but keep first-seen order for ties/readability
    counts = Counter(t.lower() for t in meaningful)
    seen: dict[str, str] = {}
    for t in meaningful:
        seen.setdefault(t.lower(), t)
    top = sorted(seen.keys(), key=lambda w: (-counts[w], list(seen).index(w)))
    chosen = [seen[w] for w in top[:max_words]]
    return " ".join(chosen)


def _fallback_segment(article_text: str, duration: float) -> dict[str, Any]:
    """Build a single fallback segment spanning the full duration.

    The search query is derived from the article text so that even when AI
    segmentation fails, media search stays topical rather than generic.
    """
    return {
        "index": 1,
        "start_s": 0.0,
        "end_s": duration,
        "duration_s": duration,
        "theme_label": "Full narration",
        "summary": article_text[:500] if article_text else "",
        "search_query": _derive_query_from_text(article_text),
    }


def segment_text(
    article_text: str,
    transcript: dict[str, Any],
    *,
    ai_config: AiModelConfig | Any | None = None,
    target_segment_s: float = 30.0,
    max_segments: int = 40,
) -> list[dict[str, Any]]:
    """Split the narration into thematic segments using the selected AI provider.

    Returns: [{"index": int, "start_s": float, "end_s": float, "duration_s": float,
               "theme_label": str, "summary": str, "search_query": str}]
    """
    resolved = _resolve_config(ai_config)

    word_list = transcript.get("words", [])
    word_summary = " ".join([w["word"] for w in word_list[:200]])
    audio_duration_for_prompt = transcript.get("duration_s", 0.0)
    has_transcript = bool(word_list) and audio_duration_for_prompt and audio_duration_for_prompt > 0.0

    if has_transcript:
        system_prompt = (
            "You are a video editor assistant. Given an article and a narration transcript, "
            "split the narration into thematic segments. Each segment should be roughly "
            f"{target_segment_s} seconds long (but can vary based on content). "
            "For each segment, provide: start_s, end_s (in seconds from the audio), "
            "theme_label (short title), summary (1-2 sentences), and search_query "
            "(a specific, concrete query naming the key people, places, objects, or events "
            "in the segment so it finds relevant public-domain media — avoid generic terms "
            "like 'historical illustration'). "
            f"Return at most {max_segments} segments. "
            "Return JSON: {\"segments\": [{\"index\": int, \"start_s\": float, \"end_s\": float, "
            "\"theme_label\": str, \"summary\": str, \"search_query\": str}]}"
        )
        user_content = (
            f"ARTICLE TEXT:\n{article_text[:4000]}\n\n"
            f"TRANSCRIPT (first 200 words):\n{word_summary}\n\n"
            f"Audio duration: {audio_duration_for_prompt} seconds"
        )
    else:
        # No voiceover: segment the ARTICLE TEXT itself into thematic chapters.
        system_prompt = (
            "You are a video editor assistant. Given an article, split it into thematic "
            "segments suitable for accompanying b-roll, one chapter per distinct idea. "
            f"Aim for {target_segment_s}-second segments; produce multiple segments whenever "
            "the article covers more than one topic. Do NOT return an empty list. "
            "For each segment, provide theme_label (short title), summary (1-2 sentences), "
            "and search_query (a specific, concrete query naming the key people, places, "
            "objects, or events in the segment so it finds relevant public-domain media — "
            "avoid generic terms like 'historical illustration'). "
            "Do not include start_s/end_s; timing is assigned automatically. "
            f"Return at most {max_segments} segments. "
            "Return JSON: {\"segments\": [{\"index\": int, \"theme_label\": str, "
            "\"summary\": str, \"search_query\": str}]}"
        )
        user_content = f"ARTICLE TEXT:\n{article_text[:4000]}"

    parsed = _chat_json(
        resolved,
        system_prompt,
        user_content,
        temperature=0.3,
        max_tokens=800,
    )
    if not parsed:
        duration = transcript.get("duration_s", 0.0)
        if not duration or duration <= 0.0:
            duration = target_segment_s
        return [_fallback_segment(article_text, duration)]
    segments_raw = parsed.get("segments", [])

    # When there's no audio, the AI may return zero-duration segments.
    # Assign sequential default durations so Ken Burns and timestamps are meaningful.
    audio_duration = transcript.get("duration_s", 0.0)
    no_audio = not audio_duration or audio_duration <= 0.0

    segments: list[dict[str, Any]] = []
    for i, seg in enumerate(segments_raw):
        start = float(seg.get("start_s", 0.0))
        end = float(seg.get("end_s", start + target_segment_s))
        if no_audio:
            start = i * target_segment_s
            end = start + target_segment_s
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
        if no_audio:
            segments.append(_fallback_segment(article_text, target_segment_s))
        else:
            duration = transcript.get("duration_s", 0.0)
            segments.append(_fallback_segment(article_text, duration))

    return segments


def rank_candidates(
    segment_summary: str,
    search_query: str,
    candidates: list[dict[str, Any]],
    *,
    ai_config: AiModelConfig | Any | None = None,
) -> list[dict[str, Any]]:
    """Use GPT-4o Vision to rank candidate media for a segment.

    Args:
        segment_summary: What the segment is about.
        search_query: The query used to find images.
        candidates: List of {"url": str, "title": str, "media_type": str, "duration_s": float} dicts.
            media_type is "still" or "video". duration_s is the video length in seconds (if video).

    Returns: List of {"url": str, "relevance_score": float} sorted by score desc.
    """
    resolved = _resolve_config(ai_config)
    if not candidates:
        return []

    # Build a summary of which candidates are video vs still for the prompt
    type_summary = []
    for i, c in enumerate(candidates[:10]):
        mtype = c.get("media_type", "still")
        if mtype == "video":
            dur = c.get("duration_s")
            type_summary.append(f"  {i}: video ({dur:.0f}s)" if dur else f"  {i}: video")
        else:
            type_summary.append(f"  {i}: still")
    type_text = "\n".join(type_summary)

    # OpenAI vision path (best effort)
    if resolved.provider == "openai" and _get_client() is not None:
        try:
            content_parts: list[dict[str, Any]] = [
                {
                    "type": "text",
                    "text": (
                        f"Segment summary: {segment_summary}\n"
                        f"Search query: {search_query}\n\n"
                        f"Candidate media types:\n{type_text}\n\n"
                        "Rate each image's relevance to the segment on a scale of 0.0 to 1.0. "
                        "Consider whether motion (video) would enhance the segment — "
                        "give a slight boost to video candidates for segments involving "
                        "action, process, movement, or dynamic events. "
                        "Return JSON: {\"rankings\": [{\"index\": int, \"score\": float}]}"
                    ),
                }
            ]
            for i, c in enumerate(candidates[:10]):
                content_parts.append({"type": "image_url", "image_url": {"url": c["url"]}})

            response = _get_client().chat.completions.create(
                model=resolved.vision_model or resolved.model,
                messages=[{"role": "user", "content": content_parts}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=500,
            )

            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            rankings = parsed.get("rankings", [])
        except Exception as exc:
            logger.warning("Vision ranking failed, using text fallback: %s", exc)
            rankings = []
    else:
        rankings = []

    if not rankings:
        # Text-only fallback using selected provider
        list_text = "\n".join([
            f"{idx}: {c.get('title','')} ({c.get('media_type','still')}) ({c.get('url','')})"
            for idx, c in enumerate(candidates[:10])
        ])
        system_prompt = (
            "You rank media candidates for relevance to a video segment. "
            "Consider whether video (motion) would enhance the segment — "
            "boost video candidates for action, process, or movement segments. "
            "Return JSON only."
        )
        user_content = (
            f"Segment summary: {segment_summary}\n"
            f"Search query: {search_query}\n\n"
            f"Candidates:\n{list_text}\n\n"
            "Return JSON: {\"rankings\": [{\"index\": int, \"score\": float}]}"
        )
        parsed = _chat_json(resolved, system_prompt, user_content, temperature=0.2, max_tokens=300)
        rankings = (parsed or {}).get("rankings", [])

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


def decide_media_type(
    segment_summary: str,
    search_query: str,
    *,
    ai_config: AiModelConfig | Any | None = None,
) -> str:
    """Use AI to decide whether a segment is better served by still or video.

    Returns "still" or "video". Falls back to "still" when AI is unavailable.
    """
    resolved = _resolve_config(ai_config)

    system_prompt = (
        "You decide whether a video segment about the given topic is best "
        "served by a still image or a video clip. "
        "Choose 'video' for segments involving action, process, movement, "
        "dynamic events, or temporal change. "
        "Choose 'still' for segments about static subjects, portraits, "
        "documents, maps, or historical artifacts. "
        "Return JSON only: {\"media_type\": \"still\"} or {\"media_type\": \"video\"}"
    )
    user_content = (
        f"Segment summary: {segment_summary}\n"
        f"Search query: {search_query}\n\n"
        "Should this segment use a still image or a video clip?"
    )
    parsed = _chat_json(resolved, system_prompt, user_content, temperature=0.1, max_tokens=50)
    if parsed and parsed.get("media_type") in ("still", "video"):
        return parsed["media_type"]
    return "still"


def generate_image(prompt: str, style: str = "", *, ai_config: AiModelConfig | Any | None = None) -> bytes | None:
    """Generate an image (currently OpenAI DALL-E 3) and return PNG bytes.

    Returns None if provider is unavailable or generation fails.
    """
    resolved = _resolve_config(ai_config)

    # DALL-E is OpenAI-only; fall back to OpenAI if another provider is selected
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
    model = resolved.image_model or DEFAULT_AI_CONFIG.image_model or "dall-e-3"

    try:
        response = client.images.generate(
            model=model,
            prompt=full_prompt,
            size="1792x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        if not image_url:
            return None

        resp = httpx.get(image_url, timeout=60, follow_redirects=True, headers=HEADERS)
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        logger.warning("DALL-E image generation failed: %s", exc)
        return None


def suggest_project_name(
    article_text: str,
    *,
    ai_config: AiModelConfig | Any | None = None,
) -> str:
    """Suggest a project name derived from the article text content.

    Returns a concise, evocative title based on the article. Falls back to a
    timestamp-based name if no AI provider is configured or the call fails.
    """
    from datetime import datetime

    resolved = _resolve_config(ai_config)

    system_prompt = (
        "You generate short, evocative project names for documentary-style video projects "
        "based on article content. Names should be 3–8 words and sound like a documentary "
        "episode title. Return JSON only."
    )
    user_content = (
        f"Article excerpt:\n{article_text[:1000]}\n\n"
        "Based on this content, suggest one project name. "
        'Return JSON: {"name": "..."}'
    )

    try:
        parsed = _chat_json(resolved, system_prompt, user_content, temperature=0.7, max_tokens=60)
        name = (parsed or {}).get("name", "").strip()
        if name:
            return name
    except Exception as exc:
        logger.debug("suggest_project_name failed: %s", exc)

    return f"Project {datetime.now().strftime('%b %d %H:%M')}"

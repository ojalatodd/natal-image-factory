# Pipeline Stages

Six stages in `backend/app/pipeline/stages.py`, orchestrated by `run_pipeline` in `backend/app/tasks.py`. All stages have real implementations as of Phase 1. AI stages gracefully degrade when `OPENAI_API_KEY` is not set.

## Stage 1: Transcribe & Align (Whisper)

- **Input**: `project.source_audio_key` (Spaces object key for uploaded audio)
- **Output**: `{"duration_s": float, "words": [{"word": str, "start_s": float, "end_s": float}]}`
- **Implementation**: Downloads audio from Spaces, calls `transcribe_audio()` in `backend/app/ai.py` which uses OpenAI Whisper API with `response_format="verbose_json"` and `timestamp_granularities=["word"]`. Updates `project.audio_duration_s` with measured duration.
- **Fallback**: Returns `{"duration_s": 0.0, "words": []}` if no API key or no audio uploaded.

## Stage 2: Semantic Segmentation (GPT-4o)

- **Input**: Transcript dict + `project.source_text_key` (article text loaded from Spaces)
- **Output**: List of `Segment` records with `index`, `start_s`, `end_s`, `duration_s`, `theme_label`, `summary`, `search_query`
- **Implementation**: Calls `segment_text()` in `backend/app/ai.py` which sends article text + transcript to GPT-4o with a system prompt asking for thematic segments (~30s each, max 40). Uses JSON response format. Clears old segments on re-runs.
- **Fallback**: Creates a single placeholder segment covering full duration.

## Stage 3: Media Search (Stills + Video)

- **Input**: Segments with `search_query` + project `media_mix` and `visual_style`
- **Output**: `Asset` records (candidates) per segment
- **Implementation**: Queries registered source adapters based on `media_mix` policy. Each adapter's `search()` is called via `asyncio.run()` with the segment's search query and visual style. Creates `Asset` DB records for each candidate. Clears old assets on re-runs.
- **Adapters**: Wikimedia Commons, Library of Congress, Internet Archive (all stills, all public APIs, no key required).
- **Media mix enforcement**: `stills` → only still adapters; `video` → only video adapters; `balanced` → both; `ai_judgement` → stills only (Phase 1).

## Stage 4: Rank & Match (GPT-4o Vision)

- **Input**: Segments with candidate Assets (thumbnail URLs)
- **Output**: Sets `chosen_media_type` and `chosen_asset_id` on each Segment, `is_chosen` and `relevance_score` on Asset
- **Implementation**: Calls `rank_candidates()` in `backend/app/ai.py` which sends thumbnail URLs to GPT-4o Vision with the segment summary and search query. GPT-4o returns relevance scores (0.0-1.0). Maps scores back to assets by URL, picks highest-scored asset.
- **Fallback**: Assigns default score 0.5 to all candidates, picks first.

## Stage 5: Acquire, Trim & Normalize

- **Input**: Segments with chosen Assets
- **Output**: Downloaded/processed media in Spaces, `Asset.status = processed`
- **Implementation (stills)**: `_process_still()` downloads the image via the source adapter's `fetch()` method or direct `httpx.get()`. Normalizes with Pillow (`image_to_bytes()` — resize to max 1920x1080, convert to JPEG at 90% quality). Generates thumbnail (`thumbnail_to_bytes()` — 400px wide). Uploads both to Spaces. Updates `asset.spaces_key`, `asset.thumbnail_key`, `asset.width`, `asset.height`.
- **Video**: Deferred to Phase 3. Sets `Asset.status = failed` for video assets.

## Stage 6: Package ZIP + Manifest

- **Input**: Segments with processed Assets
- **Output**: Spaces key for the output ZIP
- **Implementation**: Builds ZIP in memory with `zipfile.ZipFile`. For each segment with a processed chosen asset, downloads the media from Spaces and adds it as a numbered file (`01.jpg`, `02.jpg`, ...). Writes `manifest.txt` with tab-separated columns: filename, timestamp range, theme label, source, license, attribution. Uploads ZIP to Spaces at `output/project_{id}.zip`.

## Progress Percentages

| Stage | Start % | End % |
|-------|---------|-------|
| Transcribe | 10 | 25 |
| Segment | 30 | 45 |
| Search | 50 | 60 |
| Rank | 65 | 75 |
| Process | 80 | 90 |
| Package | 95 | 100 |

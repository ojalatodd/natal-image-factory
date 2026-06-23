# Pipeline Stages

Six stages in `backend/app/pipeline/stages.py`, orchestrated by `run_pipeline` in `backend/app/tasks.py`.

## Stage 1: Transcribe & Align (Whisper)

```python
def transcribe(db: Session, project: Project) -> dict
```
- **Input**: `project.source_audio_key` (Spaces object key for uploaded audio)
- **Output**: `{"duration_s": float, "words": [{"word": str, "start_s": float, "end_s": float}]}`
- **Phase 0**: Returns placeholder with `words: []` and `duration_s` from project.
- **Phase 1**: Call OpenAI Whisper API on the audio file, parse word-level timestamps.

## Stage 2: Semantic Segmentation (GPT-4o)

```python
def segment(db: Session, project: Project, transcript: dict) -> list[Segment]
```
- **Input**: Transcript dict + `project.source_text_key` (article text)
- **Output**: List of `Segment` records with `index`, `start_s`, `end_s`, `duration_s`, `theme_label`, `summary`, `search_query`
- **Phase 0**: Creates one placeholder segment covering full duration.
- **Phase 1**: Send article text + transcript to GPT-4o, parse thematic breakpoints, create Segment records.

## Stage 3: Media Search (Stills + Video)

```python
def search_media(db: Session, project: Project, segments: list[Segment]) -> None
```
- **Input**: Segments with `search_query` + project `media_mix` and `visual_style`
- **Output**: `Asset` records (candidates) per segment
- **Phase 0**: No-op.
- **Phase 1**: Query still image adapters (Wikimedia, Flickr Commons, Internet Archive) per segment.
- **Phase 3**: Add video adapters (Pexels, Internet Archive video). Enforce media_mix policy.

## Stage 4: Rank & Match (GPT-4o Vision)

```python
def rank_match(db: Session, project: Project, segments: list[Segment]) -> None
```
- **Input**: Segments with candidate Assets (thumbnails)
- **Output**: Sets `chosen_media_type` and `chosen_asset_id` on each Segment, `is_chosen` on Asset
- **Phase 0**: Sets `chosen_media_type = still` on all segments.
- **Phase 1**: GPT-4o Vision scores candidate thumbnails against segment summary. Select best per segment.

## Stage 5: Acquire, Trim & Normalize (ffmpeg)

```python
def acquire_process(db: Session, project: Project, segments: list[Segment]) -> None
```
- **Input**: Segments with chosen Assets
- **Output**: Downloaded/processed media in Spaces, `Asset.status = processed`
- **Phase 0**: No-op.
- **Phase 1**: Download chosen stills, normalize (resize, format conversion), upload to Spaces.
- **Phase 3**: Trim video clips to segment duration, normalize codec/resolution, apply Ken Burns to stills.

## Stage 6: Package ZIP + Manifest

```python
def package(db: Session, project: Project, segments: list[Segment]) -> str
```
- **Input**: Segments with processed Assets
- **Output**: Spaces key for the output ZIP
- **Phase 0**: Returns placeholder key `output/project_{id}.zip`.
- **Phase 1**: Build numbered media files (`01.jpg`, `02.mp4`, ...), write `manifest.txt` with timestamp mappings and attributions, zip everything, upload to Spaces.

## Progress Percentages

| Stage | Start % | End % |
|-------|---------|-------|
| Transcribe | 10 | 25 |
| Segment | 30 | 45 |
| Search | 50 | 60 |
| Rank | 65 | 75 |
| Process | 80 | 90 |
| Package | 95 | 100 |

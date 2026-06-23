# Pipeline Summary

The pipeline is the core processing engine of the Natal Image Factory. It transforms uploaded article text + voiceover audio into a packaged ZIP of matched media with a manifest.

## Data Flow

```mermaid
graph LR
    A[Audio + Text] --> B[Stage 1: Transcribe]
    B --> C[Stage 2: Segment]
    C --> D[Stage 3: Search Media]
    D --> E[Stage 4: Rank & Match]
    E --> F[Stage 5: Acquire & Process]
    F --> G[Stage 6: Package ZIP]
    G --> H[Output: ZIP + manifest.txt]
```

## Orchestration

- Celery task `run_pipeline` in `backend/app/tasks.py` calls stages sequentially.
- Each stage updates progress via `progress.publish()` (Redis pub/sub + Job table).
- Stages receive a SQLAlchemy session and the Project (and Segments where relevant).
- All stages are independently testable.

## Current State (Phase 0)

All six stages exist as safe stubs:
- Stage 1 returns `{"duration_s": ..., "words": []}` (no real transcription).
- Stage 2 creates a single placeholder segment covering the full duration.
- Stages 3-5 are no-ops (wired but deferred).
- Stage 6 returns a placeholder ZIP key.

See: [stages.md](stages.md), [adapters.md](adapters.md)

# Terminology

Domain language used throughout the Natal Image Factory codebase and lode.

- **B-roll** — Supplemental video or image footage intercut with the main narration to illustrate the topic.
- **Segment** — A thematic section of the narration, produced by AI semantic segmentation. Each segment has a start/end timestamp, theme label, summary, and search query.
- **Asset** — A candidate media item (still image or video clip) discovered by a source adapter for a given segment. Assets have relevance scores, licensing info, and processing status.
- **Media Mix** — User preference for the ratio of stills vs. video in the output. Options: `stills`, `video`, `balanced`, `ai_judgement`.
- **Visual Style** — User preference for the aesthetic tone of searched media (e.g., "Classical Antiquity", "Medieval", "ai_judgement").
- **Source Adapter** — A pluggable module that implements the `SourceAdapter` protocol to search a specific public-domain media repository (Wikimedia, Internet Archive, etc.) and return `CandidateAsset` results.
- **Pipeline** — The six-stage processing flow: transcribe → segment → search → rank → acquire/process → package.
- **Manifest** — A text file (`manifest.txt`) included in the output ZIP that maps each numbered media file to its timestamp range and source attribution.
- **Ken Burns** — A motion effect applied to still images (slow pan/zoom) to simulate video. Implemented via ffmpeg filters.
- **Lode** — The structured markdown knowledge base at `lode/` that serves as the AI's persistent project memory.
- **Spaces** — DigitalOcean Spaces Object Storage (S3-compatible). Used in production for media storage. Locally replaced by MinIO.
- **Bootstrap User** — The initial admin user created on first startup from `BOOTSTRAP_USER_EMAIL` / `BOOTSTRAP_USER_PASSWORD` env vars.
- **Progress Channel** — Redis pub/sub channel (`progress:{project_id}`) used to stream pipeline progress updates to the frontend via WebSocket.

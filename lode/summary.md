# Natal Image Factory — Project Summary

Natal Image Factory is a web application that transforms article text and voiceover audio into visually rich video b-roll packages for podcasters and writers (originally built for Daniel Natal of the Daniel Natal Show). Users upload an article and an audio narration file. The system uses AI to transcribe the audio, semantically segment the narration into thematic chapters, search public-domain image and video sources for matching media, rank and select the best candidates, trim/normalize video clips via ffmpeg, and package everything into a downloadable ZIP with numbered media files and a `manifest.txt` mapping each file to its timestamp range.

The system supports a user-configurable media mix (primarily stills, primarily video, balanced, or AI-judged), visual style preferences (e.g., Classical Antiquity, Medieval), optional AI-generated images, and optional AI-applied motion to stills (Ken Burns effect). Source adapters are pluggable — each public-domain source (Wikimedia Commons, Flickr Commons, Internet Archive, Pexels, etc.) implements a common protocol.

**Current state:** Phase 0 scaffold complete. The full Docker Compose stack (Caddy, FastAPI, Celery worker, Redis, MinIO) builds and runs locally. Auth, project CRUD, file uploads, and pipeline orchestration stubs are wired. All six pipeline stages exist as safe stubs that produce placeholder data. Real AI transcription, segmentation, media search, and ffmpeg processing are deferred to Phase 1+.

**Deployment target:** DigitalOcean Droplet ($12/mo) + Spaces ($5/mo) = ~$17/mo infrastructure. AI API costs are separate ($0.20–$1.00 per project).

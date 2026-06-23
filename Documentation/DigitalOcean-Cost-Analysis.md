# Natal Image Factory — DigitalOcean Product Cost Analysis

**Prepared June 2026**

---

## Workload Profile

Before comparing products, here's what the application actually does at runtime:

| Characteristic | Detail |
|---|---|
| **Users** | Single user (the client), possibly 1–3 concurrent sessions max |
| **Traffic pattern** | Bursty — active during a production session, idle the rest of the time |
| **Upload sizes** | Text: < 1 MB; Audio: 50–300 MB per voiceover |
| **AI processing** | Calls to external LLM APIs (e.g., OpenAI) for segmentation — not local GPU inference |
| **Image search** | Outbound HTTP to museum/archive APIs — I/O-bound, low CPU |
| **Image download + ZIP** | Brief burst of downloads (10–30 images), then zip packaging |
| **Database needs** | Minimal — projects, settings, user preferences (dozens of rows, not millions) |
| **Storage needs** | Moderate — uploaded audio, fetched images, generated ZIPs; most are transient |

**Key insight:** This is a low-traffic, single-user, bursty workload. The system will spend the vast majority of its time idle. Cost-effectiveness means minimizing the idle-time bill while having enough headroom to handle a processing run comfortably.

---

## Options Evaluated

### Option A — Single Droplet + Docker Compose ⭐ RECOMMENDED

Run everything on one virtual machine using Docker Compose: the web server, the background processing worker, and an embedded database (SQLite).

| Component | Product | Monthly Cost |
|---|---|---|
| Compute | **Droplet** — 2 GiB RAM / 1 vCPU / 50 GiB SSD | **$12.00** |
| File storage | **Spaces** — 250 GiB included, built-in CDN | **$5.00** |
| Database | **SQLite** (embedded, runs on the Droplet) | **$0.00** |
| Domain/SSL | Let's Encrypt (free) via Caddy or nginx | **$0.00** |
| **Total** | | **$17.00/mo** |

**Pros:**
- Lowest possible cost for a production-ready setup
- Fully predictable monthly bill — no per-request or per-second surprises
- Complete control over the environment (install any library, any runtime)
- Docker Compose means it's already containerized and portable to any host
- SQLite is more than sufficient for a single-user app (it handles millions of rows; you'll have dozens)
- Spaces handles the heavy file storage (audio uploads, image downloads, ZIP output) so the Droplet SSD isn't overwhelmed
- Included bandwidth: 2,000 GiB/mo on the Droplet + 1,024 GiB/mo on Spaces — vastly more than needed

**Cons:**
- You manage the server: OS updates, Docker updates, backups (mitigated by automated scripts and DO's snapshot backups at $2.40/mo)
- No auto-scaling (irrelevant for a single-user app)

**Scale-up path:** If the workload grows, you can resize the Droplet in-place (e.g., to 4 GiB / 2 vCPU for $24/mo) with a few clicks.

---

### Option B — App Platform (Managed PaaS)

DigitalOcean's fully managed platform. Push code to Git, it builds and deploys automatically.

| Component | Product | Monthly Cost |
|---|---|---|
| Web container | **App Platform** — 1 vCPU / 1 GiB | **$12.00** |
| Worker container | **App Platform** — 1 vCPU / 1 GiB (background jobs) | **$12.00** |
| Database | **Dev Database** (512 MiB, managed) | **$7.00** |
| File storage | **Spaces** — 250 GiB | **$5.00** |
| **Total** | | **$36.00/mo** |

Upgrading to a managed PostgreSQL instead of the dev database pushes this to **$44.15/mo**.

**Pros:**
- Zero server management — managed builds, deploys, SSL, health checks
- Git-push deployment workflow

**Cons:**
- **2× the cost** of Option A for an equivalent workload
- Two separate containers needed (web + worker) because App Platform's web containers are designed for request/response, not long-running background jobs
- Dev database has no backups, no HA, and limited to 512 MiB — upgrading to managed PostgreSQL adds $15.15/mo
- Less control over installed system packages (relevant for audio processing libraries like ffmpeg)
- App Platform containers have limited filesystem — still need Spaces for file storage

---

### Option C — DigitalOcean Kubernetes (DOKS)

Managed Kubernetes cluster with containerized microservices.

| Component | Product | Monthly Cost |
|---|---|---|
| Worker nodes | **2× Basic nodes** (minimum recommended) — 2 GiB each | **$24.00** |
| Load balancer | Required for ingress | **$12.00** |
| Database | **Managed PostgreSQL** — 1 GiB | **$15.15** |
| File storage | **Spaces** — 250 GiB | **$5.00** |
| **Total** | | **$56.15/mo** |

**Pros:**
- Industry-standard orchestration, great for multi-service architectures
- Auto-scaling, self-healing pods, rolling deployments

**Cons:**
- **3× the cost** of Option A
- Massive overkill for a single-user application
- Kubernetes operational complexity is unjustified for this workload
- Free control plane, but you pay for minimum 2 worker nodes (DigitalOcean recommends 2 to avoid downtime during upgrades)

---

### Option D — Serverless Functions + App Platform Hybrid

Use App Platform for the web UI; offload processing to DigitalOcean Functions.

| Component | Product | Monthly Cost |
|---|---|---|
| Web UI | **App Platform** — 1 vCPU / 512 MiB | **$5.00** |
| Processing | **Functions** — within free tier for low volume | **$0.00** |
| Database | **Dev Database** | **$7.00** |
| File storage | **Spaces** | **$5.00** |
| **Total** | | **$17.00/mo** |

Looks attractive on paper, but critical problems:

**Cons:**
- Functions have a **15-minute maximum timeout** — audio segmentation of long voiceovers may exceed this
- Functions have a **1 GB maximum memory** — may be tight for processing large audio files
- Functions have a **1 MB maximum response size** — cannot return a ZIP of images
- Functions have a **48 MB maximum deployment size** — audio/AI libraries (whisper, etc.) may exceed this
- Requires splitting the processing pipeline into multiple chained function calls with intermediate storage — significant architectural complexity
- Debugging and local development is harder with serverless

**Verdict:** The hard limits on timeout, memory, and package size make Functions a poor fit for audio-processing workloads.

---

## Side-by-Side Comparison

| Factor | A: Droplet ⭐ | B: App Platform | C: Kubernetes | D: Functions Hybrid |
|---|---|---|---|---|
| **Monthly cost** | **$17** | $36–$44 | $56+ | $17 (but limited) |
| **Management effort** | Moderate | Low | High | Medium |
| **Fits the workload** | ✅ Perfectly | ✅ Adequate | ❌ Overkill | ⚠️ Hard limits |
| **Audio processing** | ✅ Full control | ⚠️ Limited packages | ✅ Full control | ❌ 15-min timeout |
| **Portability** | ✅ Docker Compose | ⚠️ Vendor-tied | ✅ Standard K8s | ❌ DO-specific |
| **Scale-up path** | Resize Droplet | Add containers | Add nodes | N/A |
| **Idle cost** | $17/mo fixed | $36/mo fixed | $56/mo fixed | ~$5/mo (web only) |

---

## Recommendation: Option A — Single Droplet + Spaces

For a single-user, bursty workload like Natal Image Factory, **a $12 Droplet + $5 Spaces subscription is the clear winner** at **$17/month**.

### Recommended Starting Configuration

```
Droplet:   2 GiB RAM  /  1 vCPU  /  50 GiB SSD  /  2 TiB transfer    $12/mo
Spaces:    250 GiB storage  /  1 TiB CDN transfer                      $5/mo
Backups:   Weekly automated Droplet snapshots (optional)               ~$2.40/mo
─────────────────────────────────────────────────────────────────────────────
Total                                                            $17–$19.40/mo
```

### Why This Works

1. **Docker Compose on the Droplet** — the web app, background worker (Celery/Bull/etc.), and SQLite all run in containers. This is the exact same Docker setup that would run on Kubernetes, App Platform, or AWS — maximum portability.
2. **Spaces for files** — uploaded audio, fetched images, and generated ZIPs go into S3-compatible object storage. This keeps the Droplet SSD clean and gives you CDN-backed download links.
3. **SQLite for data** — for a single-user app with simple relational data (projects, settings, segments), SQLite outperforms managed PostgreSQL at zero cost. If multi-user support is ever needed, migrating to PostgreSQL is straightforward.
4. **2 GiB RAM is comfortable** — the web server uses ~100 MB; the worker uses ~300–500 MB during processing; the rest is available for audio analysis and image operations.

### When to Upgrade

| Trigger | Action | New Cost |
|---|---|---|
| Processing feels slow | Resize Droplet to 4 GiB / 2 vCPU | $24/mo + $5 Spaces = $29/mo |
| Multiple concurrent users | Add managed PostgreSQL, keep Droplet | $12 + $15.15 + $5 = ~$32/mo |
| High-availability needed | Move to App Platform or DOKS | $36–$56/mo |

---

## External API Costs (Not DigitalOcean)

These costs exist regardless of which DO product you choose:

| Service | Estimated Cost | Notes |
|---|---|---|
| **OpenAI API** (GPT-4o for segmentation) | ~$0.02–$0.10 per article | Text analysis of a few thousand words |
| **OpenAI Whisper API** (audio timestamps) | ~$0.006/minute of audio | A 30-min voiceover ≈ $0.18 |
| **AI image generation** (optional, DALL-E / Stable Diffusion) | ~$0.02–$0.08 per image | Only when no public-domain match is found |
| **Estimated per-project total** | **$0.20–$1.00** | Depends on article length and AI image usage |

---

*Natal Image Factory · DigitalOcean Cost Analysis · June 2026*

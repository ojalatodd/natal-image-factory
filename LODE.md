# Lode Coding — Natal Image Factory

This repository uses the [Lode Coding method](https://fjzeit.github.io/lode) for AI-assisted development.

## What is a Lode?

A **lode** is a structured set of markdown files in `lode/` that serves as the AI assistant's persistent project memory. It describes the **current state** of the system — architecture, terminology, patterns, invariants, and decisions that matter — so every new AI session starts with context instead of from scratch.

The term comes from mining: a lode is a rich vein of valuable ore. Here, the valuable material is project knowledge.

## Quick Start

### With Windsurf / Cascade

1. **Read the system prompt**: The Lode Coding system prompt is at `prompts/SystemPrompt.txt`. Paste its contents into your session or reference it when starting a new conversation.

2. **Or use the workflow**: A Windsurf workflow is available at `.windsurf/workflows/lode.md` — run `/lode` to start a Lode Coding session.

3. **The AI will automatically**:
   - Read `lode/lode-map.md`, `lode/terminology.md`, and `lode/summary.md` at session start
   - Check the lode before exploring code
   - Update lode files after code changes
   - Suggest capturing designs in the lode before implementing

### With Claude Code

```bash
claude/lode.ps1        # PowerShell (Windows)
claude/lode            # Unix
```

### With GitHub Copilot

Copy `prompts/SystemPrompt.txt` to your agent configuration, or use the Copilot agent file from the [upstream lode repo](https://github.com/fjzeit/lode).

## Lode Structure

```
lode/
├── summary.md              # Project snapshot (read this first)
├── terminology.md          # Domain language glossary
├── practices.md            # Patterns, conventions, constraints
├── lode-map.md             # Hierarchical index of all lode files
├── plans/
│   └── roadmap.md          # Phase roadmap
├── backend/                # FastAPI, SQLAlchemy, Celery
│   ├── summary.md
│   ├── architecture.md
│   ├── models.md
│   ├── auth.md
│   ├── storage.md
│   └── celery.md
├── frontend/               # React, Vite, Tailwind
│   ├── summary.md
│   └── architecture.md
├── pipeline/               # Six-stage processing pipeline
│   ├── summary.md
│   ├── stages.md
│   └── adapters.md
├── infrastructure/         # Docker, Caddy, deployment
│   ├── summary.md
│   ├── docker-compose.md
│   └── deployment.md
└── tmp/                    # Git-ignored session scraps
```

## Rules

1. **The human owns the code.** The AI is the memory and high-speed executor.
2. **Lode describes current state**, not changelog history. Write "The API client retries..." not "Added retry logic on...".
3. **One topic per file.** Keep files under 250 lines; decompose if larger.
4. **Mermaid diagrams only** (not SVG) in lode files.
5. **Update the lode after code changes** — before moving to the next task.
6. **Session scraps go in `lode/tmp/`** (git-ignored). Only permanent knowledge goes in main lode files.
7. **Check `lode/lode-map.md` first** before exploring the codebase.

## Workflow

1. **Seed**: AI reads relevant lode files at session start.
2. **Chat**: Discuss the problem and design before writing code.
3. **Decide**: Align on the approach.
4. **Implement**: AI writes code; human reviews.
5. **Capture**: AI updates the lode to reflect the new reality.
6. **Verify**: Lode structure mirrors the codebase.

## License

The Lode Coding method and system prompt are MIT licensed by [fj zeit](https://github.com/fjzeit/lode). The Natal Image Factory lode content is part of this repository.

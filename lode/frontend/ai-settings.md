# AI Settings UI

The AI Settings page allows a user to choose which AI provider and model to use globally across all pipeline stages. This configuration affects segmentation (Stage 2), ranking (Stage 4), and image generation fallback (Stage 3 when enabled).

## Route

- URL: `/settings/ai`
- Component: `frontend/src/pages/AiSettings.tsx`

## Behavior

- Loads current settings from `GET /settings/ai` and initializes the form.
- Allows selecting:
  - Provider (OpenAI, Anthropic, Gemini, DeepSeek)
  - Text model (segmentation, text ranking fallback)
  - Vision model (image ranking when OpenAI is selected)
  - Image model (DALL-E model; only when provider supports images)
- Saving uses `PUT /settings/ai`.

## Fallbacks

- If a provider is missing an API key, the backend will fall back to OpenAI (if configured) or placeholder data.
- If a provider does not support image generation, DALL-E is used when available.

## Related files

- `frontend/src/api.ts` — `getAiSettings`, `updateAiSettings`
- `backend/app/routers/ai_settings.py` — settings API
- `backend/app/ai.py` — provider abstraction and fallbacks

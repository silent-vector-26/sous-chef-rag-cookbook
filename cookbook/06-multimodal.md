# 06 · Multimodal: fridge photo → ingredients

**Serves:** 1 · **Difficulty:** ★★☆ · **Code:** `llm.describe_image_ingredients`, UI uploader

## Method
1. Send the photo as a base64 `image_url` to a vision-capable deployment (gpt-4o-mini).
2. Ask for JSON `{"ingredients": [...]}` listing only what is clearly visible.
3. Normalize and feed straight into `cook_with(have=...)` — the rest of the pipeline is unchanged.

## Taste test
Run with `BACKEND=azure`, upload a fridge photo in the "Cook with what I have" tab.

## Chef's notes
Treat vision output as a suggestion: show the detected list and let the user edit it before searching.

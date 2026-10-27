# 06 · Multimodal: fridge photo → ingredients

**Serves:** 1 · **Difficulty:** ★★☆ · **Code:** `llm.describe_image_ingredients`, UI uploader

## Method
1. Send the photo as a base64 `image_url` to a vision-capable deployment (gpt-5.4-mini).
2. Ask for JSON `{"ingredients": [...]}` listing only what is clearly visible.
3. Normalize and feed straight into `cook_with(have=...)` — the rest of the pipeline is unchanged.

## Taste test
Run with `BACKEND=azure`, upload a fridge photo in the "Cook with what I have" tab.

## Chef's notes
The UI shows the detected list after searching. Editing/confirming that list before retrieval is a recommended extension, not a feature currently implemented. When a photo is attached, detections replace the typed/chip pantry rather than being merged.

Treat vision output as a suggestion, not a reliable inventory or allergy check. The image call is not screened by the text-only `check_input` path. Offline-generated card photographs are separate bundled assets; they are not generated from user uploads.

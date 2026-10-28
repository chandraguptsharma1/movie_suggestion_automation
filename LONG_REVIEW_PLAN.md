# Seven-movie long review: implementation proposal

Status: project inspected; long-video mode is proposed, not implemented or rendered yet.

## First sample lineup

Existing completed projects provide seven prepared movies, source trailers, verified scenes, posters and metadata:

| Project | Movie |
| --- | --- |
| 32 | Migration |
| 33 | No Hard Feelings |
| 34 | Cocaine Bear |
| 35 | 65 |
| 36 | Wish |
| 37 | Plane |
| 38 | Rebel Moon – Part One: A Child of Fire |

Use a themed introduction such as seven Hollywood movies for different moods. Do not describe this mixed list as the seven highest-rated movies or fabricate a ranking. An alternative curated thematic lineup can replace it before production.

## Editorial format

- Landscape 1920x1080, target 8–10 minutes, Hindi narration.
- A 15–20 second opening previews the variety without showing every movie's best moment.
- Seven roughly 60–75 second reviews: hook; spoiler-free premise; supported strengths; supported caveat; intended audience; short verdict. The final duration follows the measured narration.
- A brief movie-name/year/poster card introduces each section, with varied trailer footage underneath. Show ratings only when a real source/value exists and label that source.
- Use clean cuts, occasional short transitions, selective slow motion, large keyword reveals, lower-third titles and readable captions. Keep the source's landscape framing, using source files rather than stretching existing Shorts exports.
- One voice identity and a consistent music bed with gentle speech ducking. Music credits remain in the description. Do not assume a music-volume slider gives the same perceived loudness on every track.
- A short closing compares viewing moods and invites a relevant comment. Include a chapter timestamp list derived from actual segment timings.
- Separate 16:9 thumbnail with 2–3 prominent posters, a clear seven-movie message, and minimal readable text. Avoid squeezing all seven full posters into tiny tiles.

## Current constraints found in code

- `backend/app/services/script_service.py` requests a 50–60 second Shorts script even for multiple movies.
- `backend/app/services/auto_pilot_service.py` accepts multiple movies but produces a Shorts collage and vertical composition; its cinematic engine is selected for single-movie projects.
- `backend/app/services/video_composer_service.py` currently composes the main output as a vertical Short, with short-specific ending-card behavior.
- `backend/app/services/processing_queue_service.py` creates one cinematic movie per job.
- `backend/app/services/publishing_automation_service.py` intentionally rejects more than one selected movie.

## Proposed changes

1. Add an explicit `long_review` format to project data with an ordered seven-movie lineup. Preserve the existing single-movie Shorts workflow.
2. Generate and validate an outline per movie using metadata, audience reviews and verified scene evidence. Avoid unsupported factual claims, fabricated scores and language implying a firsthand viewing.
3. Generate narration per section and measure it, caching each section so retries resume without repeating completed synthesis.
4. Map each section only to footage belonging to that movie. Select enough diverse scene material for the longer narration; acquire or analyze additional permitted trailers when necessary. Fail clearly when a movie lacks usable footage.
5. Render bounded landscape segments and concatenate them, then mix narration/music and captions on a timeline built from real durations. Keep memory bounded and make completed segment renders reusable.
6. Generate chapters and credits from the same timeline and source data. Create the separate landscape thumbnail.
7. Extend local job tracking and publishing eligibility for long reviews. Use long-video metadata and thumbnail handling, private upload, actual Studio checks and the existing next available 18:30 IST scheduling rule. Do not upload/schedule a sample during design exploration.

## Validation before delivery

Check each movie's footage identity and boundaries, narration/scene synchronization, duration totals, chapter start positions, caption readability, landscape framing, audio balance, exported file decode, and thumbnail readability. Check resume behavior after a failed segment. Treat actual Studio copyright results as the release gate; a local render cannot establish copyright clearance.

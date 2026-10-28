# Cinematic Review

Open a single-movie lineup in Shorts Studio. Prepare trailers, Gemini scenes and a thumbnail, then choose **Create cinematic version**. A separate lineup appears in My Lineups; the original video remains available. Repeated clicks reuse the same cinematic job. If a render fails or the backend restarts, start from the original lineup again to resume with cached narration.

The mode creates a short hook, setup, tension, evidence-based strengths, a viewer-preference caveat and a verdict. It selects only existing Gemini-analysed scenes, measures each Sarvam narration beat, and aligns cuts to video frames. Hindi phrase captions have estimated timings within each measured beat; they are not forced-aligned word timestamps. Wider establishing shots alternate with closer action shots and gentle push-ins. Music uses the saved level (default 35%) with narration ducking. Quiet synthesized accents mark selected beat changes. The final two seconds retain the poster thumbnail.

Generation rejects unavailable scene IDs, Latin text in spoken narration, missing review sections and streaming-platform claims. Generated opinions and scene relevance should still be reviewed. The mode uses the supplied premise and trailer evidence; it does not claim the model watched the full film.

Artifacts are saved in `backend/storage/final_videos/project_<id>/cinematic/`: story plan, individual voice beats, clean narration, accented narration and ASS captions. The finished export is `cinematic_review.mp4` in the parent project folder. The normal compose endpoint retains cinematic captions; changing the voice duration requires a new matching cinematic timeline.

Selected hook, strength and verdict shots play at 0.75× speed while narration stays at its original speed. Short dip-to-black transitions mark story-beat changes without shortening the timeline. Three animated centre-screen reveals accompany the hook, first tension beat and verdict. A subtle contrast/saturation grade and vignette finish the footage. These are edits to real trailer footage; the mode does not generate new video footage with a generative-video model.

This feature creates a local export. YouTube upload, copyright checks, Shorts-cover verification and scheduling remain separate steps.

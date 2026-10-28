# Automatic YouTube publishing

Movie selection creates a single-movie processing job. A completed render is enrolled in the persistent publishing queue without opening the upload page. The upload page also enrolls an existing finished movie once, using its current metadata. Default review audience: not made for kids; category: Entertainment. These defaults describe the movie review's intended audience, not whether the source movie is animated.

The backend must remain running. Its `publishing-automation` worker persists state in the project's SQLite database, uploads privately, resumes known resumable sessions, sets the ending-image thumbnail, and rechecks processing/restrictions. Uploads are serialized. An uncertain upload result never triggers a new upload. Network/account errors back off to 15 minutes. Restarting the backend preserves the jobs.

The Codex heartbeat **YouTube upload aur copyright monitor** runs in this chat every 10 minutes. Codex and the signed-in Reely Bee Chrome session must remain available. The monitor uses the computer-use skill to inspect Studio; API processing success does not establish copyright clearance. Observe the exact video ID, completed copyright checks/no issues, and the actual displayed cover. A dash in the content table or `hasCustomThumbnail=true` alone is insufficient. Compare against the expected ending JPEG. If the channel supports Studio custom Shorts thumbnails, set/save and verify it there. If the required cover control is mobile-only or unavailable, leave thumbnail verification pending and report the actionable blocker. Never invent successful verification.

## Local API

- `GET /api/publishing-automation`: enrolled projects and their state, next check, observations.
- `GET /api/publishing-automation/{project_id}`: `{automation: ...}`.
- `POST /api/publishing-automation/{project_id}`: enroll once; optional existing UploadRequest metadata body. A repeated request does not overwrite an upload or create a duplicate.
- `GET /api/youtube-upload/{project_id}`: actual upload state, exact video ID, Studio URL.
- `GET /api/youtube-upload/{project_id}/thumbnail`: expected ending-frame JPEG.
- `POST /api/publishing-automation/{project_id}/studio-evidence`: submit actual fresh UI observations only:

```json
{
  "video_id": "exact-video-id",
  "observed_at": "2026-10-25T09:00:00+00:00",
  "copyright_status": "clear",
  "checks_complete": true,
  "thumbnail_matches": true,
  "details": "Describe the visible checks result and the actual cover comparison."
}
```

Allowed copyright states: clear, pending, claim, blocked, unknown. The timestamp must include a timezone and be within 10 minutes. Do not post the example unchanged. Claims and blocks are held, even when the claim would allow monetized playback. Unknown/pending results do not schedule. A new negative Studio observation cancels an enrolled video's future scheduled release and holds it privately; it does not dispute/remove claims. Failure to cancel retries rather than claiming it succeeded. Already published videos are reported, not silently withdrawn.

Fresh clear evidence must match the exact video ID and the current thumbnail revision. The backend refreshes processing/restrictions and recomputes the channel's next free day at **18:30 Asia/Kolkata** immediately before scheduling. It confirms YouTube returned that schedule. The monitor continues checking enrolled scheduled/published videos for later claims. A new claim after publication is reported; no guarantee is made against later claims.

Stay quiet while monitoring unchanged/non-actionable state. Notify on a completed verified schedule/publication, a new claim/block, failure, or an actionable browser/login/thumbnail blocker. Do not repeatedly notify unchanged failures. Use the supported browser/computer tools, never private Studio endpoints or credential extraction.

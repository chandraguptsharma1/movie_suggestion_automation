# YouTube upload in Movie Suggestion Automation

Open **Step 8: YouTube Upload** after composing the final Short. This feature uses this project's SQLite records and final MP4, including the 2-second ending thumbnail and saved music credits.

## Connect the account

The Google OAuth client configuration from the existing movie-review setup was copied into `backend/.youtube_private/client_secret.json`. The old expired token was not copied. This private directory is outside the public `/storage` mount and is ignored by Git.

1. Start the backend and frontend normally. Install updated backend requirements if using a new environment: `python -m pip install -r requirements.txt`.
2. In Step 8, click **Connect YouTube**, then authorize the intended channel in Google's window. No password is entered into this app.
3. The existing client registers `http://localhost:3000`. During connection, the backend temporarily listens on that loopback port, handles the state/PKCE-protected callback, and closes the listener after successful authorization. The app itself can stay on port 3001.
4. If another app occupies port 3000, stop that app or configure a different registered callback. The backend route is `http://localhost:8001/api/youtube/oauth/callback`; register that exact URI in Google Cloud and set `YOUTUBE_OAUTH_REDIRECT_URI` to match, then restart the backend. Do not change redirect configuration during an active login.
5. If Google reports the app is in testing, add the channel owner's Google account as an OAuth test user in Google Cloud. YouTube Data API v3 must be enabled in that Google project.

## Upload and thumbnail

Edit title, description and tags, select the audience, and click **Upload privately + auto thumbnail**. Saved music attribution is automatically retained even if the description is edited. The backend validates the file and ending-card metadata, snapshots the exact exported video, and uploads it in resumable chunks. Refreshing the page does not start another upload.

After YouTube returns a video ID, the backend extracts an image 0.8 seconds before the snapshot ends and calls `thumbnails.set`. The image comes from the ending card of the uploaded MP4. Thumbnail errors are separate from upload errors: use **Apply latest project thumbnail** without uploading the MP4 again. YouTube account eligibility and Shorts thumbnail behavior can differ; verify the displayed thumbnail in YouTube. If needed, select the ending frame in the mobile YouTube app and confirm the thumbnail step in this app.

Thumbnail Studio now offers **Poster Spotlight** (large uncropped poster) and **Cinema Cover** (edge-to-edge poster and title), alongside Classic Collage. **Update video ending with this design** replaces the local ending card without stacking another two seconds. Changing a design preserves the old ending metadata and upload preflight requires updating the ending before a new upload.

For an existing upload, **Apply latest project thumbnail** sends the current project design without reuploading the video. It cannot replace video frames already stored on YouTube. The Upload tab shows the image sent and the thumbnail preview returned by YouTube. API acceptance and `hasCustomThumbnail` do not prove that the Shorts cover matches; the thumbnail display checkbox is required even after API success. In the YouTube mobile app, use Your videos → Short → Edit → thumbnail pencil → choose the ending frame → Done / Save. Eligible channels can upload custom Shorts thumbnails from desktop Studio. See [YouTube's current thumbnail instructions](https://support.google.com/youtube/answer/72431?hl=en-GB).

## Copyright and publication

Refresh **processing & restrictions** to retrieve the API-visible upload, rejection, processing, and region-restriction information. These checks do not return the complete Content ID/Studio Checks report and never mark the video copyright-safe.

Open the linked Studio page and review Checks/Copyright. The app keeps the video private until processing succeeds, no API-visible restriction is reported, and you explicitly confirm both Studio copyright review and the displayed Shorts thumbnail. Then choose **Schedule next slot · 6:30 PM IST**. Claims can arise later; a successful processing result is not copyright clearance.

Scheduling is fixed to **18:30 Asia/Kolkata (13:00 UTC)**, one release per date. The backend reads all pages of the connected channel's uploads playlist and retrieves owner-visible video dates and `status.publishAt`, including private and scheduled videos. It excludes the current video. The chosen date is later than the channel's latest uploaded/published/scheduled date and is never before today's next future 18:30 slot. For example, an existing 25 October schedule yields 26 October at 18:30. When all prior dates are in the past, today at 18:30 is available until the cutoff; after the cutoff, tomorrow is used.

The UI shows a read-only next-slot preview. On scheduling, the channel queue is read again under a shared scheduling lock, and locally confirmed schedules cover remote indexing delay. Repeating a confirmed schedule keeps that video's existing 18:30 slot. Queue/API errors stop scheduling; there is no guessed-date fallback. Manual timestamps and immediate publication are disabled. A successful response must confirm the exact requested timestamp and private visibility.

## Recovery and storage

- A video ID is saved before thumbnail work. Retrying a thumbnail cannot create a duplicate upload.
- Interrupted transfers can resume their existing Google upload session. If the outcome is uncertain and no session URL was saved, the app asks you to inspect Studio instead of uploading another copy.
- The HTTP transport uses Google's `build_http()` so HTTP 308 reaches the resumable-upload client as **Resume Incomplete**, rather than being followed as a redirect. API errors retain their HTTP status and JSON reason without exposing raw upload-session responses.
- One managed upload is tracked per project. Reopening it shows the existing upload; it does not publish a newly rendered version automatically.
- Run a single backend worker. Active upload coordination and the callback listener are process-local. Do not delete upload jobs to resolve an uncertain transfer.
- Tokens, OAuth state/PKCE data, video snapshots and upload-session URLs stay in `backend/.youtube_private/`. Upload-session URLs and private filesystem paths are omitted from API responses. Do not place this directory under `STORAGE_DIR`.
- Account actions are restricted to the local app; unrelated browser origins and LAN clients cannot use the saved token.

## Verified

On 2026-10-24 the connected Reely Bee channel's existing Runner transfer resumed successfully to 100% after fixing HTTP 308 handling. YouTube accepted the ending-frame thumbnail and reported `hasCustomThumbnail: true`. The video remains private for Studio copyright review; no publication was performed.

Backend tests: `python -m pytest tests -q`. Frontend: `npm run build`.

Official references: [resumable uploads](https://developers.google.com/youtube/data/guides/using_resumable_upload_protocol), [thumbnail setting](https://developers.google.com/youtube/data/reference/rest/v3/thumbnails/set), [video status and restrictions](https://developers.google.com/youtube/data/reference/rest/v3/videos), [OAuth](https://developers.google.com/identity/protocols/oauth2/web-server).

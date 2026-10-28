"""OAuth credentials stay outside the publicly served media directory."""
import base64
import hashlib
import json
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.config import settings

SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']


class YouTubeOAuthService:
    def __init__(self, root=None):
        self.root = Path(root or settings.youtube_private_dir)
        if self.root.resolve().is_relative_to(settings.storage_path.resolve()):
            raise ValueError('YouTube credentials must be outside the public storage directory.')
        self.client_secret_path = self.root / 'client_secret.json'
        self.token_path = self.root / 'youtube_token.json'
        self._lock = threading.RLock()
        self._listener = None

    def _write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(data), encoding='utf-8')
        temporary.chmod(0o600)
        temporary.replace(path)

    def config(self):
        if not self.client_secret_path.is_file():
            raise ValueError('Google OAuth client JSON setup is required on this backend.')
        data = json.loads(self.client_secret_path.read_text('utf-8'))
        return data.get('web') or data.get('installed') or {}

    def redirect_uri(self):
        return settings.youtube_redirect_uri or (self.config().get('redirect_uris') or [
            f'http://localhost:{settings.port}/api/youtube/oauth/callback'])[0]

    def begin(self, project_id, origin):
        parsed = urlsplit(origin)
        if parsed.scheme not in ('http', 'https') or parsed.hostname not in ('localhost', '127.0.0.1'):
            raise ValueError('Connect YouTube from the local application browser.')
        config = self.config()
        redirect = self.redirect_uri()
        self._ensure_listener(redirect)
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        with self._lock:
            self._write(self.root / f'oauth_{state}.json', {'verifier': verifier, 'expires': time.time() + 600,
                'origin': origin, 'redirect_uri': redirect, 'project_id': project_id})
        return {'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
            'client_id': config['client_id'], 'redirect_uri': redirect, 'response_type': 'code',
            'scope': ' '.join(SCOPES), 'access_type': 'offline', 'prompt': 'consent',
            'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256'}),
            'redirect_uri': redirect}

    def complete(self, code, state):
        if not state or len(state) > 128 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in state):
            raise ValueError('Invalid OAuth state. Start Connect YouTube again.')
        with self._lock:
            path = self.root / f'oauth_{state}.json'
            if not path.is_file():
                raise ValueError('OAuth request missing/used. Start Connect YouTube again.')
            pending = json.loads(path.read_text('utf-8'))
            path.unlink()
            if pending['expires'] < time.time():
                raise ValueError('OAuth request expired. Start Connect YouTube again.')
            if not code:
                raise ValueError('YouTube consent was not completed.')
            config = self.config()
            response = requests.post('https://oauth2.googleapis.com/token', data={
                'code': code, 'client_id': config['client_id'], 'client_secret': config['client_secret'],
                'redirect_uri': pending['redirect_uri'], 'grant_type': 'authorization_code',
                'code_verifier': pending['verifier']}, timeout=30)
            token = response.json()
            if not response.ok or token.get('error'):
                raise ValueError('Google authorization failed. Reconnect and check the configured redirect URI.')
            refresh = token.get('refresh_token')
            if not refresh:
                raise ValueError('Google did not grant offline access. Revoke the old app grant, then reconnect.')
            self._write(self.token_path, {'token': token['access_token'], 'refresh_token': refresh,
                'client_id': config['client_id'], 'client_secret': config['client_secret'],
                'token_uri': 'https://oauth2.googleapis.com/token', 'scopes': token.get('scope', ' '.join(SCOPES)).split(),
                'expiry': (datetime.now(timezone.utc) + timedelta(seconds=token.get('expires_in', 3600))).isoformat().replace('+00:00', 'Z')})
            return pending['origin']

    def get_credentials(self):
        with self._lock:
            if not self.token_path.is_file():
                return None
            data = json.loads(self.token_path.read_text('utf-8'))
            creds = Credentials.from_authorized_user_info(data)
            if not creds.valid and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    raise ValueError('YouTube authorization expired/revoked. Connect YouTube again.') from None
                self._write(self.token_path, json.loads(creds.to_json()))
            return creds

    def disconnect(self):
        with self._lock:
            self.token_path.unlink(missing_ok=True)

    def _ensure_listener(self, redirect):
        """Reuse an existing registered loopback URI without changing Google Cloud settings."""
        target = urlsplit(redirect)
        if target.hostname not in ('localhost', '127.0.0.1') or target.port == settings.port:
            return  # The backend callback route handles configured hosted/backend URLs.
        if target.scheme != 'http' or not target.port:
            raise ValueError('Use an HTTP loopback callback or the backend OAuth callback URL.')
        with self._lock:
            if self._listener:
                return
            service = self
            class Callback(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass  # Authorization codes must never appear in access logs.

                def do_GET(self):
                    request = urlsplit(self.path)
                    if request.path.rstrip('/') != target.path.rstrip('/'):
                        self.send_error(404)
                        return
                    query = parse_qs(request.query)
                    try:
                        origin = service.complete(query.get('code', [''])[0], query.get('state', [''])[0])
                        html = service.callback_html(origin)
                        status = 200
                    except ValueError:
                        html, status = '<p>Connection failed or cancelled. Close this window and try Connect YouTube again.</p>', 400
                    self.send_response(status)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Referrer-Policy', 'no-referrer')
                    self.end_headers()
                    self.wfile.write(html.encode())
                    if status == 200:
                        def stop():
                            server.shutdown()
                            server.server_close()
                            with service._lock:
                                service._listener = None
                        threading.Thread(target=stop, daemon=True).start()
            try:
                server = HTTPServer((target.hostname, target.port), Callback)
            except OSError:
                raise ValueError(f'Callback port {target.port} is occupied. Stop the other app on this port, or configure a registered backend callback URI.') from None
            self._listener = server
            threading.Thread(target=server.serve_forever, name='youtube-oauth-callback', daemon=True).start()

    @staticmethod
    def callback_html(origin):
        return ('<!doctype html><meta name="referrer" content="no-referrer"><title>YouTube connected</title>'
                '<p>YouTube connected. You can close this window and return to the Shorts app.</p><script>'
                'history.replaceState({},"",location.pathname);'
                f'if(window.opener) window.opener.postMessage({{type:"youtube-connected"}},{json.dumps(origin)});'
                'window.close();</script>')


youtube_oauth_service = YouTubeOAuthService()

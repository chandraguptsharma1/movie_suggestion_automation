import base64
import hashlib
import json
import time
import socket
import requests
import logging
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest

from app.config import settings
from app.services.youtube_oauth_service import YouTubeOAuthService


@pytest.fixture
def oauth(tmp_path, monkeypatch):
    service = YouTubeOAuthService(tmp_path / 'private')
    service.root.mkdir()
    service.client_secret_path.write_text(json.dumps({'web': {'client_id': 'client', 'client_secret': 'test-secret',
        'redirect_uris': ['http://localhost:3000']}}))
    monkeypatch.setattr(settings, 'youtube_redirect_uri', '')
    monkeypatch.setattr(service, '_ensure_listener', Mock())
    return service


def test_connect_uses_expiring_state_and_pkce(oauth):
    reply = oauth.begin(14, 'http://localhost:3001')
    query = parse_qs(urlsplit(reply['auth_url']).query)
    state = query['state'][0]
    data = json.loads((oauth.root / f'oauth_{state}.json').read_text())
    digest = base64.urlsafe_b64encode(hashlib.sha256(data['verifier'].encode()).digest()).rstrip(b'=').decode()
    assert query['code_challenge'] == [digest]
    assert data['expires'] > time.time()
    assert 'test-secret' not in reply['auth_url']


def test_callback_is_single_use_and_tokens_stay_private(oauth, monkeypatch):
    query = parse_qs(urlsplit(oauth.begin(14, 'http://localhost:3001')['auth_url']).query)
    post = Mock(return_value=Mock(ok=True, json=lambda: {'access_token': 'private-access', 'refresh_token': 'private-refresh', 'expires_in': 3600}))
    monkeypatch.setattr('app.services.youtube_oauth_service.requests.post', post)
    assert oauth.complete('code', query['state'][0]) == 'http://localhost:3001'
    assert post.call_args.kwargs['data']['code_verifier']
    assert oauth.token_path.is_file()
    assert oauth.get_credentials().token == 'private-access'
    with pytest.raises(ValueError, match='missing/used'):
        oauth.complete('code', query['state'][0])


def test_invalid_or_expired_state_never_exchanges_tokens(oauth, monkeypatch):
    post = Mock()
    monkeypatch.setattr('app.services.youtube_oauth_service.requests.post', post)
    with pytest.raises(ValueError, match='Invalid'):
        oauth.complete('code', '../secret')
    query = parse_qs(urlsplit(oauth.begin(14, 'http://localhost:3001')['auth_url']).query)
    path = oauth.root / f"oauth_{query['state'][0]}.json"
    data = json.loads(path.read_text()); data['expires'] = 0; path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='expired'):
        oauth.complete('code', query['state'][0])
    post.assert_not_called()


def test_private_tokens_cannot_be_placed_under_served_storage():
    with pytest.raises(ValueError, match='outside'):
        YouTubeOAuthService(settings.storage_path / 'private')


def test_non_local_login_origin_rejected(oauth):
    with pytest.raises(ValueError, match='local'):
        oauth.begin(14, 'https://unrelated.example')


def test_registered_loopback_callback_returns_to_app(tmp_path, monkeypatch):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    service = YouTubeOAuthService(tmp_path / 'bridge')
    monkeypatch.setattr(service, 'complete', lambda code, state: 'http://localhost:3001')
    service._ensure_listener(f'http://127.0.0.1:{port}')
    try:
        result = requests.get(f'http://127.0.0.1:{port}/?code=private-code&state=nonce', timeout=5)
        assert result.status_code == 200
        assert 'youtube-connected' in result.text
        assert 'private-code' not in result.text
        assert result.headers['Cache-Control'] == 'no-store'
    finally:
        if service._listener:
            service._listener.shutdown()
            service._listener.server_close()


def test_callback_code_is_redacted_from_access_log():
    from app.routes.youtube_oauth_routes import RedactOAuthCallback
    record = logging.LogRecord('uvicorn.access', logging.INFO, '', 0, '%s %s %s %s %s',
        ('127.0.0.1', 'GET', '/api/youtube/oauth/callback?code=private-code&state=nonce', '1.1', 200), None)
    RedactOAuthCallback().filter(record)
    assert 'private-code' not in record.getMessage()

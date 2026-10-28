from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import youtube_upload_routes as routes


def client(monkeypatch):
    service = Mock()
    service._error_message.side_effect = lambda exc: str(exc)
    monkeypatch.setattr(routes, 'service', service)
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app), service


def test_account_route_precedes_movie_id_route(monkeypatch):
    api, service = client(monkeypatch)
    service.account.return_value = {'is_authenticated': False}
    assert api.get('/youtube-upload/account').json() == {'is_authenticated': False}


def test_upload_requires_audience_and_rejects_invalid_metadata(monkeypatch):
    api, service = client(monkeypatch)
    assert api.post('/youtube-upload/7', json={'title': 'Review'}).status_code == 422
    service.start.assert_not_called()
    service.start.return_value = {'movie_id': 7, 'state': 'PREPARING'}
    response = api.post('/youtube-upload/7', json={'title': 'Review', 'made_for_kids': False})
    assert response.status_code == 200
    assert service.start.call_args.args[1]['made_for_kids'] is False


def test_publish_review_is_forwarded_and_errors_are_visible(monkeypatch):
    api, service = client(monkeypatch)
    service.publish.side_effect = ValueError('Copyright review required')
    response = api.post('/youtube-upload/7/publish', json={})
    assert response.status_code == 400
    assert 'Copyright' in response.json()['detail']
    assert service.publish.call_args.args == (7, False, None, False)


def test_unrelated_website_cannot_use_the_local_upload_token(monkeypatch):
    api, service = client(monkeypatch)
    response = api.post('/youtube-upload/7', headers={'Origin': 'https://unrelated.example'},
                        json={'title': 'Review', 'made_for_kids': False})
    assert response.status_code == 403
    service.start.assert_not_called()

from unittest.mock import Mock

import pytest
import requests

from app.services import tmdb_service as module
from app.services.tmdb_service import TMDBService


@pytest.fixture(autouse=True)
def isolate_trailer_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(module.settings, 'storage_dir', str(tmp_path / 'storage'))


def response(videos, status=200):
    res = Mock(status_code=status)
    res.json.return_value = {"results": videos}
    if status >= 400:
        res.raise_for_status.side_effect = requests.HTTPError("sensitive URL")
    return res


def video(key, kind="Trailer", official=True):
    return {"key": key, "site": "YouTube", "type": kind, "official": official}


def test_language_fallback_filters_non_trailers_and_sorts(monkeypatch):
    get = Mock(side_effect=[response([video("feature", "Featurette")]), response([
        video("teaser", "Teaser"), video("trailer", official=False), video("official"), video("official"),
    ])])
    monkeypatch.setattr(module.requests, "get", get)
    trailers = TMDBService().fetch_videos(1, strict=True)
    assert [t["key"] for t in trailers] == ["official", "trailer", "teaser"]
    assert get.call_args.kwargs["params"]["language"] == "hi-IN"


def test_transient_connection_is_retried(monkeypatch):
    get = Mock(side_effect=[requests.ConnectionError("reset"), response([video("ok")])])
    monkeypatch.setattr(module.requests, "get", get)
    monkeypatch.setattr(module.time, "sleep", Mock())
    assert TMDBService().fetch_videos(1, strict=True)[0]["key"] == "ok"
    assert get.call_count == 2


def test_strict_failure_is_not_mistaken_for_empty_results(monkeypatch):
    get = Mock(side_effect=requests.ConnectionError("reset"))
    monkeypatch.setattr(module.requests, "get", get)
    monkeypatch.setattr(module.time, "sleep", Mock())
    with pytest.raises(RuntimeError, match="connection failed after 6 attempts"):
        TMDBService().fetch_videos(1, strict=True)
    assert get.call_count == 6


def test_auth_failure_has_safe_error_and_is_not_retried(monkeypatch):
    get = Mock(return_value=response([], 401))
    monkeypatch.setattr(module.requests, "get", get)
    with pytest.raises(RuntimeError, match="HTTP 401") as exc:
        TMDBService().fetch_videos(1, strict=True)
    assert "sensitive URL" not in str(exc.value)
    assert get.call_count == 1


def test_empty_results_are_not_an_api_failure(monkeypatch):
    monkeypatch.setattr(module.requests, "get", Mock(return_value=response([])))
    assert TMDBService().fetch_videos(1, strict=True) == []


def test_connection_failure_tries_alternate_language(monkeypatch):
    get = Mock(side_effect=[requests.ConnectionError('reset'), requests.ConnectionError('reset'), response([video('ok')])])
    monkeypatch.setattr(module.requests, 'get', get)
    monkeypatch.setattr(module.time, 'sleep', Mock())
    assert TMDBService().fetch_videos(1, strict=True)[0]['key'] == 'ok'
    assert get.call_args.kwargs['params']['language'] == 'hi-IN'


def test_saved_trailer_links_survive_service_restart_and_network_outage(monkeypatch):
    monkeypatch.setattr(module.requests, 'get', Mock(return_value=response([video('saved')])) )
    assert TMDBService().fetch_videos(1, strict=True)[0]['key'] == 'saved'
    monkeypatch.setattr(module.requests, 'get', Mock(side_effect=requests.ConnectionError('secret URL')))
    monkeypatch.setattr(module.time, 'sleep', Mock())
    assert TMDBService().fetch_videos(1, strict=True)[0]['key'] == 'saved'
    with pytest.raises(RuntimeError):
        TMDBService().fetch_videos(2, strict=True)


def test_live_empty_collection_does_not_reuse_old_links(monkeypatch):
    service = TMDBService()
    monkeypatch.setattr(module.requests, 'get', Mock(return_value=response([video('old')])))
    service.fetch_videos(1, strict=True)
    monkeypatch.setattr(module.requests, 'get', Mock(return_value=response([])))
    assert service.fetch_videos(1, strict=True) == []


def test_old_or_corrupt_cache_is_not_used(monkeypatch):
    import json
    service = TMDBService()
    path = service._video_cache_path(1, 'movie')
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'tmdb_id': 1, 'media_type': 'movie', 'saved_at': 0, 'trailers': []}))
    monkeypatch.setattr(module.requests, 'get', Mock(side_effect=requests.Timeout()))
    monkeypatch.setattr(module.time, 'sleep', Mock())
    with pytest.raises(RuntimeError):
        service.fetch_videos(1, strict=True)
    path.write_text('corrupt json')
    with pytest.raises(RuntimeError):
        service.fetch_videos(1, strict=True)


def test_malformed_video_list_reports_error_without_crashing(monkeypatch):
    monkeypatch.setattr(module.requests, 'get', Mock(return_value=response('not a video list')))
    with pytest.raises(RuntimeError, match='invalid response'):
        TMDBService().fetch_videos(1, strict=True)

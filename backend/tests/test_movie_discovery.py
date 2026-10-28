from unittest.mock import Mock

import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services import tmdb_service as module
from app.routes import suggestion_routes as routes


def response(items, pages=1):
    result = Mock()
    result.json.return_value = {'results': items, 'total_pages': pages, 'total_results': len(items)}
    return result


def movie(index=1, genres=None):
    return {'id': index, 'title': f'Movie {index}', 'release_date': '2025-02-12', 'genre_ids': genres or [53]}


def test_year_and_category_are_sent_to_tmdb(monkeypatch):
    request = Mock(return_value=response([movie()]))
    monkeypatch.setattr(module.requests, 'get', request)
    result = module.TMDBService().browse_movies(year=2025, genre_id=53, sort_by='vote_average.desc')
    params = request.call_args.kwargs['params']
    assert params['primary_release_year'] == 2025
    assert params['with_genres'] == 53
    assert params['vote_count.gte'] == 100
    assert not params['include_adult']
    assert result['results'][0]['genres'] == ['Thriller']


def test_name_with_genre_scans_pages_without_losing_pagination(monkeypatch):
    request = Mock(side_effect=[response([movie(1, [35])], 3), response([movie(2)], 3), response([movie(3)], 3)])
    monkeypatch.setattr(module.requests, 'get', request)
    result = module.TMDBService().browse_movies(query='Movie', year=2025, genre_id=53)
    assert [item['tmdb_id'] for item in result['results']] == [2, 3]
    assert result['total_results'] is None and result['next_page'] is None
    assert request.call_args.kwargs['params']['primary_release_year'] == 2025
    assert '/search/movie' in request.call_args.args[0]


def test_bounded_search_returns_next_unscanned_page(monkeypatch):
    request = Mock(return_value=response([movie(1, [35])], 20))
    monkeypatch.setattr(module.requests, 'get', request)
    result = module.TMDBService().browse_movies(query='Movie', genre_id=53)
    assert result['next_page'] == 6
    assert result['results'] == []
    assert request.call_count == 5


def test_error_is_not_misreported_as_no_matches(monkeypatch):
    monkeypatch.setattr(module.requests, 'get', Mock(side_effect=requests.ConnectionError('private connection info')))
    with pytest.raises(RuntimeError, match='unavailable'):
        module.TMDBService().browse_movies()


def test_existing_modal_name_search_still_returns_movies(monkeypatch):
    monkeypatch.setattr(module.requests, 'get', Mock(return_value=response([movie()])))
    assert module.TMDBService().search_multi('Movie', 'movie')[0]['tmdb_id'] == 1


def test_routes_validate_year_genre_and_sort(monkeypatch):
    app = FastAPI()
    app.include_router(routes.router)
    api = TestClient(app)
    assert api.get('/suggestions/discover?year=1500').status_code == 422
    assert api.get('/suggestions/discover?sort_by=unsafe').status_code == 422
    assert api.get('/suggestions/discover?genre_id=999999').status_code == 400
    assert any(item['name'] == 'Thriller' for item in api.get('/suggestions/movie-genres').json())

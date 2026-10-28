from fastapi import APIRouter, HTTPException, Request, Depends
import logging
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.database import project_repo
from app.services.youtube_oauth_service import youtube_oauth_service as oauth
from app.routes.youtube_security import require_local_request

router = APIRouter(prefix='/youtube/oauth', tags=['YouTube account'], dependencies=[Depends(require_local_request)])


class RedactOAuthCallback(logging.Filter):
    def filter(self, record):
        if isinstance(record.args, tuple) and len(record.args) == 5:
            args = list(record.args)
            if '/youtube/oauth/callback?' in str(args[2]):
                args[2] = str(args[2]).split('?', 1)[0]
                record.args = tuple(args)
        return True


logging.getLogger('uvicorn.access').addFilter(RedactOAuthCallback())


class ConnectRequest(BaseModel):
    project_id: int


@router.post('/start')
def start(payload: ConnectRequest, request: Request):
    if not project_repo.get_by_id(payload.project_id):
        raise HTTPException(status_code=404, detail='Project not found')
    try:
        return oauth.begin(payload.project_id, request.headers.get('origin') or 'http://localhost:3001')
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/callback', response_class=HTMLResponse)
def callback(code: str = '', state: str = ''):
    try:
        origin = oauth.complete(code, state)
        return HTMLResponse(oauth.callback_html(origin), headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})
    except ValueError as exc:
        return HTMLResponse('<p>Connection failed. Close this window and reconnect from the Upload tab.</p>', status_code=400)


@router.post('/disconnect')
def disconnect():
    oauth.disconnect()
    return {'success': True}

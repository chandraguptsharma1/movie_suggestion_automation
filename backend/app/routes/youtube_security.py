from urllib.parse import urlsplit
from fastapi import HTTPException, Request


def require_local_request(request: Request):
    """The local account token must not authorize requests from unrelated websites/LAN clients."""
    if request.client and request.client.host not in ('127.0.0.1', '::1', 'localhost', 'testclient'):
        raise HTTPException(status_code=403, detail='Use YouTube upload from the local application.')
    origin = request.headers.get('origin')
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in ('http', 'https') or parsed.hostname not in ('localhost', '127.0.0.1'):
            raise HTTPException(status_code=403, detail='Untrusted YouTube request origin.')

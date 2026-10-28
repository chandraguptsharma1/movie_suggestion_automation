from pathlib import Path
from unittest.mock import Mock

import pytest

from app.services import trailer_downloader_service as module
from app.services.trailer_downloader_service import TrailerDownloaderService


def test_download_uses_default_clients_and_enables_node(tmp_path, monkeypatch):
    monkeypatch.setattr(module.settings, 'storage_dir', str(tmp_path))
    monkeypatch.setattr(module.shutil, 'which', lambda _: 'node.exe')
    monkeypatch.delenv('YOUTUBE_COOKIES', raising=False)
    options = {}

    def make_downloader(opts):
        options.update(opts)
        downloader = Mock()
        downloader.__enter__ = Mock(return_value=downloader)
        downloader.__exit__ = Mock(return_value=False)
        downloader.download.side_effect = lambda _: Path(opts['outtmpl']).write_bytes(b'x' * 2000)
        return downloader

    monkeypatch.setattr(module.yt_dlp, 'YoutubeDL', make_downloader)
    result = TrailerDownloaderService().download_trailer('https://www.youtube.com/watch?v=test', 1, 'Runner')
    assert result['success']
    assert 'extractor_args' not in options
    assert options['js_runtimes'] == {'node': {'path': 'node.exe'}}
    assert options['retries'] > 0


def test_download_does_not_accept_missing_output(tmp_path, monkeypatch):
    monkeypatch.setattr(module.settings, 'storage_dir', str(tmp_path))
    downloader = Mock()
    downloader.__enter__ = Mock(return_value=downloader)
    downloader.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(module.yt_dlp, 'YoutubeDL', Mock(return_value=downloader))
    with pytest.raises(RuntimeError, match='usable video file'):
        TrailerDownloaderService().download_trailer('https://www.youtube.com/watch?v=test', 1, 'Runner')

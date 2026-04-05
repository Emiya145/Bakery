"""
Serve the built Vite/React SPA (production). Dev uses Vite dev server on :5173.
"""
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


def _index_path():
    return Path(settings.BASE_DIR) / 'frontend' / 'dist' / 'index.html'


_RESERVED_PREFIXES = frozenset({'api', 'admin', 'static', 'media', 'api-auth'})


def spa_index(request, path=''):
    """Return index.html for client-side routes; assets are under /static/ after collectstatic."""
    first = (path or '').split('/')[0] if path else ''
    if first in _RESERVED_PREFIXES:
        raise Http404()

    index = _index_path()
    if not index.is_file():
        return HttpResponse(
            'Frontend not built. Run: cd frontend && npm ci && npm run build',
            status=503,
            content_type='text/plain',
        )
    return FileResponse(index.open('rb'), content_type='text/html; charset=utf-8')

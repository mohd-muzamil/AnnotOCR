from app import create_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

flask_app = create_app()

# Fallback app for requests not under /annotation to prevent NoneType error
def fallback_app(environ, start_response):
    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return [b'404 Not Found']

app = DispatcherMiddleware(fallback_app, {
    '/annotation': flask_app
})

import eventlet
from eventlet import wsgi
from app import apicalls

app = apicalls()
wsgi.server(eventlet.list(("127.0.0.1", 5000), app))

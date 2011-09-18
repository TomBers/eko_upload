import webapp2

from webapp2_extras import jinja2, sessions
from google.appengine.api import users
from data import Kiosk, SyncSession
from google.appengine.ext import db
import logging

from handlers.BaseHandler import BaseHandler
from handlers.KioskHandlers import RegKiosksHandler, ListKiosksHandler
from handlers.RPCHandlers import RPCHeartbeatHandler

class HomePageHandler(BaseHandler):
    def get(self):
        user = users.get_current_user()
        ctx = self.get_ctx(user)
        self.render_response('main.html', **ctx)

config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'le9c3jc0dkiwidocsiameses',
}

app = webapp2.WSGIApplication([
    ('/', HomePageHandler),
    ('/kiosks', ListKiosksHandler),
    ('/kiosks/register', RegKiosksHandler),
    ('/kiosks/<kiosk_id>', ListKiosksHandler),
    ('/kiosks/<kiosk_id>/edit', ListKiosksHandler),
    ('/kiosks/<kiosk_id>/send_message', ListKiosksHandler),
    ('/kiosks/<kiosk_id>/send_command', ListKiosksHandler),
    ('/kiosks/<kiosk_id>/status', ListKiosksHandler),
    ('/kiosks/<kiosk_id>/sync', ListKiosksHandler),
    ('/kiosks/<kiosk_id>/logs', ListKiosksHandler),
    ('/kiosks/<kiosk_id>/sync/<sync_id>', ListKiosksHandler),
    ('/kiosks/<kiosk_id>/logs/<log_id>', ListKiosksHandler),
    ('/api/<kiosk_id>/heartbeat', RPCHeartbeatHandler),
    ('/api/<kiosk_id>/logupload', RPCHeartbeatHandler),
    ('/api/<kiosk_id>/communicate', RPCHeartbeatHandler),
], config=config, debug=True)

def main():
    app.run()
    
if __name__ == '__main__':
    main()
    

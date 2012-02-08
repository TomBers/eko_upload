from webapp2_extras import jinja2, sessions
from google.appengine.api import users
from data import Kiosk, SyncSession, ServerMessage
from google.appengine.ext import db
import logging

from handlers.BaseHandler import BaseHandler
from handlers.KioskHandlers import KioskFeedHelper

from google.appengine.api import memcache
from datetime import datetime, timedelta

class ListSyncSessionHandler(BaseHandler):
    def get(self, dieid):
        user = users.get_current_user()
        ctx = self.get_ctx(user)
        if user:
            kiosk = Kiosk.kiosk_from_dieid(dieid)
            if not kiosk:
                self.error(404)
                return
            ctx['kiosk'] = kiosk
            helper = KioskFeedHelper(user)
            ctx['heartbeat'] = helper.getMostRecentHeartbeat(kiosk)
            twomonthsago = datetime.utcnow() - timedelta(days=60)
            logging.debug("SyncSessions since %s." % (twomonthsago.strftime("%d%b%Y")))
            syncsessions = memcache.get(dieid, namespace='syncsessions')
            if not syncsessions:
                syncsessions = kiosk.syncsession_set.fetch(100)
                logging.debug("%d syncsessions fetched." % len(syncsessions))
                memcache.set(dieid, syncsessions, 60*60, namespace="syncsessions")
            ctx['sync_sessions'] = syncsessions
            
        else:
            self.redirect(users.create_login_url(self.request.uri))
        self.render_response('sync_list.html', **ctx)
import webapp2

from webapp2_extras import jinja2, sessions
from google.appengine.api import users
from google.appengine.api import memcache
import logging


class BaseHandler(webapp2.RequestHandler):

    @webapp2.cached_property
    def jinja2(self):
        # Returns a Jinja2 renderer cached in the app registry.
        return jinja2.get_jinja2(app=self.app)
            
    def render_response(self, _template, **context):
        # Renders a template and writes the result to the response.
        rv = self.jinja2.render_template(_template, **context)
        self.response.write(rv)
        
    def get_ctx(self, user):
        ctx = {}
        if user:
            ctx['login_text'] = "Logout"
            ctx['login_link'] = users.create_logout_url('/')
            ctx['user_name'] = user.nickname()
        else:
            ctx['login_text'] = "Login"
            ctx['login_link'] = users.create_login_url(self.request.uri)
        ctx['flashes'] = self.session.get_flashes()
        return ctx
    
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)
        
        try:
        # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
        # Save all sessions.
            self.session_store.save_sessions(self.response)
    
    @webapp2.cached_property
    def session(self):
    # Returns a session using the default cookie key.
        return self.session_store.get_session()

class FlushCacheHandler(BaseHandler):
    def get(self):
        memcache.flush_all()
        self.session.add_flash("Memcache flushed.", 'ok')
        self.redirect('/kiosks')
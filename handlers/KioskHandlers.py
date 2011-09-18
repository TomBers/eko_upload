import webapp2

from webapp2_extras import jinja2, sessions
from google.appengine.api import users
from data import Kiosk, SyncSession
from google.appengine.ext import db
import logging

from handlers.BaseHandler import BaseHandler

class ListKiosksHandler(BaseHandler):
    def get(self):
        user = users.get_current_user()
        ctx = self.get_ctx(user)
        if user:
            ctx['kiosks'] = db.GqlQuery("SELECT * FROM Kiosk WHERE admin = :1", user)
        else:
            self.redirect(users.create_login_url(self.request.uri))
        self.render_response('kiosk_list.html', **ctx)

class RegKiosksHandler(BaseHandler):
    
    formerror = []
    
    def get(self):
        self._render_form()
    
    def post(self):
        user = users.get_current_user()
        data = {}
        self.formerror = []
        if user:
            #validate
            data['name'] = self.request.get('name')
            data['org'] = self.request.get('organisation')
            data['loc'] = self.request.get('location')
            data['pubkey'] = self.request.get('pubkey')
            data['dieid'] = self.request.get('dieid')
            data['notify_email'] = self.request.get('notify_email')
            data['notify_sms'] = self.request.get('notify_sms')
            data['hardware'] = self.request.get('hardware')
            data['pubkey_e'] = self.request.get('pubkey_e')
            data['pubkey_n'] = self.request.get('pubkey_n')
            data['admin'] = user
            
            if data['name'] == '':
                self.formerror.append('Enter a kiosk name.')
            if data['org'] == '':
                self.formerror.append('Enter a organisation name.')
            if data['loc'] == '':
                self.formerror.append('Enter a location for this kiosk.')
            if data['pubkey_e'] == '':
                self.formerror.append('Set the RSA public key [e] parameter for the datalogger.')
            if data['pubkey_n'] == '':
            	self.formerror.append('Set the RSA public key [n] parameter for the datalogger.')
            
            if len(self.formerror) != 0:
                self._render_form(data)
                return
            
            try:
                k = Kiosk()
                k.populate_from_dict(data)
                k.put()
            #except:
            #    logging.exception('Unable to save kiosk to db') 
            #    self.session.add_flash('Add failed', 'error')
            finally:
                self.redirect('/kiosks')
                self.session.add_flash('Kiosk record created for %s at %s' % (data['name'], data['loc']), 'ok')
        else:
            #kick user
            self.redirect(users.create_login_url(self.request.uri)) 
            
    def _render_form(self, data={}):
        user = users.get_current_user()
        ctx = self.get_ctx(user)
        ctx['kioskhwls'] = [{'value':'BBXM_MB1', 'text':'BeagleXM / Mainboard Rev2'}, {'value':'BBXM_MB2', 'text':'BeagleXM / Mainboard Rev1'}, {'value':'IGEP', 'text':'IGEPv2'}]
        if data:
            ctx['data'] = data
            ctx['prepop'] = True
        ctx['errors'] = self.formerror
        
        if user:
            pass
        else:
            self.redirect(users.create_login_url(self.request.uri))
        self.render_response('kiosk_register.html', **ctx)
  
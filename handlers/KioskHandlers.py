import webapp2

from webapp2_extras import jinja2, sessions
from google.appengine.api import users
from data import Kiosk, SyncSession, ServerMessage
from google.appengine.ext import db
import logging

from handlers.BaseHandler import BaseHandler
from google.appengine.api import memcache
from datetime import datetime, timedelta

class ListKiosksHandler(BaseHandler):
    def get(self):
        user = users.get_current_user()
        ctx = self.get_ctx(user)
        if user:
            ctx['kiosks'] = KioskFeedHelper.getKiosksByUser(user)
            helper = KioskFeedHelper(user)
            ctx['heartbeats'] = helper.getHeartbeats()
            ctx['unsynced_smsgs'], ctx['recent_smsgs'] = helper.getServerMessages()
        else:
            self.redirect(users.create_login_url(self.request.uri))
        self.render_response('kiosk_list.html', **ctx)

class KioskFeedHelper(object):
    def __init__(self, user):
        self.user = user
    
    def getKiosksByUser(cls, user, recache=False):
    	if not user:
    		return
    	kiosks = memcache.get(user.user_id(), namespace='kiosks_by_owner')
        if (not kiosks) or (recache == True):
        	kiosks = db.GqlQuery("SELECT * FROM Kiosk WHERE admin = :1", user)
        	if not memcache.add(user.user_id(), kiosks, 5*60*60,namespace='kiosks_by_owner'):
        		logging.error("Could not cache kiosks in memcache.")
        return kiosks
    
    getKiosksByUser = classmethod(getKiosksByUser)
    
    def getHeartbeats(self, limit=20):
        """Returns a list of heartbeat records ordered by time for the current users kiosks"""
        kiosks = self.getKiosksByUser(self.user)
        heartbeats = []
        for kiosk in kiosks:
            heartbeats += kiosk.heartbeat_set.order('-server_time').fetch(limit)
        return heartbeats
    
    def getServerMessages(self, limit=10):
        """Returns a list of server messages"""
        kiosks = self.getKiosksByUser(self.user)
        unsynced_msgs = []
        recently_synced = []
        for kiosk in kiosks:
        	unsynced_msgs += kiosk.servermessage_set.filter('retrieved =', False).fetch(limit)
        	recently_synced += kiosk.servermessage_set.filter('retrieved =', True).fetch(limit)
        return (unsynced_msgs, recently_synced)
        
class RegKiosksHandler(BaseHandler):
    formerror = []
    
    def get(self):
        self._render_form()
    
    def post(self, kiosk_id=''):
        user = users.get_current_user()
        data = {}
        self.formerror = []
        if user:
            #validate
            data['name'] = self.request.get('name')
            data['org'] = self.request.get('organisation')
            data['loc'] = self.request.get('location')
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
            if data['dieid'] == '':
                self.formerror.append('Enter the die id of the OMAP3 SoC or hardcode a unqiue ID on the device.')
            if len(self.formerror) != 0:
                self._render_form(data)
                return
            
            try:
                self._commit_to_store(data)
            except:
                logging.exception('Unable to save kiosk to db') 
                self.session.add_flash('Add failed', 'error')
            finally:
            	# recache kiosks for this user
            	KioskFeedHelper.getKiosksByUser(user, recache=True)
                self.redirect('/kiosks')
                
        else:
            #kick user
            self.redirect(users.create_login_url(self.request.uri))
    
    def _commit_to_store(self, data):
        k = Kiosk()
        k.populate_from_dict(data)
        k.put()
        self.session.add_flash('Kiosk record created for %s at %s' % (data['name'], data['loc']), 'ok')
            
    def _render_form(self, data={}, edit=False):
        user = users.get_current_user()
        ctx = self.get_ctx(user)
        ctx['kioskhwls'] = [{'value':'BBXM_MB1', 'text':'BeagleXM / Mainboard Rev2'}, {'value':'BBXM_MB2', 'text':'BeagleXM / Mainboard Rev1'}, {'value':'IGEP', 'text':'IGEPv2'}]
        if data:
            ctx['data'] = data
            ctx['prepop'] = True
        if edit:
            ctx['editdata'] = True
        ctx['errors'] = self.formerror
        
        if user:
            pass
        else:
            self.redirect(users.create_login_url(self.request.uri))
        self.render_response('kiosk_register.html', **ctx)

class EditKioskHandler(RegKiosksHandler):
    formerror = []
    def get(self, kiosk_id):
        user = users.get_current_user()
        data = {}
        if user:
            # grab the data from datastore
            kiosk = db.GqlQuery("SELECT * FROM Kiosk WHERE dieid = :1 AND admin = :2", kiosk_id, user).get()
            if not kiosk:
                self.session.add_flash('There is no kiosk by id %s that is administered by you.' % kiosk_id, 'error')
                self.redirect('/kiosks')
                return
            data['name'] = kiosk.name
            data['org'] = kiosk.organisation
            data['hardware'] = kiosk.hardware
            data['admin'] = kiosk.admin
            data['loc'] = kiosk.location
            data['pubkey_e'] = kiosk.pubkey_e
            data['pubkey_n'] = kiosk.pubkey_n
            data['notify_email'] = kiosk.notify_email
            data['notify_sms'] = kiosk.notify_sms
            data['dieid'] = kiosk.dieid
            data['diero'] = True
            self._render_form(data, edit=True)
        else:
            self.redirect(users.create_login_url(self.request.uri))
    
    def _commit_to_store(self, data):
        user = users.get_current_user()
        kiosk_id = data['dieid']
        if not user:
            self.error(403)
            self.redirect(users.create_login_url(self.request.uri))
        k = db.GqlQuery("SELECT * FROM Kiosk WHERE dieid = :1 AND admin = :2", kiosk_id, user).get()
        if not k:
            logging.warn('Unable to commit kiosk %s to db' % kiosk_id) 
            self.session.add_flash('Edit failed, could not locate kiosk %s' % kiosk_id, 'error')
            self.redirect('/kiosks')
        k.populate_from_dict(data)
        try:
            k.put()
            self.session.add_flash('Kiosk record updated for %s at %s' % (data['name'], data['loc']), 'ok')
        except:
            logging.exception('Kiosk update failed!')
            self.session.add_flash('Could not update record', 'error')
            self.redirect('/kiosks')
        return

class SendMsgKioskHandler(BaseHandler):
    formerror = []
    
    def get(self):
        self._render_form()
        
    def post(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return
        data = {}
        data['dieid'] = self.request.get('dieid')
        data['msg_type'] = self.request.get('msg_type')
        data['message'] = self.request.get('message')
        if data['message'] == '':
            self.formerror.append('Message cannot be blank.')
        if data['msg_type'] == '':
            self.formerror.append('Please select a message type.')
        if data['dieid'] == '':
            self.formerror.append('Select a kiosk.')
        if len(self.formerror) != 0:
            return self._render_form(data)
        
        try:
            self._commit_to_store(data)
        except:
            logging.exception("Unable to add message to datastore")
            self.session.add_flash("Add SendMsg failed.", 'error')
        finally:
            self.redirect('/kiosks')
            
    def _commit_to_store(self, data):
        m = ServerMessage()
        kiosk = db.GqlQuery("SELECT * FROM Kiosk WHERE dieid = :1", data['dieid']).get()
        if not kiosk:
            logging.warn("Kiosk dissapeared for dieid %s?" % data['dieid'])
            self.session.add_flash("Add SendMsg failed because kiosk record is absent?")
        m.kiosk = kiosk
        m.msg_type = data['msg_type']
        m.message = data['message']
        m.date = datetime.utcnow()
        m.retrieved = False
        m.put()
        self.session.add_flash("Message (%s) waiting for device %s installed at %s." % (data['msg_type'], kiosk.name, kiosk.location), 'ok')
        
    def _render_form(self, data={}, edit=False):
        user = users.get_current_user()
        ctx = self.get_ctx(user)
        ctx['msgtypes'] = [{'value':'CMD', 'text':'Execute System Command'}, {'value':'DISP', 'text':'Display Message on Monitor'}, {'value':'GIVELOGS', 'text':'Upload Specified Log Files'}, {'value':'STAYALIVE', 'text':'Stay Online for Remote Access'}]
        kiosks = db.GqlQuery("SELECT * FROM Kiosk WHERE admin = :1", user)
        if not kiosks:
            self.session.add_flash('You do not have any kiosks registered.', 'error')
            self.redirect('/kiosks')
            return
        lst = []
        for kiosk in kiosks:
            dict = {}
            dict['text'] = '(%s) %s - %s [%s]' % (kiosk.organisation, kiosk.name, kiosk.location, kiosk.dieid)
            dict['value'] = kiosk.dieid
            lst.append(dict)
        ctx['kiosks'] = lst
        
        if data:
            ctx['data'] = data
            ctx['prepop'] = True
        if edit:
            ctx['editdata'] = True
        ctx['errors'] = self.formerror
        
        if user:
            pass
        else:
            self.redirect(users.create_login_url(self.request.uri))
        self.render_response('kiosk_send_message.html', **ctx)

import datetime
from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.api import memcache
import logging
class Kiosk(db.Model):
    """A record for a kiosk including its owner and security key"""
    name = db.StringProperty()
    admin = db.UserProperty()
    organisation = db.StringProperty()
    hardware = db.StringProperty()
    location = db.StringProperty()
    pubkey_e = db.StringProperty()
    pubkey_n = db.StringProperty()
    dieid = db.StringProperty()
    notify_email = db.EmailProperty()
    notify_sms = db.StringProperty()
    
    def populate_from_dict(self, data):
        self.name = data['name']
        self.hardware = data['hardware']
        self.organisation = data['org']
        self.admin = data['admin']
        self.location = data['loc']
        self.pubkey_e = data['pubkey_e']
        self.pubkey_n = data['pubkey_n']
        self.notify_email = data['notify_email']
        self.notify_sms = data['notify_sms']
        self.dieid = data['dieid']
        return
    
    def kiosk_from_dieid(cls, dieid):
        kiosk = memcache.get(dieid, namespace='kiosks')
        if kiosk is not None:
            return kiosk
        else:
            kiosk = db.GqlQuery("SELECT * FROM Kiosk where dieid = :1", dieid).get()
            if kiosk is None:
                return None
            if not memcache.add(dieid, kiosk, namespace='kiosks'):
                logging.error("Unable to set memcache for kiosk %s." % kiosk.dieid)
            return kiosk
    kiosk_from_dieid = classmethod(kiosk_from_dieid)
    
    # override the default put function to update memcache transparently
    # this handles both create and update.
    def put(self, **kwargs):
        super(Kiosk, self).put(**kwargs)
        if not memcache.set(self.dieid, self, namespace='kiosks'):
            logging.error("Unable to add entity kiosk to memcache")
        if not memcache.delete('allkiosks'):
            logging.error("Network Error deleteig all cached kiosks.")
        if not memcache.delete(self.admin.user_id(), namespace="kiosks_by_owner"):
            logging.error("Network Error deleting all cached kiosks by owner.")
    
class SyncSession(db.Model):
    """A upload session from the kiosk"""
    client_ref = db.StringProperty()
    kiosk = db.ReferenceProperty(Kiosk)
    start_date = db.DateTimeProperty()
    end_date = db.DateTimeProperty()
    data_type = db.StringProperty()
    payload_size = db.IntegerProperty()
    client_ip = db.StringProperty()
    software_version = db.StringProperty()
    payload = blobstore.BlobReferenceProperty()
    manifest = blobstore.BlobReferenceProperty()
    
    def put(self, **kwargs):
        super(SyncSession, self).put(**kwargs)
        # cache session in memcache for 1 hour
        if not memcache.set(self.client_ref, self, 60*60,namespace='syncsessions'):
            logging.error("Could not put syncsession %s in memcache." % self.client_ref)
    
    def get_by_clientref(cls, ref):
        sess = memcache.get(ref, namespace='syncsessions')
        if not sess:
            sess = db.GqlQuery("SELECT * FROM SyncSession WHERE client_ref = :1", ref).get()
            if sess:
                memcache.set(sess.client_ref, self, 60*60, namespace='syncsessions')
        return sess
    get_by_clientref = classmethod(get_by_clientref)

class ServerMessage(db.Model):
    """A message from the server to the kiosk"""
    kiosk = db.ReferenceProperty(Kiosk)
    message = db.TextProperty() # can be a command. eg: STAY_ALIVE
    msg_type = db.StringProperty()
    date = db.DateTimeProperty()
    retrieved = db.BooleanProperty()
    retrieved_date = db.DateTimeProperty()
    
class KioskMessage(db.Model):
    """A message from the kiosk to the server"""
    kiosk = db.ReferenceProperty(Kiosk)
    message = db.TextProperty()
    origin = db.StringProperty()
    ip = db.StringProperty()
    
    date = db.DateTimeProperty()
    
    origin_date = db.DateTimeProperty()
    # a kiosk may refer to a server message
    #server_msg = db.ReferenceProperty(ServerMessage)
    
    # a kiosk may refer to a sync upload
    session_ref = db.ReferenceProperty(SyncSession)

class Heartbeat(db.Model):
    """A kiosk sends a heartbeat every time it finds itself online"""
    kiosk = db.ReferenceProperty(Kiosk)
    client_ip = db.StringProperty()
    client_intip = db.StringProperty()
    client_uptime = db.StringProperty()
    software_version = db.StringProperty()
    client_time = db.DateTimeProperty()
    server_time = db.DateTimeProperty()
    
    def skew_str(self):
        tdiff = self.server_time - self.client_time
        skew_secs = tdiff.seconds
        if skew_secs == 0:
            return "%.2f ms" % (tdiff.microseconds/1000.0)
        elif skew_secs > 3600*24:
            return "%d days" % tdiff.days
        else:
            return "%d secs" % tdiff.seconds
    
    def bad_skew(self):
        tdiff = self.server_time - self.client_time
        if tdiff.seconds >= 120:
            return True
        return False
    
    def age(self):
        tdiff = self.server_time - datetime.datetime.utcnow()
        seconds = tdiff.seconds
        if seconds > 60*60:
            return "%.2f hours ago" % (tdiff.seconds/3600.0)
        elif seconds > 60:
            return "%d minutes ago" % (int(round(tdiff.seconds/60.0)))
        else:
            return "%d seconds ago" % (tdiff.seconds)
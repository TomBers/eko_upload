import datetime
from google.appengine.ext import db
from google.appengine.ext import blobstore

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

class SyncSession(db.Model):
	"""A upload session from the kiosk"""
	kiosk = db.ReferenceProperty(Kiosk)
	date = db.DateTimeProperty()
	dat_payload_size = db.IntegerProperty()
	msg_recvd = db.IntegerProperty()
	client_ip = db.StringProperty()
	software_version = db.StringProperty()
	data_zip = blobstore.BlobReferenceProperty()
	logs_zip = blobstore.BlobReferenceProperty()


class ServerMessage(db.Model):
	"""A message from the server to the kiosk"""
	kiosk = db.ReferenceProperty(Kiosk)
	message = db.StringProperty() # can be a command. eg: STAY_ALIVE
	date = db.DateTimeProperty()
	retrieved = db.BooleanProperty()
	session = db.ReferenceProperty(SyncSession)

class KioskMessage(db.Model):
	"""A message from the kiosk to the server"""
	kiosk = db.ReferenceProperty(Kiosk)
	message = db.StringProperty()
	origin = db.StringProperty()
	date = db.DateTimeProperty()
	session = db.ReferenceProperty(SyncSession)

class Heartbeat(db.Model):
	"""A kiosk sends a heartbeat every time it finds itself online"""
	kiosk = db.ReferenceProperty(Kiosk)
	client_ip = db.StringProperty()
	client_uptime = db.StringProperty()
	software_version = db.StringProperty()
	client_time = db.DateTimeProperty()
	server_time = db.DateTimeProperty()
	
import webapp2
from google.appengine.api import users
import logging
import simplejson_with_datetime as simplejson

from Crypto.Hash import MD5
import Crypto.PublicKey.RSA as RSA

import pickle

from datetime import datetime

from data import Heartbeat

class RPCHandler(webapp2.RequestHandler):
    """ Allows the functions defined in the RPCMethods class to be RPCed."""
    def __init__(self):
        webapp.RequestHandler.__init__(self)
        self.methods = RPCMethods()
	
	def _process(self):
		json = simplejson.loads(self.request.body)
        # args looks like {'method':'foo', 'id':'blhblah', 'params':[arg1, arg2,...]}
        try:
        	self.method = json['method']
        	self.params = json['params']
        	self.id = json['id']
        except KeyError as e:
        	logger.critical("JSON message processing failed. Dumping Msg:\n\n%s" % self.request.body)
    		raise ValueError("JSON body missing parameter: %s" % e)
        return (self.method, self.params, self.id)
    
    def _standard_error_response(self, func, id, ename, ecode, edesc):
    	resp = {}
    	error_dict = {}
    	error_dict['name'] = ename
    	error_dict['code'] = ecode
    	error_dict['message'] = edesc
    	resp['method'] = func
    	resp['result'] = None
    	resp['id'] = id
    	resp['error'] = error_dict 
    	return resp
    
    
    def post(self):
        try:
        	func, params, id = self._process()
        except ValueError as e:
        	self.error(400) # bad request
        	return
        	
        if func[0] == '_':
            self.error(403) # access denied
            return

        func = getattr(self.methods, func, None)
        if not func:
            self.error(404) # file not found
            return
        self.response.headers['content-type'] = 'application/json'
        try:
        	result = func(*args)
        except:
        	logging.exception("Could not execute rpc %s." % func)
        	self.error(500)
        	return
        self.response.out.write(simplejson.dumps(result))

class RPCHeartbeatHandler(RPCHandler):
	def heartbeat(self, dieid, uptime, sw_version, time):
		# find the kiosk from the kiosk id
		kiosk = db.GqlQuery("SELECT * FROM Kiosk where dieid = :1", dieid).get()
		if not kiosk:
			logging.warn('Unrecognised kiosk attempted heartbeat (IP: %s, sw_version: %s, dieid: %s).' % (self.request.remote_addr, sw_version, dieid))
			return self._standard_error_response(func, id, 'Not recognised', 20, 'Kiosk not registered with system.')
		hash = MD5.new(self.request.body).digest()
		try:
			signature = self.request.headers['X-eko-signature']
		except KeyError:
			logger.critical("Client message did not provide verification signature")
		if not signature:
			# prepare error response
			return self._standard_error_response(func, id, 'Signature Absent', 10, 'Verification signature not present.')
		
		#create the public key
		try:
			pubkey = RSA.construct((int(kiosk.pubkey_e), int(kiosk.pubkey_n)))
		except:
			logger.critical("Could not create public key for kiosk")
		
		if not pubkey:
			return self._standard_error_response(func, id, 'Signature Fail', 11, 'Unable to create public key from config.')
		
		if pubkey and signature:
			if pubkey.verify(hash, signature):
				#message is authentic
				self._create_heartbeat(kiosk, uptime, sw_version, time, self.request.remote_addr)
				data = {}
				data['result'] = 'Success'
				data['error'] = None
				data['id'] = self.id
				return data
			else:
				return self._standard_error_response(func, id, 'Signature Incorrect', 12, 'Verification signature failed check.')
	def _create_heartbeat(self, kiosk, uptime, sw_version, time, ip):
		h = HeartBeat()
		h.client_ip = ip
		h.client_uptime = uptime
		h.kiosk  = kiosk
		h.software_version = sw_version
		h.client_time = time
		h.server_time = datetime.now()
		h.put()
		logging.info("Heartbeat registerd from %s@%s" % (kiosk.name, ip))
		return
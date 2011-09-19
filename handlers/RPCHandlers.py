import webapp2
from google.appengine.api import users
import logging
import simplejson_with_datetime as simplejson

from Crypto.Hash import MD5
import Crypto.PublicKey.RSA as RSA
from google.appengine.ext import db

import pickle

from datetime import datetime

# the database model
from data import Heartbeat

# encode decode/long integers to from ascii
from baseconv import BaseConverter

class JSONRPCMethods(object):
    def __init__(self, request):
        self.request = request
    
    def get_messages(self, method, id, **kwargs):
    	"""Returns all server messages that are pending for the kiosk"""
    	bconv = BaseConverter('0123456789abcdef')
    	dieid = kwargs['dieid']
    	logging.debug('[GETMSG] Die id is: %s' % dieid)
    	
    	kiosk = db.GqlQuery("SELECT * FROM Kiosk where dieid = :1", dieid).get()
    	
    	if not kiosk:
    		logging.warn('Unrecognised kiosk attempted to fetch server messages (IP: %s, dieid %s).' % (self.request.remote_addr, dieid))
    		return self._standard_error_response(method, id, 'Not recognised', 20, 'Kiosk not registered with system.')
    	
    	hash = MD5.new(self.request.body).digest()
    	
    	logging.info('Receiving message fetch request from kiosk %s at IP %s' % (kiosk.name, self.request.remote_addr))
    	
    	try:
            signature = bconv.to_decimal(self.request.headers['X-eko-signature'])
        except KeyError:
            logging.critical("Client message did not provide verification signature")
        
        # useful for debugging RSA issues
        logging.debug("signature long : %d ::: " % signature)
        logging.debug("hdr: %s" % self.request.headers['X-eko-signature'])
        logging.debug("hash: %s"  % "".join(["%02x " % ord(x) for x in hash]))
        
        if not signature:
            # prepare error response
            return self._standard_error_response(method, id, 'Signature Absent', 10, 'Verification signature not present.')
        
        # get encoded public key from database
        pubkey_n = bconv.to_decimal(kiosk.pubkey_n)
        pubkey_e = bconv.to_decimal(kiosk.pubkey_e)
        
        #create the public key
        try:
            pubkey = RSA.construct((pubkey_n, pubkey_e))
        except:
            logging.critical("Could not create public key for kiosk")
        
        if not pubkey:
            return self._standard_error_response(method, id, 'Signature Fail', 11, 'Unable to create public key from config.')
        
        
        if pubkey and signature:
            if pubkey.verify(hash, (signature,)):
                #message is authentic
                messages = self._get_server_messages(kiosk)
                data = {}
                data['result'] = messages
                data['error'] = None
                data['id'] = id
                return data
            else:
                return self._standard_error_response(method, id, 'Signature Incorrect', 12, 'Verification signature failed check.')
    
    def _get_server_messages(self, kiosk):
    	messages = kiosk.servermessage_set.filter('retrieved =', False).fetch(10)
    	response = []
    	for message in messages:
    		dict = {}
    		dict['msg'] = message.message
    		dict['msg_type'] = message.msg_type
    		dict['date'] = message.date
    		message.retrieved = True
    		message.retrieved_date = datetime.utcnow()
    		message.put()
    		response.append(dict)
    	return response
    
    def _standard_error_response(self, func, id, ename, ecode, edesc):
        """Creates a json object in the format of an error"""
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
        
    def heartbeat(self, method, id, **kwargs):
        """Registers a heartbeat from a datalogger unit"""
        bconv = BaseConverter('0123456789abcdef')
        # extract arguments
        dieid = kwargs['dieid']
        uptime = kwargs['uptime']
        sw_version = kwargs['sw_version']
        time = kwargs['time']
        
        # find the kiosk from the kiosk id
        logging.debug("[%s] Die id is : %s" % (method, dieid))
        kiosk = db.GqlQuery("SELECT * FROM Kiosk where dieid = :1", dieid).get()
        
        if not kiosk:
            logging.warn('Unrecognised kiosk attempted %s (IP: %s, sw_version: %s, dieid: %s).' % (method, self.request.remote_addr, sw_version, dieid))
            return self._standard_error_response(method, id, 'Not recognised', 20, 'Kiosk not registered with system.')
        
        # calculate hash of request body
        hash = MD5.new(self.request.body).digest()
        
        # log this event
        logging.info('Receiving kiosk heartbeat from kiosk %s at IP %s' % (kiosk.name, self.request.remote_addr))
        
        # check for message signature
        try:
            signature = bconv.to_decimal(self.request.headers['X-eko-signature'])
        except KeyError:
            logging.critical("Client message did not provide verification signature")
        
        # useful for debugging RSA issues
        logging.debug("signature long : %d ::: " % signature)
        logging.debug("hdr: %s" % self.request.headers['X-eko-signature'])
        logging.debug("hash: %s"  % "".join(["%02x " % ord(x) for x in hash]))
        
        if not signature:
            # prepare error response
            return self._standard_error_response(method, id, 'Signature Absent', 10, 'Verification signature not present.')
        
        # get encoded public key from database
        pubkey_n = bconv.to_decimal(kiosk.pubkey_n)
        pubkey_e = bconv.to_decimal(kiosk.pubkey_e)
        
        #create the public key
        try:
            pubkey = RSA.construct((pubkey_n, pubkey_e))
        except:
            logging.critical("Could not create public key for kiosk")
        
        if not pubkey:
            return self._standard_error_response(method, id, 'Signature Fail', 11, 'Unable to create public key from config.')
        
        
        if pubkey and signature:
            if pubkey.verify(hash, (signature,)):
                #message is authentic
                self._create_heartbeat(kiosk, uptime, sw_version, time, self.request.remote_addr)
                data = {}
                data['result'] = 'Success'
                data['error'] = None
                data['id'] = id
                return data
            else:
                return self._standard_error_response(method, id, 'Signature Incorrect', 12, 'Verification signature failed check.')
    
    # registers the heartbeat in the data store
    def _create_heartbeat(self, kiosk, uptime, sw_version, time, ip):
        h = Heartbeat()
        h.client_ip = ip
        h.client_uptime = uptime
        h.kiosk  = kiosk
        h.software_version = sw_version
        h.client_time = time
        h.server_time = datetime.utcnow()
        h.put()
        logging.info("Heartbeat registered from %s@%s" % (kiosk.name, ip))
        return

class JSONRPCHandler(webapp2.RequestHandler):
    """ Allows the functions defined in the RPCMethods class to be RPCed through JSON."""
    def __init__(self, request=None, response=None):
        webapp2.RequestHandler.__init__(self, request, response)
        self.methods = JSONRPCMethods(request)
        return

    def process(self):
        json = simplejson.loads(self.request.body)
        # args looks like {'method':'foo', 'id':'blhblah', 'params':{'arg1':'bar',...}}
        try:
            method = str(json['method'])
            params = json['params']
            id = str(json['id'])
        except KeyError, e:
            logging.critical("JSON message processing failed. Dumping Msg:\n\n%s\n\n" % self.request.body)
            raise ValueError("JSON body missing parameter: %s" % e)
        params2 = dict([(str(x),params[x]) for x in params.keys()]) 
        logging.info("WTF? %s" % str(params))
        return (method, params2, id)
    
    def post(self):
        try:
            method, params, id = self.process()
        except ValueError, e:
            self.error(400) # bad request
            return
            
        if method[0] == '_':
            self.error(403) # access denied
            return

        func = getattr(self.methods, method, None)
        if not func:
            self.error(404) # file not found
            return
        
        logging.info("This is whats causing trouble %s" % str(params))
        self.response.headers['content-type'] = 'application/json'
        try:
            result = func(method, id, **params)
        except:
            logging.exception("Could not execute rpc %s." % func)
            self.error(500)
            return
        self.response.out.write(simplejson.dumps(result))


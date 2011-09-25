"""
.. module:: RPCHandlers
   :platform: Unix (GAE Runtime)
   :synopsis: Handles RPC requests from remote clients.
   
.. moduleauthor:: Charith Amarasinghe<charith.amarasinghe08@imperial.ac.uk>
"""

import webapp2
from google.appengine.api import users
import logging
import simplejson_with_datetime as simplejson

from Crypto.Hash import MD5
import Crypto.PublicKey.RSA as RSA
from google.appengine.ext import db
from google.appengine.api import memcache
import pickle

from datetime import datetime

# the database model
from data import Heartbeat, Kiosk, KioskMessage, SyncSession, ServerMessage

# encode decode/long integers to from ascii
from baseconv import BaseConverter

class JSONRPCMethods(object):
    """
    .. py:class:: JSONRPCMethods(request)
    
    Contains methods accessible by the JSON RPC.
    
    :param request: The WebOb request object.
    """
    def __init__(self, request):
        self.request = request
        self.bconv = BaseConverter('0123456789abcdef')
    
    def _extract_signature_hdr(self):
        """
        .. py:func:: _extract_signature_hdr()
        
        Extracts the signature from the request header and calculates the request hash.
        
        :rtype (hash, (signature,)): A tuple containing the hash and signature.
        """
        hash = MD5.new(self.request.body).digest()
        
        try:
            signature = self.bconv.to_decimal(self.request.headers['X-eko-signature'])
        except KeyError:
            logging.critical("Client message did not provide verification signature")
        
        # useful for debugging RSA issues
        logging.debug("signature long : %d ::: " % signature)
        logging.debug("hdr: %s" % self.request.headers['X-eko-signature'])
        logging.debug("hash: %s"  % "".join(["%02x " % ord(x) for x in hash]))
        return (hash, (signature,))
    
    def _get_public_key(self, kiosk):
        """
        .. py:func:: _get_public_key(kiosk)
        
        Returns the public key for this kiosk, either from memcache or the datastore.
        
        :param kiosk: The kiosk object.
        :rtype RSAobj: A public key object.
        """
        # check memcache
        pubkey = memcache.get(kiosk.dieid, namespace='rsa-publickeys')
        if pubkey is not None:
            return pubkey
        else:
            # get encoded public key from database
            pubkey_n = self.bconv.to_decimal(kiosk.pubkey_n)
            pubkey_e = self.bconv.to_decimal(kiosk.pubkey_e)
            
            #create the public key
            try:
                pubkey = RSA.construct((pubkey_n, pubkey_e))
            except:
                logging.critical("Could not create public key for kiosk")
                return None
            if not memcache.add(kiosk.dieid, pubkey, namespace='rsa-publickeys'):
                logging.error("Unable to save rsa key to memcache.")
            return pubkey
    
    def get_messages(self, method, id, **kwargs):
        """
        .. py:func:: get_messages(method, id, **kwargs)
        
        Returns all server messages that are pending for the kiosk.
        
        :param method: The name of the requested json method (should be equal to 'get_messages')
        :param id: Unused
        :param **kwargs: Keyword arguments to the function. Should have non-unicode keys.
        :rtype dict: The response object. 
        Expects the following in kwargs:
        kiosk-id : The unique kiosk identifier
        
        Expects the following headers:
        X-eko-signature: RSA signed hash of request body.
        """
        
        dieid = kwargs['kiosk-id']
        
        logging.debug('device with id : %s is requesting incoming messages.' % dieid)
        
        # grab kiosk, internally utilises memcache
        kiosk = Kiosk.kiosk_from_dieid(dieid)
        
        if not kiosk:
            logging.warn('Unrecognised kiosk attempted to fetch server messages (IP: %s, dieid %s).' % (self.request.remote_addr, dieid))
            return self._standard_error_response(method, id, 'Not recognised', 20, 'Kiosk not registered with system.')
        
        logging.info('Receiving message fetch request from kiosk %s at IP %s' % (kiosk.name, self.request.remote_addr))
        
        hash, signature = self._extract_signature_hdr()
        
        if not signature[0]:
            # prepare error response
            return self._standard_error_response(method, id, 'Signature Absent', 10, 'Verification signature not present.')
        
        pubkey = self._get_public_key(kiosk)
        
        if not pubkey:
            return self._standard_error_response(method, id, 'Signature Fail', 11, 'Unable to create public key from config.')
        
        
        if pubkey and signature[0]:
            if pubkey.verify(hash, signature):
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
        """
        .. py:func:: _get_server_messages(kiosk)
        
           Returns server messages that haven't yet been downloaded by a kiosk.
           
           :param kiosk: The kiosk object which owns the messages.
        """
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
        """
        .. py:func:: heartbeat(method, id, **kwargs)
        
        Registers a kiosks IP address, software version and uptime in the datastore.
        
        :param method: The name of the requested json method (should be equal to 'heartbeat')
        :param id: Unused
        :param **kwargs: Keyword arguments to the function. Should have non-unicode keys.
        :rtype dict: The response object. 
        Expects the following in kwargs:
        kiosk-id : The unique kiosk identifier
        uptime: A string representing the time elapsed since the script executed.
        sw_version: Version of the datalogger software running on the device.
        time: The UTC time on the datalogger.
        
        Expects the following headers:
        X-eko-signature: RSA signed hash of request body.
        """
        # extract arguments
        dieid = kwargs['kiosk-id']
        uptime = kwargs['uptime']
        sw_version = kwargs['sw-version']
        time = kwargs['time']
        
        # find the kiosk from the kiosk id
        logging.debug('device with id : %s has a pulse.' % dieid)
        kiosk = Kiosk.kiosk_from_dieid(dieid)
        
        
        if not kiosk:
            logging.warn('Unrecognised kiosk attempted %s (IP: %s, sw_version: %s, dieid: %s).' % (method, self.request.remote_addr, sw_version, dieid))
            return self._standard_error_response(method, id, 'Not recognised', 20, 'Kiosk not registered with system.')
        
        # log this event
        logging.info('Receiving kiosk heartbeat from kiosk %s at IP %s' % (kiosk.name, self.request.remote_addr))
        
        hash, signature = self._extract_signature_hdr()
       
        if not signature[0]:
            # prepare error response
            return self._standard_error_response(method, id, 'Signature Absent', 10, 'Verification signature not present.')
        
        pubkey = self._get_public_key(kiosk)
        
        if not pubkey:
            return self._standard_error_response(method, id, 'Signature Fail', 11, 'Unable to create public key from config.')
        
        
        if pubkey and signature:
            if pubkey.verify(hash, signature):
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
        """
        .. py:func:: _create_heartbeat(kiosk, uptime, sw_version, time, ip)
        
           Creates a heartbeat record in the datastore.
        """
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
        
    def post_messages(self, method, id, **kwargs):
        """
        .. py:func:: post_messages(method, id, **kwargs)
        
        Registers a message from a kiosk in the datastore.
        
        :param method: The name of the requested json method (should be equal to 'post_messages')
        :param id: Unused
        :param **kwargs: Keyword arguments to the function. Should have non-unicode keys.
        :rtype dict: The response object. 
        
        Expects the following in kwargs:
        kiosk-id : The unique kiosk identifier
        message: A text message.
        origin: The origin of the message (subsystem).
        date: The UTC time on the datalogger that the message originated.
        
        [session-ref] : An optional reference to a upload session.
        
        Expects the following headers:
        X-eko-signature: RSA signed hash of request body.
        """
        # extract arguments
        dieid = kwargs['kiosk-id']
        messages = kwargs['messages']
        
        # find the kiosk from the kiosk id
        logging.debug('device with id : %s has a pulse.' % dieid)
        kiosk = Kiosk.kiosk_from_dieid(dieid)
        
        
        if not kiosk:
            logging.warn('Unrecognised kiosk attempted %s (IP: %s, dieid: %s).' % (method, self.request.remote_addr, dieid))
            return self._standard_error_response(method, id, 'Not recognised', 20, 'Kiosk not registered with system.')
        
        # log this event
        logging.info('Receiving %d kiosk messages from kiosk %s at IP %s' % (len(messages), kiosk.name, self.request.remote_addr))
        
        hash, signature = self._extract_signature_hdr()
       
        if not signature[0]:
            # prepare error response
            return self._standard_error_response(method, id, 'Signature Absent', 10, 'Verification signature not present.')
        
        pubkey = self._get_public_key(kiosk)
        
        if not pubkey:
            return self._standard_error_response(method, id, 'Signature Fail', 11, 'Unable to create public key from config.')
        
        
        if pubkey and signature:
            if pubkey.verify(hash, signature):
                #message is authentic
                for message in messages:
                    self._create_clientmsg(kiosk, message, self.request.remote_addr)
                data = {}
                data['result'] = 'Success'
                data['error'] = None
                data['id'] = id
                return data
            else:
                return self._standard_error_response(method, id, 'Signature Incorrect', 12, 'Verification signature failed check.')
    
    # registers the heartbeat in the data store
    def _create_clientmsg(self, kiosk, message, ip):
        """
        .. py:func:: _create_clientmsg(kiosk, message)
        
           Creates a kisok message record in the datastore.
        """
        h = KioskMessage()
        h.ip = ip
        h.date = datetime.utcnow()
        h.kiosk  = kiosk
        
        if 'session-ref' in message.keys():
            session_uuid = message['session-ref']
        else:
            session_uuid = None
            
        if 'message' in message.keys():
            if message['message'] is not None:
                h.message = message['message']
        else:
            logging.error("No message in kiosk msg from %s" % kiosk.dieid)
        
        if 'origin' in message.keys():
            if message['origin'] is not None:
                h.origin = message['origin']
        else:
            logging.error("No origin for kiosk msg from %s" % kiosk.dieid)
        
        if 'origin-date' in message.keys():
            if message['origin-date'] is not None:
                h.origin_date = message['origin-date']
        else:
            logging.error("No origin date for kiosk msg from %s" % kiosk.dieid)
        
        if session_uuid is not None:
            sess = db.GqlQuery("SELECT __key__ FROM SyncSession WHERE client_ref = :1", session_uuid).get()
            if sess:
                h.session_ref = sess
        
        h.put()
        logging.info("Kiosk Message registered from %s@%s" % (kiosk.name, ip))
        return

class JSONRPCHandler(webapp2.RequestHandler):
    """
    .. py:class:: JSONRPCHandler(request, response)
    
       Allows the functions defined in the RPCMethods class to be RPCed through JSON.
    
       :param request: WebOb Request.
       :param response: WebOb Response.
    """
    def __init__(self, request=None, response=None):
        webapp2.RequestHandler.__init__(self, request, response)
        self.methods = JSONRPCMethods(request)
        return

    def process(self):
        """
        .. py:func:: process()
        
           Processes a JSON request
        """
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
        
    def get(self):
        response_dict = {}
        response_dict['me'] = self.request.url
        response_dict['version'] = '2.0.0'
        response_dict['vendor'] = 'e.quinox'
        response_dict['provides'] = ['heartbeat', 'get_messages', 'post_messages']
        response_dict['config'] = {'utc': datetime.utcnow()}
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(response_dict))
        
    def post(self):
        """
        .. py:func:: post()
        
           Dispatches a JSON request to the relavent method in JSONRPCMethods.
        """
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
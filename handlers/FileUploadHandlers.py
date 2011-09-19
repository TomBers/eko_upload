import webapp2

from webapp2_extras import jinja2, sessions
from google.appengine.api import users
from data import Kiosk, SyncSession
from google.appengine.ext import db
import logging

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

from handlers.BaseHandler import BaseHandler

from datetime import datetime, timedelta

from baseconv import BaseConverter

from uuid import uuid1

from Crypto.Hash import MD5
import Crypto.PublicKey.RSA as RSA

class FileUploadRequestHandler(webapp2.RequestHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/api/upload')
        self.response.headers['X-eko-challenge'] = str(uuid1().get_hex())
        self.response.write(upload_url)
        return

class FileUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    
    def _verify_client(self, kiosk, signature, challenge):
        bconv = BaseConverter('0123456789abcdef')
        
        # get encoded public key from database
        pubkey_n = bconv.to_decimal(kiosk.pubkey_n)
        pubkey_e = bconv.to_decimal(kiosk.pubkey_e)
        
        #create the public key
        try:
            pubkey = RSA.construct((pubkey_n, pubkey_e))
        except:
            logging.critical("Could not create public key for kiosk")
            return False
        
        try:
            val = pubkey.verify(challenge, (signature,))
        except:
            return False
        return val
        
    def post(self):
        
        logging.debug('Running File Upload Handler')
        
        bconv = BaseConverter('0123456789abcdef')
        
        dieid = self.request.get('kiosk-id')
        if not dieid:
            self.error(403)
            self.response.write('No device id provided.\n')
            return
        
        kiosk = db.GqlQuery("SELECT * FROM Kiosk WHERE dieid = :1", dieid).get()
        if not kiosk:
            self.error(400)
            self.response.write('Kiosk is unregistered on system.\n')
            logging.warn('Unregistered kiosk on ip %s with dieid %s.' % (self.request.remote_addr, dieid))
            return
        
        # look for the signature
        try:
            signature = bconv.to_decimal(self.request.headers['X-eko-signature'])
            challenge = self.request.headers['X-eko-challenge']
            # signature should be uuid we sent kiosk signed with the public key
            verify = self._verify_client(kiosk, signature, challenge)
        except:
            logging.exception("Authentication signature not found.\n")
            verify = False
        
        # auth failed
        if not verify:
            self.error(403)
            self.response.write('Unable to verify identity of kiosk.\n')
            return
        
        # a uuid that identifies this data packet on the remote device
        client_ref       = self.request.get('reference')
        if not client_ref:
            logging.error("No client reference provided.")
            client_ref = "FAILSAFE"
        
        # the type of data being sent (logs, readings, etc...)
        type             = self.request.get('type')
        # version of the client
        software_version = self.request.get('software_version')
        # manifest
        try:
            manifest = self.get_uploads(field_name='manifest')[0]
            logging.debug("Manifest uploaded, size: %s" % str(manifest.size))
        except:
            logging.exception("Manifest missing from upload data.")
            self.response.write('Manifest Not Found\n')
        
        # payload
        try:
            payload = self.get_uploads(field_name='payload')[0]
        except:
            logging.exception("Payload missing from upload data.")
            self.response.write('Payload Not Found\n')
        
        sync = SyncSession()
        sync.client_ref = client_ref
        sync.data_type = type
        
        sync.payload_size = 0
        
        # payload size + manifest size
        if payload:
            sync.payload_size += payload.size
        if manifest:
            sync.payload_size += manifest.size
        
        sync.payload = payload
        sync.manifest = manifest
        
        sync.client_ip = self.request.remote_addr
        sync.date = datetime.utcnow()
        
        try:
            sync.put()
            logging.debug("Sync packet succesfully added to datastore")
            self.response.write('Success\n')
        except:
            logging.exception("Adding sync packet failed.")
            self.response.write('Failure\n')
        return
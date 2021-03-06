import webapp2

from webapp2_extras import jinja2, sessions
from google.appengine.api import users
from data import Kiosk, SyncSession
from google.appengine.ext import db
from google.appengine.api import memcache
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
        challenge = str(uuid1().get_hex())
        self.response.headers['X-eko-challenge'] = challenge
        dieid = self.request.get('kiosk-id')
        kiosk = Kiosk.kiosk_from_dieid(dieid)
        
        # we create a sync session
        sess = SyncSession()
        sess.client_ref = challenge
        sess.client_ip = self.request.remote_addr
        sess.kiosk = kiosk
        sess.start_date = datetime.utcnow()
        sess.put()
        
        self.response.headers['client-ip'] = self.request.remote_addr
        self.response.write(upload_url)
        return

class FileUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    bconv = BaseConverter('0123456789abcdef')
    
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
            logging.debug("Pubkey n: %s." % kiosk.pubkey_n)
            pubkey_n = self.bconv.to_decimal(kiosk.pubkey_n)
            logging.debug("Pubkey e: %s." % kiosk.pubkey_e)
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
        
    def _verify_client(self, kiosk, signature, challenge):
        #create the public key
        pubkey = self._get_public_key(kiosk)
        
        if not pubkey:
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
            logger.warn('Device attempted contact without die id from ip %s.' % self.request.remote_addr)
            return
            
        logging.info("File upload incoming from kiosk : %s" % dieid)
        
        kiosk = Kiosk.kiosk_from_dieid(dieid)
        
        if not kiosk:
            self.error(400)
            self.response.write('Kiosk is unregistered on system.\n')
            logging.warn('Unregistered kiosk on ip %s with dieid %s.' % (self.request.remote_addr, dieid))
            return
            
        logging.debug("Encoded sig: %s." % self.request.headers['X-eko-signature'])
        
        # look for the signature
        try:
            signature = bconv.to_decimal(self.request.headers['X-eko-signature'])
            logging.debug("Decoded sig: %s." % str(signature))
            challenge = self.request.headers['X-eko-challenge']
            logging.debug("Challenge: %s." % challenge)
            # signature should be uuid we sent kiosk signed with the public key
            verify = self._verify_client(kiosk, signature, challenge)
        except:
            logging.exception("Authentication signature not found.\n")
            verify = False
        
        # auth failed
        if not verify:
            logging.error("Kiosk id %s did not pass id check." % dieid)
            self.response.write('Unable to verify identity of kiosk.\n')
            return
        
        # a uuid that identifies this data packet on the remote device
        client_ref       = self.request.headers['X-eko-challenge']
        if not client_ref:
            logging.error("No client reference provided.")
            self.response.write('Client Error: No reference provided.')
            return
        
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
        
        sync = SyncSession.get_by_clientref(client_ref)
        if not sync:
            logging.error("Upload attempt without requesting sync session.")
            self.response.write('Upload request improperly handled.')
            return
        sync.kiosk = kiosk
        sync.data_type = type
        sync.payload_size = 0
        
        # payload size + manifest size
        if payload:
            sync.payload_size += payload.size
        if manifest:
            sync.payload_size += manifest.size
        
        sync.payload = payload
        sync.manifest = manifest
        
        sync.software_version = software_version
        
        #sync.client_ip = self.request.remote_addr
        sync.end_date = datetime.utcnow()
        
        try:
            sync.put()
            logging.debug("Sync packet succesfully added to datastore")
            self.response.write('Success\n')
        except:
            logging.exception("Adding sync packet failed.")
            self.response.write('Failure\n')
        return
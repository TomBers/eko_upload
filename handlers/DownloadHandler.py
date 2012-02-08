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

class DownloadSyncHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, dload_key):
        if not blobstore.get(dload_key):
            self.error(404)
        else:
            self.send_blob(dload_key)
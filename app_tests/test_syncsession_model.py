import unittest
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed

from google.appengine.api import users

from data import Kiosk, SyncSession

import os

class KioskModelTestCase(unittest.TestCase):
    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()
        os.environ['USER_EMAIL'] = 'a@b.c'
        os.environ['USER_ID'] = '123'
        self.create_dummy_kiosk()
        self.create_dummy_session()
    
    def tearDown(self):
        self.testbed.deactivate()
    
    def create_dummy_kiosk(self):
        user = users.get_current_user()
        k = Kiosk()
        k.dieid = "A"
        k.name = "Foo"
        k.hardware = "Bar"
        k.admin = user
        k.put()
        #
        self.a = k
        k1 = Kiosk()
        k1.dieid = "B"
        k1.name = "Foo"
        k1.hardware = "Bar"
        k1.admin = user
        k1.put()
        self.b = k1
        return (k, k1)
    
    def create_dummy_session(self):
        sess = SyncSession()
        sess.kiosk = self.a
        sess.client_ref = 'C'
        sess.client_ip = '222.222.222.222'
        sess.data_type = 'Sensor Data'
        sess.put()
        self.sess1 = sess
    
        
    def testUpdateCachedFromDb(self):
        """Updates a session from database, then compares with that in cache."""
        sessq = db.GqlQuery('SELECT * FROM SyncSession WHERE client_ref = :1', 'C')
        sess = sessq.get()
        sess.payload_size = 5
        sess.put()
        sess2 = memcache.get('C', namespace = 'syncsessions')
        self.assertEqual(sess.payload_size, sess2.payload_size)
        self.assertEqual(1, sessq.count())
    
    def testUpdateDbFromCached(self):
        """Updates a session from cache, then checks db for change"""
        sess = memcache.get('C', namespace='syncsessions')
        sess.payload_size = 6
        sess.put()
        sess2q = db.GqlQuery('SELECT * FROM SyncSession WHERE client_ref = :1', 'C')
        sess2 = sess2q.get()
        self.assertEqual(sess2.payload_size, sess.payload_size)
        self.assertEqual(1, sess2q.count())
    
    def testGetByClientRef(self):
        """Checks the class method, get_by_clientref"""
        sess = db.GqlQuery('SELECT * FROM SyncSession WHERE client_ref = :1', 'C').get()
        sess.payload_size = 9
        sess.put()
        sess2 = SyncSession.get_by_clientref('C')
        self.assertEqual(sess.payload_size, sess2.payload_size)
import unittest
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed

from google.appengine.api import users

from data import Heartbeat, Kiosk

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
    
    def testHeartbeatFunctions(self):
        pass
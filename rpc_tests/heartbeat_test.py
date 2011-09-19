#!/bin/python

import simplejson_with_datetime as json
import os.path
import urllib2


from baseconv import BaseConverter

from Crypto.Hash import MD5
from Crypto.PublicKey import RSA

from datetime import datetime
import time

import pickle

import os

DIEID =  '2c6400211ff00000015739eb0c01002d'

START = datetime.utcnow()
UPTIME = 0

def load_RSA():
    if os.path.isfile('prikey.pickle'):
        fh = open('prikey.pickle', 'rb')
        p = pickle.Unpickler(fh)
        key = p.load()
        fh.close()
        return key
    else:
        return generate_RSA()

def generate_RSA():
    fh = open('prikey.pickle', 'wb')
    p = pickle.Pickler(fh)
    key = RSA.generate(512, os.urandom)
    p.dump(key)
    fh.close()
    baseconv = BaseConverter('0123456789abcdef')
    fh2 = open('pubkey.text', 'w')
    fh2.write('Public Key e Parameter\n')
    fh2.write(baseconv.from_decimal(key.publickey().e))
    fh2.write('\nPublic key n Parameter\n')
    fh2.write(baseconv.from_decimal(key.publickey().n))
    fh2.close()
    print "New Key Generated!"
    print "-"*20
    print "pubkey.e : %s" % key.publickey().e
    print ""
    print "pubkey.n : %s" % key.publickey().n
    print "-"*20
    return key

     
def send_heartbeat(url, key):
    json_msg = {}
    json_msg['method'] = 'heartbeat'
    json_msg['id'] = 4
    params = {}
    params['dieid'] = DIEID
    if UPTIME < 60:
        # under a minute
        uptimestr = "%.2f seconds" % UPTIME
    elif UPTIME < 60*60:
        # under a hour
        uptimestr = "%.2f minutes" % (UPTIME/(60.0))
    elif UPTIME < 60*60*24*3:
        # under 3 days
        uptimestr = "%.2f hours" % (UPTIME/(60.0*60.0))
    else:
        # over 3 days
        uptimestr = "%.2f days" % (UPTIME/(60.0*60.0*24.0))
        
    params['uptime'] = uptimestr
    params['sw_version'] = '1.0.0'
    params['time'] = datetime.utcnow()
    json_msg['params'] = params
    jsstr = json.dumps(json_msg)
    hash = MD5.new(jsstr).digest()
    baseconverter = BaseConverter('0123456789abcdef')
    sign_16encode = baseconverter.from_decimal(key.sign(hash, "")[0])
    #print "encoded: %s" % sign_16encode
    #print "signature: %d" % key.sign(hash, "")[0]
    #print "hash: %s"  % "".join(["%02x " % ord(x) for x in hash])
    headers = {'X-eko-signature': sign_16encode}
    print jsstr
    
    #test decoding
    x = key.publickey().verify(hash, (baseconverter.to_decimal(sign_16encode),))
    
    req = urllib2.Request(url, jsstr, headers)
    response = urllib2.urlopen(req)
    the_page = response.read()
    print the_page

def get_messages(url, key):
    json_msg = {}
    json_msg['method'] = 'get_messages'
    json_msg['id'] = 4
    json_msg['params'] = {'dieid': DIEID}
    jsstr = json.dumps(json_msg)
    hash = MD5.new(jsstr).digest()
    baseconverter = BaseConverter('0123456789abcdef')
    sign_16encode = baseconverter.from_decimal(key.sign(hash, "")[0])
    #print "encoded: %s" % sign_16encode
    #print "signature: %d" % key.sign(hash, "")[0]
    #print "hash: %s"  % "".join(["%02x " % ord(x) for x in hash])
    headers = {'X-eko-signature': sign_16encode}
    print jsstr
    
    #test decoding
    x = key.publickey().verify(hash, (baseconverter.to_decimal(sign_16encode),))
    
    req = urllib2.Request(url, jsstr, headers)
    response = urllib2.urlopen(req)
    the_page = response.read()
    print the_page

if __name__ == "__main__":
    key = load_RSA()
    while True:
        uptime = datetime.utcnow() - START
        UPTIME = uptime.total_seconds()
        get_messages('http://www.ekohub.org/api/json', key)
        send_heartbeat('http://www.ekohub.org/api/json', key)
        time.sleep(5)
        
        time.sleep(5)
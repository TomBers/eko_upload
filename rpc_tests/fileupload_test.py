from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2
from baseconv import BaseConverter
from uuid import uuid1
import pickle

DIEID =  '2c6400211ff00000015739eb0c01002d'

def load_RSA():
    fh = open('prikey.pickle', 'rb')
    p = pickle.Unpickler(fh)
    key = p.load()
    fh.close()
    return key

def solve_challenge(challenge):
    baseconv = BaseConverter('0123456789abcdef')
    key = load_RSA()
    signature = key.sign(challenge, "")
    sig_encoded = baseconv.from_decimal(signature[0])
    return sig_encoded

url_req = 'http://localhost:8081/api/upload_request'


if __name__=="__main__":
    register_openers()    
    fh = open('test.manifest.lst', 'rb')
    dh = open('test.data.zip', 'rb')
    datagen, headers = multipart_encode({ 'payload': dh, 'manifest': fh, 'kiosk-id': DIEID,
            'software_version': '1.0.0', 'type':'data', 'reference': uuid1().get_hex()})
    get_target = urllib2.Request(url_req)
    resp_url = urllib2.urlopen(get_target)
    url_targ = resp_url.read().strip()
    
    headers['X-eko-challenge'] = resp_url.headers['X-eko-challenge']
    headers['X-eko-signature'] = solve_challenge(resp_url.headers['X-eko-challenge'])
    
    upload = urllib2.Request(url_targ, datagen, headers)
    response = urllib2.urlopen(upload)
    fh.close()
    dh.close()
    
    print(response.read())
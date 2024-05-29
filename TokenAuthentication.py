from Logger import debug
from cryptography import fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import json
import base64
import random
import time


def salt(len=16):
    chars = '0123456789abcdefhijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return ''.join([random.choice(chars) for x in range(len)])


class TokenAuthentication:
    def __init__(self):
        self.encoder = None

    def create(self, user="", pin="", expires=None, validLength=None, audience=None, info=None):
        if validLength is not None:
            expires = int(time.time() + validLength)
        elif expires is None:
            expires = 0

        if info is None:
            info = ""
        else:
            info = base64.b64encode(json.dumps())

        claims = salt(16) + (",".join(["v2", user, pin, str(expires), info, audience]))
        debug("tokenAuthentication: create: %s", claims)

        return self.encoder.encrypt(claims.encode("utf-8")).decode("utf-8")

    def encode(self, s):
        return self.encoder.encrypt(s.encode("utf-8")).decode("utf-8")

    def decode(self, s):
        return self.encoder.decrypt(s.encode("utf-8")).decode("utf-8")
    
    def verify(self, s, skipTime=False):
        if not s:
            debug("tokenAuthentication: invalid token:<>")
            return None

        try:
            s = self.encoder.decrypt(s.encode("utf-8")).decode("utf-8")
            ss = s[16:]

            r = ss.split(",")
            if r[0] != "v2":
                debug("tokenAuthentication: old style token:<%s>", s)
                return None

            expire = int(r[3])
            if expire == 0:
                skipTime = True
                
            remaining = max(0, expire - int(time.time()))
            info = None if len(r[4]) == 0 else json.loads(base64.b64decode(r[4]))
            result = {"user": r[1], "pin": r[2], "exp": int(expire), "info": info, "aud": r[5], "remaining": remaining}
            rc = result if remaining or skipTime else None
            debug("tokenAuthentication: verify:%s verified=%s", result, rc is not None)

            return rc
        except fernet.InvalidToken:
            debug("tokenAuthentication: invalid token:<%s>", s)
            return None

    def generateKey(self):
        self.key = fernet.Fernet.generate_key()
        self.key_utf8 = self.key.decode("utf-8")

        self.encoder = fernet.Fernet(self.key)
        return self.key_utf8

    def generateKeyFromPassphrase(self, passphrase):
        salt = b'\x065tI\xf4\x94\x00O7\xef\xbe\x12w\xff$\x1a'
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(),
                         length=32,
                         salt=salt,
                         iterations=390000,
                         )

        bPassphrase = passphrase.encode("utf-8")
        self.key = base64.urlsafe_b64encode(kdf.derive(bPassphrase))
        self.key_utf8 = self.key.decode("utf-8")

        self.encoder = fernet.Fernet(self.key)
        return self.key_utf8

    def getKey(self):
        return self.key_utf8

    def getRawKey(self):
        return self.key

    def setKey(self, key):
        self.key_utf8 = key
        self.key = key.encode("utf-8")
        self.encoder = fernet.Fernet(self.key)

        
if __name__ == "__main__":
    t = TokenAuthentication()

    k1 = t.generateKey()
    print("k1:", k1)

    c1 = t.create("GHJKLJ", expires=int(time.time()) + 100, audience="sheet 1")
    print("c1:", c1)

    d1 = t.verify(c1)
    print(d1)

    k2 = t.generateKey()
    print("k2:", k2)

    bad = t.verify(c1)
    print("token good" if bad else "token bad")

    t.setKey(k1)
    d3 = t.verify(c1)
    print(d3)

    n = 1000

    startTime = time.time()
    for i in range(n):
        c = t.create("GHJKLJ", expires=int(time.time()) + 100, audience="sheet 1")
    endTime = time.time()

    diff = endTime - startTime
    print("create ops:", n / diff)

    startTime = time.time()
    for i in range(n):
        d = t.verify(c)
    endTime = time.time()

    diff = endTime - startTime
    print("verify ops:", n / diff)

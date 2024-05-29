from Logger import error
import os
import time
import datetime
from OpenSSL import crypto
from Utils import updateNumberedBackupFiles


def generateSSLCertificate(domain="local", address="address", certificateFile="ssl.crt", keyFile="ssl.key", country="CA", region="BC", city="somewhere", organization="club", unit="unit", email="admin", hosts=None):
    hostStr = ""
    # generate alt names for hosts
    if hosts:
        hostStr = ' -addext "subjectAltName=' + ",".join([f"DNS:{host}.{domain}" for host in hosts]) + '"'
    
    cmd = f'openssl req -newkey rsa:2048 -x509 -sha256 -days 366 -out {certificateFile}.tmp -keyout {keyFile}.tmp -nodes -subj "/C={country}/ST={region}/L={city}/O={organization}/OU={unit}/CN={address}/emailAddress={email}"' + hostStr

    print(cmd)

    startTime = time.time()
    p = os.system(cmd)
    elapsed = time.time() - startTime

    print(f"running = {elapsed} rc={p}")
    if p != 0:
        print("failed to create ssl certificates")
        return None

    try:
        updateNumberedBackupFiles([[certificateFile + ".tmp", certificateFile],
                                   [keyFile + ".tmp", keyFile]])
    except OSError as e:
        print(e)
        return False

    # openssl x509 -noout -text -in ssl.crt
    return True


def dumpSSLCertificate(path, filename="ssl.crt"):
    certificateFile = filename if path is None else os.path.join(path, filename)
    
    with open(certificateFile, "r") as f:
        cert_buf = f.read()

    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_buf)

    ci = CertInfo(cert)
    ci.print()
    
    return True


def getInfoSSLCertificate(path, filename="ssl.crt"):
    certificateFile = filename if path is None else os.path.join(path, filename)
    
    with open(certificateFile, "r") as f:
        cert_buf = f.read()

    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_buf)

    ci = CertInfo(cert)
    return ci.info()


class CertInfo:
    def __init__(self, cert=None):
        self.cert = cert

    def decode_x509name_obj(self, o):
        parts = []
        for c in o.get_components():
            parts.append(c[0].decode('utf-8') + '=' + c[1].decode('utf-8'))
        return ', '.join(parts)

    def cert_date_to_gmt_date(self, d):
        return datetime.datetime.strptime(d.decode('ascii'), '%Y%m%d%H%M%SZ')

    def cert_date_to_gmt_date_string(self, d):
        return self.cert_date_to_gmt_date(d).strftime("%Y-%m-%d %H:%M:%S GMT")

    def get_item(self, item, extension=None, return_as=None, algo=None):
        try:
            if item == 'subject':
                return self.decode_x509name_obj(self.cert.get_subject())

            elif item == 'subject_o':
                return self.cert.get_subject().O.strip()

            elif item == 'subject_cn':
                return self.cert.get_subject().CN.strip()

            elif item == 'extensions':
                ext_count = self.cert.get_extension_count()
                if extension is None:
                    ext_infos = []
                    for i in range(0, ext_count):
                        ext = self.cert.get_extension(i)
                        ext_infos.append(ext.get_short_name().decode('utf-8'))
                    return ext_infos

                for i in range(0, ext_count):
                    ext = self.cert.get_extension(i)
                    if extension in str(ext.get_short_name()):
                        return ext.__str__().strip()
                return None

            elif item == 'version':
                return self.cert.get_version()

            elif item == 'pubkey_type':
                pk_type = self.cert.get_pubkey().type()
                if pk_type == crypto.TYPE_RSA:
                    return 'RSA'
                elif pk_type == crypto.TYPE_DSA:
                    return 'DSA'
                return 'Unknown'

            elif item == 'pubkey_pem':
                return crypto.dump_publickey(crypto.FILETYPE_PEM, self.cert.get_pubkey()).decode('utf-8')

            elif item == 'serial_number':
                return self.cert.get_serial_number()

            elif item == 'not_before':
                not_before = self.cert.get_notBefore()
                if return_as == 'string':
                    return self.cert_date_to_gmt_date_string(not_before)
                return self.cert_date_to_gmt_date(not_before)

            elif item == 'not_after':
                not_after = self.cert.get_notAfter()
                if return_as == 'string':
                    return self.cert_date_to_gmt_date_string(not_after)
                return self.cert_date_to_gmt_date(not_after)

            elif item == 'has_expired':
                return self.cert.has_expired()

            elif item == 'issuer':
                return self.decode_x509name_obj(self.cert.get_issuer())

            elif item == 'issuer_o':
                return self.cert.get_issuer().O.strip()

            elif item == 'issuer_cn':
                return self.cert.get_issuer().CN.strip()

            elif item == 'signature_algorithm':
                return self.cert.get_signature_algorithm().decode('utf-8')

            elif item == 'digest':
                # ['md5', 'sha1', 'sha256', 'sha512']
                return self.cert.digest(algo)

            elif item == 'pem':
                return crypto.dump_certificate(crypto.FILETYPE_PEM, self.cert).decode('utf-8')

            else:
                return None

        except Exception as e:
            error('ssl error: item = %s, exception, e = %s', item, e)
            return None

    @property
    def subject(self):
        return self.get_item('subject')

    @property
    def subject_o(self):
        return self.get_item('subject_o')

    @property
    def subject_cn(self):
        return self.get_item('subject_cn')

    @property
    def subject_name_hash(self):
        return self.get_item('subject_name_hash')

    @property
    def extension_count(self):
        return self.get_item('extension_count')

    @property
    def extensions(self):
        return self.get_item('extensions')

    @property
    def extension_basic_constraints(self):
        return self.get_item('extensions', extension='basicConstraints')

    @property
    def extension_subject_key_identifier(self):
        return self.get_item('extensions', extension='subjectKeyIdentifier')

    @property
    def extension_authority_key_identifier(self):
        return self.get_item('extensions', extension='authorityKeyIdentifier')

    @property
    def extension_subject_alt_name(self):
        return self.get_item('extensions', extension='subjectAltName')

    @property
    def version(self):
        return self.get_item('version')

    @property
    def pubkey_type(self):
        return self.get_item('pubkey_type')

    @property
    def pubkey_pem(self):
        return self.get_item('pubkey_pem')

    @property
    def serial_number(self):
        return str(self.get_item('serial_number'))

    @property
    def not_before(self):
        return self.get_item('not_before')

    @property
    def not_before_s(self):
        return self.get_item('not_before', return_as='string')

    @property
    def not_after(self):
        return self.get_item('not_after')

    @property
    def not_after_s(self):
        return self.get_item('not_after', return_as='string')

    @property
    def has_expired(self):
        return self.get_item('has_expired')

    @property
    def issuer(self):
        return self.get_item('issuer')

    @property
    def issuer_o(self):
        return self.get_item('issuer_o')

    @property
    def issuer_cn(self):
        return self.get_item('issuer_cn')

    @property
    def signature_algorithm(self):
        return self.get_item('signature_algorithm')

    @property
    def digest_sha256(self):
        return self.get_item('digest', algo='sha256')

    @property
    def pem(self):
        return self.get_item('pem')

    def info(self, cert_items=None):
        data = [
            ('Subject', self.subject),
            ('Subject-CN', self.subject_cn),
            ('Subject name hash', self.subject_name_hash),
            ('Issuer', self.issuer),
            ('Issuer-CN', self.issuer_cn),
            ('Extensions', ', '.join(self.extensions)),
            ('Extension-basicConstraints', self.extension_basic_constraints),
            ('Extension-subjectKeyIdentifier', self.extension_subject_key_identifier),
            ('Extension-authorityKeyIdentifier', self.extension_authority_key_identifier),
            ('Extension-subjectAltName (SAN)', self.extension_subject_alt_name),
            ('Version', self.version),
            ('Serial_number', self.serial_number),
            ('Public key-type', self.pubkey_type),
            ('Public key-pem', self.pubkey_pem),
            ('Not before', self.not_before_s),
            ('Not after', self.not_after_s),
            ('Has expired', self.has_expired),
            ('Signature algortihm', self.signature_algorithm),
            ('Digest-sha256', self.digest_sha256.decode("utf-8")),
            ('PEM', self.pem),
        ]

        if cert_items:
            data = data.filter(lambda x: x[0], cert_items)

        return data
        
    def print(self):
        info = self.info()
        print('\n'.join([f"{n}: {v}" for n, v in info]))
        

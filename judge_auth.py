"""Expiring HTTPS Basic auth. Configure a hash of a random password; never log it."""
import base64
import hashlib
import hmac
import os
import re
import time

def authorize(event, now=None):
    if os.environ.get('CAPTUREGATE_JUDGE_AUTH') != 'required':
        context=event.get('requestContext') or {}
        if isinstance(context,dict) and context.get('apiId'):
            return 503,'Judge access is not configured.'
        return None
    digest=os.environ.get('CAPTUREGATE_JUDGE_PASSWORD_SHA256','')
    try: expires=int(os.environ.get('CAPTUREGATE_JUDGE_EXPIRES','0'))
    except ValueError: expires=0
    if not re.fullmatch(r'[0-9a-f]{64}',digest) or expires<=0:
        return 503,'Judge access is not configured.'
    if (time.time() if now is None else now)>=expires:
        return 403,'This judge demonstration has expired.'
    headers=event.get('headers') or {}
    if not isinstance(headers,dict):return 401,'Judge credentials required.'
    values=[v for k,v in headers.items() if isinstance(k,str) and k.lower()=='authorization']
    try:
        if len(values)!=1 or not isinstance(values[0],str) or len(values[0])>1024:raise ValueError()
        scheme,encoded=values[0].split(' ',1)
        if scheme.lower()!='basic':raise ValueError()
        user,password=base64.b64decode(encoded,validate=True).decode('utf-8').split(':',1)
        correct=hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(),digest)
        if user!='judges' or not correct:raise ValueError()
    except (ValueError,UnicodeError):return 401,'Judge credentials required.'
    return None

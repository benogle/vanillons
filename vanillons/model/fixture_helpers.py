"""
To help you writing tests. Should be able to create each type of object in the system
with no other inputs. 
"""
from vanillons.model import Session, users
from pylons_common.lib import utils

def create_unique_str(pre=u'', extra=u"\u00bf"):
    """
    @param pre: The string to prefix the unique string with. Defaults to
                nothing.
    @param extra: The string to append to the unique string. Default to a
                  unicode character.
    @return: A unique string.
    """
    return u"%s%s%s" % (pre, utils.uuid(), extra)

def create_email_address():

    return create_unique_str(u'email') + u"@email.com"

def create_str(length=None):
        
        letters = ' abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        key = []
        
        l = length or random.randint(30, 50)
        
        for i in range(l):
            key.append(letters[random.randint(0, len(letters)-1)])
        
        return ''.join(key)

def create_user(is_admin=False, **kw):

    kw.setdefault("email", create_email_address())
    kw.setdefault("username", create_unique_str(u'user', extra=u''))
    kw.setdefault("password", u'testpassword')
    
    if is_admin:
        kw.setdefault("role", users.ROLE_ADMIN)
    else:
        kw.setdefault("role", users.ROLE_USER)

    user = users.User(**kw)
    Session.add(user)
    Session.flush()
    return user
from adroll.api import enforce, logger, h, validate
from adroll.utils import errors
from adroll.model import Session
from adroll.model.users import Organization, User, ROLE_USER, ROLE_ADMIN, ROLE_ENGINEER
from adroll.model.api import ApiCall
import sqlalchemy as sa
from adroll import utils

import formencode
import formencode.validators as fv

@enforce(key=unicode, value=unicode, use_actual_user=bool)
def set_pref(actual_user, user, key, value, use_actual_user=True):
    
    class Pref(formencode.Schema):
        key     = fv.MaxLength(64, not_empty=True)
        value   = fv.MaxLength(64, not_empty=False)
    scrubbed = validate(Pref, key=key, value=value)
    
    u = user
    if use_actual_user:
        u = actual_user
    u.set_preference(scrubbed.key, scrubbed.value or '')

def generate_password():
    return utils.uuid()[:8]

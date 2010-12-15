from vanillons.api import authorize, enforce, FieldEditor, convert_date
from vanillons.model import fixture_helpers as fh, Session, users
from vanillons import api
from vanillons.tests import *

from datetime import datetime, timedelta

import formencode
import formencode.validators as fv

from pylons_common.lib.exceptions import *

class TestUser(TestController):
    
    def test_set_pref(self, admin=False):
        pass


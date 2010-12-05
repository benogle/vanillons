from vanillons.lib.base import *
from vanillons.model import users
from vanillons import api

from pylons_common.lib.exceptions import *

import formencode
import formencode.validators as fv

class TestController(BaseController):
    """
    A controller that has middleware exercise actions.
    """
    
    def qunit(self):
        return self.render('/test/qunit.html');
    
    def async_exercise(self):
        return self.render('test/async_exercise.html');
    
    @async
    def rando_form(self, **_):
        """
        A dumb form handler that makes two queries.
        
        The middleware tests use this, so be careful changing.
        """
        
        class RandoForm(formencode.Schema):
            a_number = fv.Int(not_empty=True)
            a_string = formencode.All(fv.UnicodeString(not_empty=True), fv.MaxLength(20))
        
        scrubbed = self.validate(RandoForm, **dict(request.params))
        
        #useless queries
        Session.query(users.User).all()
        Session.query(users.User).all()
        
        Session.query(users.UserPreference).filter_by(user_id=1).all()
        
        return dict(scrubbed)
    
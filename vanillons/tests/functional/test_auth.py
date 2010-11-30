from datetime import date, timedelta

from vanillons.model import users
from vanillons.tests import *
#import vanillons.model.fixture_helpers as fh

#from adroll.dotcom.controllers.account import SALT
#import hashlib

class TestAccountController(TestController):
    def test_all(self):
        
        # test registering
        response = self.get(url_for(controller='auth', action='register'))
        assert "auth_register" in response

        username = u'test@example.com'
        post_vars = {'default_timezone' : u'-8', 'password' : u'secret', 'confirm_password' : u'secret', 'email' : username}
        response = self.client_async(url_for(controller='auth', action='register'), post_vars)
        response = response.results.url == '/'
        
        user = Session.query(users.User).filter_by(username=username).first()
        assert user
        
        response = self.get(url_for(controller='index', action='index'))
        assert username in response and 'user-logged-in' in response
        
        response = self.get(url_for(controller='auth', action='login'), status=302).follow()
        
        response = self.get(url_for(controller='auth', action='logout'), status=302).follow()
        assert username not in response and 'user-logged-in' not in response
        
        response = self.get(url_for(controller='auth', action='login'), status=200)
        response = self.post(url_for(controller='auth', action='login'), {'username':username, 'password': 'secret'}).follow()
        assert username in response and 'user-logged-in' in response
        
        response = self.get(url_for(controller='index', action='index'))
        assert username in response and 'user-logged-in' in response
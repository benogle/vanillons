from vanillons.api import auth, enforce, FieldEditor
from vanillons.lib.exceptions import ApiValueException
from vanillons.lib import exceptions
from vanillons.model import fixture_helpers as fh, Session, users
from vanillons import api
from vanillons.tests import TestController

from datetime import datetime, timedelta

import formencode
import formencode.validators as fv

#
## @auth
#

@auth(check_admin=True)
def auth_admin_fn(user):
    return True

@auth(must_own='ad')
def auth_owns_fn_user(user, ad):
    return True

@auth(must_own='ad')
def auth_owns_fn_actual_user(actual_user, ad):
    return True

@auth(must_own='ad')
@enforce(user=users.User, ad=advertisers.Ad)
def auth_enforce_owns_fn(user, ad):
    return True

class TestInit(TestController):

    def _create_ad_user(self, make_admin=False):
        u = make_admin and fh.create_admin() or fh.create_user()
        
        adv = fh.create_advertisable(user=u)
        self.flush()
        
        orig_ad = fh.create_ad(advertisable=adv, name=u"test_ad", destination_url=u"http://example.com")
        self.flush()
        
        return u, adv, orig_ad
    
    def test_auth_admin(self):
        u = fh.create_user()
        adm = fh.create_admin()
        
        assert auth_admin_fn(adm)
        assert self.throws_exception(lambda: auth_admin_fn(u)).code == errors.FORBIDDEN

    def test_auth_owns_pretend(self):
        u, adv, ad = self._create_ad_user()
        
        rando = fh.create_user()
        u2 = fh.create_user()
        adm = fh.create_admin()
        
        assert auth_owns_fn_user(u, ad)
        assert auth_owns_fn_actual_user(u, ad)
        assert auth_enforce_owns_fn(u, ad)
        assert auth_owns_fn_user(adm, ad)
        
        assert self.throws_exception(lambda: auth_owns_fn_user(u2, ad)).code == errors.FORBIDDEN
        assert self.throws_exception(lambda: auth_enforce_owns_fn(u2, ad)).code == errors.FORBIDDEN
    
    def test_enforce_datetime(self):
        
        @enforce(somedate=datetime)
        def fn(somedate):
            assert type(somedate) is datetime
        
        fn(datetime(2002, 4, 5))
        fn(u'5-3-2010')
        fn(u'Jul 3, 2030')
        fn(u'2010-3-23 23:23:56')
        
        assert self.throws_exception(lambda: fn(u'June 3rd 2030 23:23:56'), types=(ApiValueException,)).code == errors.INVALID
    
    def test_field_editor(self):
        
        u = fh.create_user()
        adm = fh.create_admin()
        
        class SomeForm(formencode.Schema):
            things = fv.Number(not_empty=False, min=0)
            yo_mammas = fv.Int(not_empty=False, min=0)
            admin_only = fv.Int(not_empty=False, min=0)
            error_1 = fv.UnicodeString(not_empty=False)
            error_2 = fv.UnicodeString(not_empty=False)
        
        edit_fields = ['things', 'yo_mammas', 'error_1', 'error_2']
        admin_edit_fields = ['admin_only']
        
        class Editor(FieldEditor):
            def __init__(self):
                super(Editor, self).__init__(edit_fields, admin_edit_fields, SomeForm)
            
            def edit_error_1(self, actual_user, user, obj, key, value):
                raise errors.ClientException('error_1')
            def edit_error_2(self, actual_user, user, obj, key, value):
                raise errors.ClientException('error_2')
            
            def edit_things(self, actual_user, user, obj, key, value):
                assert actual_user
                assert user
                assert key == 'things'
                obj['things'] = value
            
            def edit_random(self, actual_user, user, obj, key, value):
                obj['random'] = value
            
            def edit_admin_only(self, actual_user, user, obj, key, value):
                assert key == 'admin_only'
                obj['admin_only'] = value
            
            #not defining yo_mammas intentionally
        
        editor =  Editor()
        
        #basic case, non admin
        obj = {}
        editor.edit(u, u, obj, things='3.0')
        assert obj['things'] == 3.0
        
        obj = {}
        editor.edit(u, u, obj, key='things', value='4.0')
        assert obj['things'] == 4.0
        
        #basic case, admin, multiple fields
        obj = {}
        editor.edit(adm, u, obj, things='5.0', admin_only=34)
        assert obj['things'] == 5.0
        assert obj['admin_only'] == 34
        
        #FAIL case, non-admin. will not edit admin!
        obj = {}
        editor.edit(u, u, obj, things='5.0', admin_only=34)
        assert obj['things'] == 5.0
        assert 'admin_only' not in obj
        
        # should not run the validator on the admin_only field
        editor.edit(u, u, obj, things='5.0', admin_only='dont breaK!')
        assert obj['things'] == 5.0
        assert 'admin_only' not in obj
        
        ce = (errors.ClientException,)
        
        #FAIL case, empty
        assert self.throws_exception(lambda: editor.edit(u, u, obj), types=ce).code == errors.INCOMPLETE
        
        #FAIL case, dont edit random stuff we dont care about
        obj = {}
        assert self.throws_exception(lambda: editor.edit(u, u, obj, random='poo'), types=ce).code == errors.INCOMPLETE
        assert not obj
        assert self.throws_exception(lambda: editor.edit(u, u, obj, admin_only='poo'), types=ce).code == errors.INCOMPLETE
        assert not obj
        editor.edit(u, u, obj, things=4.5, random='poo')
        assert 'things' in obj
        assert 'random' not in obj
        editor.edit(u, u, obj, things=4.5, random_foo='poo')
        assert 'things' in obj
        assert 'random_foo' not in obj
        
        #this cant call the function cause it isnt defined
        obj = {}
        assert self.throws_exception(lambda: editor.edit(u, u, obj, yo_mammas='2'), types=(errors.AdrollException,)).code == errors.INCOMPLETE
        
        exc = self.throws_exception(lambda: editor.edit(u, u, obj, error_1='blah', error_2='blah'), types=(errors.CompoundException,))
        assert exc.has_exceptions
        assert len(exc.exceptions) == 2
        assert 'error_1' in [e.msg for e in exc.exceptions]
        assert 'error_2' in [e.msg for e in exc.exceptions]
        
        ##
        #validation!
        ##
        
        i = (formencode.validators.Invalid,)
        exc = self.throws_exception(lambda: editor.edit(u, u, obj, things='asd', yo_mammas='qw'), types=i)
        assert exc
        assert len(exc.error_dict.keys()) == 2
        assert 'things' in exc.error_dict.keys()
        assert 'yo_mammas' in exc.error_dict.keys()

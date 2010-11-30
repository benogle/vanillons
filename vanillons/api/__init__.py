from vanillons.weblib.base import h, logger
from vanillons.lib import exceptions
from vanillons.model import Session, users
import sqlalchemy as sa

from vanillons.lib.utils import objectify
from vanillons.lib.exceptions import ApiValueException

import formencode.validators as fv

"""
    @enforce MUST be specified before @auth on your api functions. @enforce will convert strings to
    proper DB objects when coming in from the web service. @auth relies on there being proper DB
    objects to do must_own authorization.
"""

DATE_FORMAT_ACCEPT = [u'%Y-%m-%d %H:%M:%S', u'%Y-%m-%d', u'%m-%d-%Y', u'%m/%d/%Y', u'%m.%d.%Y', u'%b %d, %Y']

def zipargs(decorated_fn):
    """
    This will zip up the positional args into kwargs. This makes handling them in
    decorators easier. Call on the inner deocrator function, and pass in the outer's
    arg. Outer function must be @stackable. Convolution. Apologies.
    """
    def decorator(fn):
        def new(*args, **kwargs):
            
            # Get the original func's param names. If this is the outer decorator, decorated_fn.func_code.co_varnames
            # will have the inner decorator's names ('args', 'kwargs'). The inner decorator should
            # attach original_varnames to the function
            varnames = hasattr(decorated_fn, 'original_varnames') and decorated_fn.original_varnames or decorated_fn.func_code.co_varnames
            
            dargs = dict(zip(varnames, args))
            dargs.update(kwargs)
            
            return fn(**dargs)
        
        return new
    
    return decorator

def stackable(fn):
    """
    This will make a decorator 'stackable' in that we can get the original function's params.
    """
    def new(*args, **kwargs):
        
        decorated_fn = args[0]
        newfn = fn(*args, **kwargs)
        if decorated_fn:
            # We need to pass the original_varnames into every fn we return in these decorators so
            # the dispatch controller has access to the original function's arg names.
            # Do this in @auth due to decorator stacking.
            newfn.func_name = decorated_fn.func_name
            newfn.original_varnames = hasattr(decorated_fn, 'original_varnames') and decorated_fn.original_varnames or decorated_fn.func_code.co_varnames
        return newfn
    
    return new

##
### Decorators for api functions
##

def enforce(**types):
    """
    Assumes all arguments are unicode strings, and converts or resolves them to more complex objects.
    If a type of the form [Type] is specified, the arguments will be interpreted as a comma-delimited
    list of strings that will be converted to a list of complex objects. 
    """
    
    # there is probably a fancy python way to do this...
    types.setdefault('user', users.User)
    types.setdefault('real_user', users.User)
    
    from datetime import datetime
    
    @stackable
    def decorator(fn):
        
        @zipargs(fn)
        def new(**kwargs):
            import sqlalchemy as sa

            errors = []
            
            def convert(arg_name, arg_type, arg_value):
                converted_value = arg_value
                try:
                    if arg_type is file:
                        if type(arg_value) is not file:
                            if hasattr(arg_value, 'file'):
                                converted_value = arg_value.file
                            else:
                                raise ValueError("Value must be an open file object, or uploaded file.")
                    if arg_type == 'filedict':
                        if type(arg_value) is not dict:
                            if hasattr(arg_value, 'file'):
                                converted_value = {'file': arg_value.file}
                            else:
                                raise ValueError("Value must be an open file object, or uploaded file.")
                            
                            if hasattr(arg_value, 'filename'):
                                converted_value['filename'] = arg_value.filename
                    elif arg_type is int:
                        converted_value = int(arg_value)
                    elif arg_type is float:
                        converted_value = float(arg_value)
                    elif arg_type is datetime:
                        converted_value = convert_date(arg_value)
                    elif type(arg_type) is sa.ext.declarative.DeclarativeMeta:
                        if type(type(arg_value)) is not sa.ext.declarative.DeclarativeMeta:
                            
                            is_int = True
                            try:
                                arg_value = int(arg_value)
                            except ValueError, e:
                                is_int = False
                            
                            if not is_int and hasattr(arg_type, 'eid'):
                                field = arg_type.eid
                                if arg_value is str:
                                    arg_value = arg_value.decode('utf-8')
                                else:
                                    arg_value = unicode(arg_value)
                            else:
                                field = arg_type.id
                                arg_value = int(arg_value)
                            converted_value = Session.query(arg_type).filter(field == arg_value).first() 
                    elif arg_type is str:
                        if type(arg_value) is unicode:
                            converted_value = arg_value.encode('utf-8')
                        else:
                            converted_value = str(arg_value)
                    elif arg_type is unicode:
                        if type(arg_value) is str:
                            converted_value = arg_value.decode('utf-8')
                        else:
                            converted_value = unicode(arg_value)
                    elif arg_type is bool:
                        if type(arg_value) is not bool:
                            arg_value = arg_value.encode('utf-8').lower()
                            if arg_value in ['t','true','1','y','yes','on']:
                                converted_value = True
                            elif arg_value in ['f','false','0','n','no']:
                                converted_value = False
                            else:
                                raise ValueError('Value must be true or false')
                except (ValueError, TypeError), e:
                    errors.append((e, arg_name, arg_value))
                
                return converted_value

            for name, value in kwargs.iteritems():
                if name in types and value is not None:             
                    t = types[name]
                    if type(type(value)) is sa.ext.declarative.DeclarativeMeta or isinstance(value, list):
                        kwargs[name] = convert(name, t, value)
                    # If the type is a list, this means that we want to 
                    # return a list of objects of the type at index 0 in the list                        
                    elif isinstance(t, list):
                        if not isinstance(value, list):
                            list_of_values = [s for s in value.split(',') if s]
                            converted_values = []
                            t = t[0]
                            for v in list_of_values:
                                converted_values.append(convert(name, t, v))
                        # If the value was already a list, then it must have
                        # been a list of DB objects, so we didn't need to touch it                       
                        kwargs[name] = converted_values
                    else:
                        kwargs[name] = convert(name, t, value)
            if errors:
                raise ApiValueException([{'value': str(e[2]), 'message':str(e[0]), 'field': e[1]} for e in errors], exceptions.INVALID)
            else:
                return fn(**kwargs)
            
        return new
    return decorator

def auth(must_own=None, must_own_if_present=None, check_admin=False, has_role=None):
    
    """
    Authorization checking. Will make sure the user is an admin if you want. And it will verify
    ownership of a db object or multiple db objects.
    
    :param must_own: a string name of a parameter which will have the object to validate. This can be a list.
    """
    @stackable
    def decorator(fn):
        
        @zipargs(fn)
        def new(**kwargs):
            from adroll.model import errors
            
            # find the user
            user = kwargs.get('real_user') or kwargs.get('user')
            if user is None:
                try:
                    user = h.get_real_user()
                except TypeError, e:
                    user = None
            
            if not user:
                raise exceptions.ClientException("@auth must have access to a user for authorization. Specify user in the function arguments.", exceptions.INCOMPLETE,field='user')
            
            if must_own:
                # user.must_own takes a list of objects. This allows the user to pass in a single
                # param name, or multiple names.
                mo = must_own
                if not isinstance(mo, list) and not isinstance(mo, tuple):
                    mo = [mo]
                
                #pull the objects that correspond to the param names from the function's args.
                mo_obj_list = []
                for var in mo:
                    if var not in kwargs:
                        raise exceptions.ClientException("Parameter '%s' not found in function arguments." % (var), exceptions.NOT_FOUND, field=var)
                    mo_obj_list.append(kwargs[var])
                
                user.must_own(*mo_obj_list)
            
            if must_own_if_present:
                # user.must_own takes a list of objects. This allows the user to pass in a single
                # param name, or multiple names.
                mo = must_own_if_present
                if not isinstance(mo, list) and not isinstance(mo, tuple):
                    mo = [mo]
                
                #pull the objects that correspond to the param names from the function's args.
                mo_obj_list = []
                for var in mo:
                    if var in kwargs and kwargs[var] != None:
                        mo_obj_list.append(kwargs[var])
                
                if mo_obj_list:
                    user.must_own(*mo_obj_list)
            
            elif check_admin:
                if not user.is_admin():
                    raise exceptions.ClientException("User must be an admin", exceptions.FORBIDDEN)

            if has_role:
                if user.role != has_role:
                    raise exceptions.ClientException("User must be in role %s" % has_role, exceptions.FORBIDDEN)
            
            return fn(**kwargs)
            
        return new
    return decorator

def convert_date(value):
    from datetime import datetime
    
    if not value:
        return None
    
    if isinstance(value, datetime):
        return value
    
    def try_parse(val, format):
        try:
            dt = datetime.strptime(val, format)
        except ValueError:
            dt = None
        return dt
    
    converted_value = None
    for format in DATE_FORMAT_ACCEPT:
        converted_value = converted_value or try_parse(value, format)
    if not converted_value:
        raise ValueError('Cannot convert supposed date %s' % value)
    
    return converted_value

class ConvertDate(fv.FancyValidator):
    def _to_python(self, value, state):
        
        try:
            value = convert_date(value)
        except (ValueError,), e:
            raise fv.Invalid(e.args[0], value, state)
        
        return value

class FieldEditor(object):
    """
    The edit functions for a given object are big and tend to be error prone.
    This class allows you to just specify a validator class, the params you want
    to edit, and some functions to edit those params.
    
    This class will handle editing of one variable at a time, it will catch and
    package up multiple errors, and it will do general authorization.
    
    You just extend it and add your edit functions with name edit_<param_name>
    Then you instantiate and call edit(). Example function:
    
    def edit_budget(actual_user, user, campaign, key, value):
        raise exceptions.ClientException('OMG bad shit is happening!', field=key)
    
    'key' would be 'budget'
    
    Notes:
    
    * If the user is not an admin and he tries ot edit an admin field, the editor
      will just ignore the field as if he had not specified it.
    * Your editing can work one param at a time.
      so /api/v1/campaign/edit?name=my+name
      /api/v1/campaign/edit?key=name&value=my+name are equivalent
    * Your field editing functions can be passed None
      so /api/v1/campaign/edit?cpc= would unset the CPC.
      If you dont want to accept None, check for it in your edit_ function, not
      in the validator.
    * You must do object ownership authorization outside of this editor. The only
      auth this thing does is an admin check for the editing of admin fields.
      Use the @auth(must_own='asd') on your edit api function.
    * Your edit_ functions can raise ClientExceptions. They will be packaged up in
      a CompoundException and be returned to the client side as a collection.
      If you raise an AdrollException, it will get through to the error middleware.
    """
    
    def __init__(self, fields, admin_fields, validator):
        self.validator = validator
        self.fields = fields
        self.admin_fields = admin_fields
    
    def _edit_generic(self, name, obj, key, param, can_be_none=True):
        if not can_be_none and param == None:
            raise exceptions.ClientException('Please enter a %s' % name, field=key)
        
        old = getattr(obj, key)
        setattr(obj, key, param)
        self.log(name, key, old, getattr(obj, key))
    
    def log(self, field, key, old_val, new_val):
        logger.info('%s edited by %s: %s (%s) = %s from %s' % (self.object, self.actual_user, field, key, new_val, old_val))
    
    def edit(self, actual_user, user, obj, key=None, value=None, **kwargs):
        
        self.actual_user = actual_user
        self.user = user
        self.object = obj
        self.params = kwargs
        
        # for the single field edit
        if key and value != None and key not in kwargs:
            kwargs[key] = value
        
        # There is no authorization check in here. This is effectively it.
        # If the user is not an admin, the admin fields are stripped out. 
        editable_keys = set(actual_user.is_admin() and (self.fields + self.admin_fields) or self.fields)
        
        # is there anything we can edit?
        to_edit = [k for k in kwargs.keys() if k in editable_keys]
        if not to_edit:
            raise exceptions.ClientException('Specify some parameters to edit, please.', code=exceptions.INCOMPLETE)
        
        # we fill out the kwargs so we dont piss off the validator. hack. poo. Must have all
        # fields as the validator will too.
        for k in self.fields + self.admin_fields:
            if k not in kwargs or k not in editable_keys:
                kwargs[k] = None
        
        params = validate(self.validator, **kwargs)
        
        #this is for collecting errors. 
        error = exceptions.CompoundException('Editing issues!', code=exceptions.FAIL)
        
        # only go through the keys that we got in the original call/request (to_edit)
        for k in to_edit:
            if k not in editable_keys: continue
            param = params[k]
            
            fn_name = 'edit_%s' % k
            if hasattr(self, fn_name):
                
                try:
                    results = getattr(self, fn_name)(actual_user, user, obj, k, param)
                except exceptions.ClientException, e:
                    # if error from editing, we will package it up so as to
                    # return all errors at once
                    error.add(e)
            else:
                #this is an adroll exception cause it should bubble up to a WebApp email
                raise exceptions.AppException('Cannot find %s edit function! :(' % fn_name, code=exceptions.INCOMPLETE)
        
        if error.has_exceptions:
            raise error
        
        Session.flush()
        
        return True

import user

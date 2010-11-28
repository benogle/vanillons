from vanillons.api import enforce, logger, validate, h, auth

"""
This module just creates errors. It is useful for blackbox testing the api
(and our middleware)'s error handling abilities
"""

ERROR_TYPES = ['adroll', 'value', 'type', 'validation', 'balloffire']

@enforce(type=unicode)
@auth(check_admin=True)
def explode(actual_user, user, type):
    
    if type == 'adroll':
        raise errors.AdrollException('This is an AdrollException', errors.FAIL)
    elif type == 'value':
        a = int('zzz')
    elif type == 'type':
        from decimal import Decimal
        a = 2.45 + Decimal('3.4')
    elif type == 'validation':
        class Rawr(formencode.Schema):
            meow = fv.Number()
        scrubbed = validate(Rawr, meow='zzzz')
    elif type == 'balloffire':
        1/0
    
    return "This shouldn't pass!! What are you doing!?!?"

@enforce(error=unicode)
def jserror(actual_user, user, error):
    
    logger.info('JS ERROR! actual %s; %s with error: %s' % (actual_user, user, error))
    
    return True
    
    
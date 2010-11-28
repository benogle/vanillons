"""The base Controller API

Provides the BaseController class for subclassing.
"""
from pylons import tmpl_context as c, config, app_globals as g, request, response, session

from formencode import htmlfill
import formencode

#careful with the imports. Controllers import * from here...
from pylons.controllers import WSGIController
from pylons.templating import render_mako as render

from vanillons.model.meta import Session

class BaseController(WSGIController):

    def render(self, *args, **kw):
        return render_response(*args, **kw)
    
    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']
        try:
            request.environ['USER'] = session.get('username', '')
            request.environ['REAL_USER'] = session.get('real_username', '')
            
            # set the start of the rendering
            c.render_start = time.time()
            
            c.requested_url = request.environ.get('PATH_INFO')
            if request.environ.get('QUERY_STRING'):
                c.requested_url += '?' + request.environ['QUERY_STRING']
            logger.info(c.requested_url)

            # Capture IP address in non-ssl mode, so we can use it in SSL mode see ticket #2275
            ip = h.get_user_ip()
            if not session.get('IP_ADDRESS') and ip:
                session['IP_ADDRESS'] = ip
            elif not session.get('IP_ADDRESS') and request.environ.get('HTTP_RLNCLIENTIPADDR'):
                session['IP_ADDRESS'] = request.environ.get('HTTP_RLNCLIENTIPADDR')
            elif not session.get('IP_ADDRESS') and request.environ.get('REMOTE_ADDR'):
                session['IP_ADDRESS'] = request.environ.get('REMOTE_ADDR')
            
            # Save the first referer we see to store in user record when/if we create one.
            if not session.get('referer'):
                session['referer'] = environ.get('HTTP_REFERER','').decode('utf-8','ignore')
                session.save()
                
            return WSGIController.__call__(self, environ, start_response)
        finally:
            Session.remove()
    
    def _set_session_for_flash_uploads(self):
        '''
        For flash uploads, flash does not pass the cookie forward.
        So, I do it in a request param, then do this crap to reset the proper
        session.
        
        http://groups.google.com/group/pylons-discuss/browse_thread/thread/7814b72df58f788b?pli=1
        '''
        if 'session_cookie' in request.params:

            cookie = request.params['session_cookie']

            logger.info("BF3: Got session cookie '%s', resetting session...." % cookie)

            session_id = str(cookie)
            newsession = session.get_by_id(session_id)

            # Normal pylons session behavior creates a temporary session if none exists.
            # If we don't do that here, and no session exists (such as right after the session store (memcached)
            # is restarted, and one tries to upload a logo w/o logging in), subsequent code will puke.
            # The safest way to fix this would be to emulate pylons behavior, and instantiate a fresh beaker.session.Session object,
            # but I don't know what to pass in for the billions of kwargs it takes, so we'll just use an empty {} for simplicity.
            # If something breaks down the line because it expects Session-specific methods or properties, this is the problem.
            if not newsession:
                logger.info("No session found for key '%s'! Using an empty dictionary..." % cookie)
                newsession = {}

            # Load the registry and replace our global session withthe new one
            registry = request.environ['paste.registry']
            registry.register(session, newsession)

            # Replace the other session reference to look to the new one
            pylons_obj = request.environ['pylons.pylons']
            pylons_obj.session = newsession
    
    def rollback(self):
        """
        convenience method to rollback the applied data
        """
        Session.rollback()

    def flush(self, *args):
        """
        convenience method; flush data into transaction
        """
        Session.flush(*args)
           
    def commit(self):
        """
        convenience method; commit the transaction
        """
        # only do the flushing if we are running functional tests
        if 'paste.testing_variables' in request.environ:
            Session.flush()
        else:
            Session.commit()

def render_response(*args, **kw):
    """
    override pylons render_response so that we can supply
        defaults to a form using htmlfill. form_defaults can
        either be passed in as part of the keyword dict or
        on the c variable (ie, c.form_defaults = dict(...))
    """
    form_defaults = kw.pop('form_defaults', False)
    # the prepare_form method puts the defaults on c.form_defaults
    if not form_defaults and c.form_defaults:
        form_defaults = c.form_defaults
        
    content = render(*args, **kw)
    
    def formatter_that_doesnt_suck(error):
        return 'no suckage'
    
    # pylons does htmlfill.render on pages that have errors, so don't do it here (pylons.decorators.__init__.py line 183)
    if not c.form_errors:
        if form_defaults:
            content = htmlfill.render(content, defaults=form_defaults, encoding="utf-8")
    return content

import formencode

from paste.httpexceptions import HTTPException
from pylons import tmpl_context as c

import exceptions
import helpers as h

FORMAT_JSON = u'json'
FORMAT_CSV = u'csv'

STATUS_SUCCESS   = u'success'
STATUS_FAIL = u'fail'

ERROR_HTTP_STATUS = {
    errors.FORBIDDEN: 403,
    errors.NOT_FOUND: 404
}

def htmlfill_error_formatter(error):
    """
    An error formatter to make the errors consistent with the js validate errors.
    """
    from formencode.rewritingparser import html_quote
    return '<div class="error-container"><label class="error">%s</label></div>' % (html_quote(error))

def _jsonify(d):
    import simplejson
    return simplejson.dumps(d)

def format_results(results, format):
    
    if format == FORMAT_JSON:
        content_type = 'text/json'
        formatted_results = _jsonify(results)
    else:
        content_type = 'text/json'
        formatted_results = _jsonify(results)

    # Set HTTP headers, stamp runtime, return
    response.headers['Content-Type'] = content_type + '; charset=utf-8'
    return formatted_results

def async(func, *args, **kwargs):
    """
    A decorator to interface with async client requests,
    including returning controller exceptions.
    """
    request.environ['is_async'] = True
    
    # Determine format from param
    format = request.params.get('format')
    format = format in [FORMAT_JSON, FORMAT_CSV] and format or FORMAT_JSON
    
    # Determine format from Accept header, if not specified in the URL
    if format != FORMAT_CSV:
        accept = request.headers.get('Accept','').lower()
        logger.info(accept)
        if FORMAT_XML in accept:
            format = FORMAT_XML
        elif FORMAT_JSON in accept:
            format = FORMAT_JSON
    
    user_agent = request.headers.get('User-Agent', '')
    flash_request = 'Adobe Flash Player' in user_agent
    
    def append_client_exception(result, ce):
        if 'errors' not in result: result['errors'] = []
        
        err = {'value': ce.value, 'message': ce.msg, 'code': ce.code}
        if ce.field:
            err['field'] = ce.field
        
        result['errors'].append(err)
    
    # run the function
    try:
        result = func(*args)
        
        if result == True:
            result = {u'status': STATUS_SUCCESS}
        elif result == False:
            result = {u'status': STATUS_FAIL}
        #elif type(result) is dict and not result.has_key('status'):
        #    result[u'status'] = STATUS_SUCCESS
        elif not (type(result) is dict):
            result = {
                u'results': result
            }
        
        if flash_request:
            result['status'] = STATUS_SUCCESS
    
    except formencode.validators.Invalid, (e):
        # Keep the response status at 200 for Flash requests, otherwise the client wont see
        # any useful error information        
        if not flash_request:
            response.status = 400
            # Setting this key in the environ disables the error middleware that might otherwise
            # clobber our error structure with a glossy error webpage.
            pylons.request.environ['pylons.status_code_redirect'] = True
        else:
            result['status'] = STATUS_FAIL
        
        result = {}
        
        errs = e.error_dict
        error_list = []
        for field in errs.keys():
            if isinstance(errs[field], formencode.validators.Invalid):
                error_list.append({'value': errs[field].value, 'message': errs[field].msg, 'field': field})
            else:
                error_list.append({'value': None, 'message': errs[field], 'field': field})
            
        result['errors'] = error_list
    
    except HTTPException, (e):
        result = {}
        if e.code in [404, 403]:
            result['errors'] = [{'message': 'Not found (404): %s' % (e.detail), 'code': e.code}]
        else:
            raise
        
    except exceptions.ClientException, (e):
        # some of the error codes correspond to different HTTP statuses.
        # i.e. errors.NOT_FOUND -> 404
        
        # Keep the response status at 200 for Flash requests, otherwise the client wont see
        # any useful error information
        if not flash_request: 
            response.status = ERROR_HTTP_STATUS.get(e.code, 400)
            # Setting this key in the environ disables the error middleware that might otherwise
            # clobber our error structure with a glossy error webpage.
            pylons.request.environ['pylons.status_code_redirect'] = True
        else:
            result['status'] = STATUS_FAIL
        
        result = {}
        
        append_client_exception(result, e)
    
    except exceptions.CompoundException, (e):
        # some of the error codes correspond to different HTTP statuses.
        # i.e. errors.NOT_FOUND -> 404
        
        # Keep the response status at 200 for Flash requests, otherwise the client wont see
        # any useful error information
        if not flash_request:
            response.status = 400
            # Setting this key in the environ disables the error middleware that might otherwise
            # clobber our error structure with a glossy error webpage.
            pylons.request.environ['pylons.status_code_redirect'] = True
        else:
            result['status'] = STATUS_FAIL
        
        result = {}
        
        if not e.has_exceptions:
            result['errors'] = [{'message': 'Unknown Error :(', 'code': errors.UNSET}]
        else:
            for ce in e.exceptions:
                append_client_exception(result, ce)
    
    # queries for the query analyzer.
    debug = h.is_admin()
    if debug and c.queries:
        from time import time
        length = len(c.queries)
        result['debug'] = {
            'queries': length,
            'query_time': c.query_time or 0,
            'total_time': time() - c.render_start,
            'requested_url': c.requested_url,
            'request_html': render_response('/debug/request.html')
        }
        logger.info('ASYNC queries: %s; qtime: %.3fsec; total time: %.3fsec' % (result['debug']['queries'], result['debug']['query_time'], result['debug']['total_time']))
        
    return format_results(result, format)
async = decorator(async)

def mixed_response(sync_error_action=None, prefix_error=False,
                   auto_error_formatter=htmlfill_error_formatter, **htmlfill_kwargs):
    """
    """
    def dec(fn):
        
        sea = sync_error_action or fn.__name__
        
        def new(self, *args, **kwargs):
            
            accept = request.headers.get('Accept','').lower()
            was_xhr = request.headers.get('X-Requested-With','').lower() == 'xmlhttprequest'
            
            self.is_async = was_xhr or 'text/html' not in accept
            
            params = request.params
            
            if self.is_async:
                @client_async
                def run_async():
                    return fn(self, *args, **kwargs)
                return run_async()
            
            else:
                errs = {}
                
                def append_client_exception(ce):
                    if ce.field:
                        errs[ce.field] = ce.msg
                    else:
                        errs['_general'] = ce.msg
                    
                try:
                    val = fn(self, *args, **kwargs)
                    if isinstance(val, dict) and 'url' in val:
                        return h.redirect(val['url'])
                    return val
                except formencode.Invalid, e:
                    errs = e.unpack_errors(False, '.', '-')
                except errors.ClientException, e:
                    append_client_exception(e)
                except errors.CompoundException, e:
                    for ce in e.exceptions:
                        append_client_exception(e.exceptions)
                
                if errs:
                    request.environ['REQUEST_METHOD'] = 'GET'
                    
                    self._py_object.tmpl_context.form_errors = errs
        
                    request.environ['pylons.routes_dict']['action'] = sea
                    response = self._dispatch_call()
        
                    htmlfill_kwargs2 = htmlfill_kwargs.copy()
                    htmlfill_kwargs2.setdefault('encoding', request.charset)
                    htmlfill_kwargs2.setdefault('prefix_error', prefix_error)
                    htmlfill_kwargs2.setdefault('auto_error_formatter', auto_error_formatter)
                    
                    return htmlfill.render(response, defaults=params, errors=errs,
                                           **htmlfill_kwargs2)
        return new
    return dec
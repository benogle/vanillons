"""
Here we define each front end module. They are in the format:

JS = {
    'module_name': ('path/to/compressed.js', [
        'lib/some/file.js',
        'lib/that/is/part.js',
        'lib/of/the/compressed/module.js'
    ])
}

There is a javascript and a CSS dict. Modules that contain both js and css should
be named the same.

There are multiple consumers of these dicts.

The bin/build_frontend.py file does the compression. It isnt smart with respect to
the output dorectories. It only creates a conrollers and an modules dir. 

The templates/require.html module uses them as well:

<%namespace name="r" file="/require.html"/>
r.require('core', 'charting'). 
"""

JS = {
    'core': ('build/core.js', [
        
        'jquery.js',
        'include/jquery.form.js',
        'include/jquery.validate.js',
        'include/jquery.cookie.js',
        'include/jquery.json.js',
        'include/jquery.jeditable.js',
        'include/underscore.js',
        'include/backbone.js',
        
        'quaid/src/core.js',
        'quaid/src/log.js',
        'quaid/src/util.js',
        'quaid/src/widget.js',
        'quaid/src/form.js',
        'quaid/src/validation.js',
        
        'quaid/src/extension/backbone.js',
        'quaid/src/extension/debug.js',
        'quaid/src/extension/notifications.js',
        'quaid/src/extension/editablefield.js',
        
        'lib/base.js'
    ]),
    
    'test': ('build/modules/tests.js',[
        'test/base.js',
        'test/qunit.js',
        'test/test_base.js',
    ]),
    
    'controllers.auth': ('build/controllers/auth.js', ['controllers/auth.js']),
    'controllers.admin': ('build/controllers/admin.js', [
        'controllers/admin/base.js'
    ])
}

CSS = {
    'core': ('build/core.css', [
        'main.css',
        'forms.css',
        'core/notifications.css',
        'widgets/simpleconsole.css',
        'widgets/debugbar.css'
    ]),
    
    'test': ('build/modules/test.css', [
        'test/qunit.css',
    ]),
    
    'ie': ('build/ie.css', ['ie.css']),
    
    'controllers.admin': ('build/controllers/admin.css', [
        'controllers/admin.css'
    ])
}
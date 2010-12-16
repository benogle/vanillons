
from vanillons.lib.base import BaseController, h, c, auth

class AdminController(BaseController):
    
    def __before__(self, *a, **kw):
        if not auth.is_admin():
            abort(404)
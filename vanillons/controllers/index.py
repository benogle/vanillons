from vanillons.lib.base import *

class IndexController(BaseController):
    """
    """
    def index(self):
        return render('/index/index.html')


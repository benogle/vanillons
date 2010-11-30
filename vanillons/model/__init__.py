"""The application's model objects"""
import datetime
from vanillons.model.meta import Session, Base
from vanillons.model.users import User, UserPreference

def init_model(engine):
    """Call me before using any of the tables or classes in the model"""
    Session.configure(bind=engine)
    
    from psycopg2 import extensions
    extensions.register_type(extensions.UNICODE)
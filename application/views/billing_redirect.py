import time
import hashlib

from flask import redirect, flash, url_for, request
from flask.ext.admin import BaseView, expose
from flask.ext.login import current_user
from application import app


def generate_whmcs_url(goto=None):
    ''' Creates a link that allows an user to visit their billing account
        http://docs.whmcs.com/AutoAuth
        
        This is helpful because WHMCS doesn't have LDAP support.
    '''
    timestamp = str(int(time.time()))
    whmcs_url = app.config['WHMCS_URL']
    key = app.config['AUTO_AUTH_KEY'] # set in WHMCS config
    
    hash = hashlib.sha1(current_user.email + timestamp + key)
    hash_string = hash.hexdigest()
    
    url = "%s?email=%s&timestamp=%s&hash=%s&goto=%s" % (
        whmcs_url, current_user.email, timestamp, hash_string, goto
    )
    return url


class BillingRedirect(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated()
        
    # redirect to login if not authenticated
    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login.index', next=request.url))
        
    @expose('/')
    def index(self):
        return redirect(generate_whmcs_url("clientarea.php"))
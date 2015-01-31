from application import app
from application.utils import change_badge_status, AdminOnlyMixin
from flask import redirect, request, jsonify, flash, url_for
from flask.ext.admin import BaseView, expose
from flask.ext.login import current_user


class BadgeAPI(AdminOnlyMixin, BaseView):
    """ API endpoint for activating/deactivating badges.        
        
        Note: WHMCS has an automatic trigger which uses this deactivate overdue users.
    """
    def is_accessible(self):
        # bypass login if user has a valid API key
        api_key = request.args.get('apiKey')
        if api_key and (request.remote_addr in app.config['IP_WHITELIST']):
            if (api_key == app.config['BADGE_API_KEY']):
                return True
        return current_user.is_authenticated() and current_user.is_admin()
        
    def is_visible(self):
        return False
            
    @expose('/')
    def index(self):
        status = request.args.get('status')
        whmcs_user_id = request.args.get('whmcs_user_id')
        badge = request.args.get('badge')
        return jsonify(**change_badge_status(status, whmcs_user_id, badge))

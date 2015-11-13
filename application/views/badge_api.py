from application import app, db
from application.utils import change_badge_status, AdminOnlyMixin
from application.models import WHMCSclients
from flask import request, jsonify
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
        change_status_to = request.args.get('status')
        whmcs_user_id = request.args.get('whmcs_user_id')

        if not (whmcs_user_id and change_status_to):
            return jsonify(error="Status and whmcs_user_id are required.")

        user = WHMCSclients.query.get(whmcs_user_id)
        if not user:
            return jsonify(error="Could not find that User ID in WHMCS.")

        if ((change_status_to == "Active") and (user.deactivated_badges >
                                                user.active_products_and_addons)):
            return jsonify(error="User has too many deactivated badges. "
                                 "Some of the badges need to be marked as 'Lost'.")

        results = []
        for badge in user.badges:
            result = None
            if change_status_to == "Active":
                if badge.status == "Deactivated":
                    result = change_badge_status(change_status_to, badge)
            else:
                if badge.status == "Active":
                    result = change_badge_status(change_status_to, badge)

            if result:
                results.append(result)
                if "error" not in result:
                    badge.status = change_status_to
                    db.session.commit()

        return jsonify(results=results)

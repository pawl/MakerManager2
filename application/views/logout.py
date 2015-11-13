from flask import redirect, flash, url_for
from flask.ext.login import logout_user, current_user
from flask.ext.admin import BaseView, expose


class Logout(BaseView):
    def is_visible(self):
        """ Login link is hardcoded in base.html.
            No need to use framework to display the link.
        """
        return False

    @expose('/')
    def index(self):
        if current_user.is_authenticated():
            logout_user()
            flash('Successfully logged out.')
            return redirect(url_for('admin.index'))
        else:
            flash('You are already logged out.')
            return redirect(url_for('admin.index'))

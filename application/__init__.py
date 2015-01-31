from flask import Flask, render_template, session, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.admin import Admin
from flask.ext.mandrill import Mandrill

app = Flask(__name__, static_url_path='/assets')
app.config.from_object('application.default_settings')
app.config.from_envvar('PRODUCTION_SETTINGS', silent=True)

if not app.debug:
	import logging
	app.logger.addHandler(logging.StreamHandler())
	app.logger.setLevel(logging.INFO)
    
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login.index' # for @login_required

# for sending e-mail through mandrillapp.com
mandrill = Mandrill(app)

from application.models import *

# prevent "'AnonymousUserMixin' object has no attribute" errors
from application.utils import AnonymousUser
login_manager.anonymous_user = AnonymousUser

from application.views import *
from application.hooks import *

admin = Admin(app, name='Maker Manager 2', index_view=HomeView(name="Home", url='/'),
              base_template='base.html', template_mode="bootstrap3")

admin.add_view(BillingRedirect('Billing Account', endpoint='billing'))

admin.add_view(BadgeAdmin(Badges, db.session, name='All Badges', endpoint='badges',
                          category="Manage Badges"))

admin.add_view(BadgesHistoryAdmin(BadgesHistory, db.session, name='Badge Activity Log',
                                  endpoint='badgehistory', category="Manage Badges"))

admin.add_view(BadgeAPI('Badge API', endpoint='badgeapi'))

admin.add_view(BadgeRequest('Badge Request', endpoint='badge_request'))

admin.add_view(Login('Login', endpoint='login'))
admin.add_view(Logout('Logout', endpoint='logout'))

# menu links - admin only
admin.add_link(AdminMenuLink(name='Active Badges',
                             url='/makermanager/badges/?flt0_status_equals=Active', category="Manage Badges"))
admin.add_link(AdminMenuLink(name='Deactivated Badges',
                             url='/makermanager/badges/?flt0_status_equals=Deactivated', category="Manage Badges"))
admin.add_link(AdminMenuLink(name='Pending Badges',
                             url='/makermanager/badges/?flt0_status_equals=Pending', category="Manage Badges"))
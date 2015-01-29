from application.models import User
from flask import request, redirect, url_for, flash
from flask.ext.admin import BaseView, expose
from flask.ext.login import login_user, current_user
from wtforms import Form
from wtforms.fields import StringField, PasswordField, HiddenField
from wtforms.validators import InputRequired


class LoginForm(Form):
    username = StringField(u'Username', [InputRequired()])
    password = PasswordField(u'Password', [InputRequired()])
    next = HiddenField(u'Next')


class Login(BaseView):
    def is_visible(self):
        """ Login link is hardcoded in base.html.
            No need to use framework to display the link.
        """
        return False
        
    @expose('/', methods=('GET', 'POST'))
    def index(self):
        next = request.args.get('next') or url_for('admin.index')
        
        if current_user.is_authenticated():
            return redirect(url_for('admin.index'))
            
        form = LoginForm(request.form)
        
        if (request.method == "POST") and form.validate():
            # LDAP authentication occurs when the User object is initialized
            user = User(username=form.username.data, password=form.password.data)
            if user.active:
                login_user(user)
                return redirect(request.form.get('next') or url_for('admin.index'))
            else:
                flash('Unable to authenticate with the username and password you provided.')
                return redirect(url_for('login.index'))
                
        return self.render('login.html', form=form, next=next)

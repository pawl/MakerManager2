from flask.ext.admin.base import MenuLink
from flask.ext.login import current_user


# Create menu links classes with reloaded accessible
class AuthenticatedMenuLink(MenuLink):
    def is_accessible(self):
        return current_user.is_authenticated()


# Create menu links classes with reloaded accessible
class AdminMenuLink(MenuLink):
    def is_accessible(self):
        return current_user.is_authenticated() and current_user.is_admin()

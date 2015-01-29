from application import login_manager
from application.models import User


@login_manager.user_loader
def load_user(uid):
    return User(uid=uid)

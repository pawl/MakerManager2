from flask.ext.admin import expose, AdminIndexView


class HomeView(AdminIndexView):
    def is_visible(self):
        return False
        
    @expose('/')
    def index(self):
        return self.render('home.html')

from application import app, db, admin
from manage import initdb


class TestBasic:
    def setup(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        initdb()

    def test_home(self):
        rv = self.client.get('/')
        assert rv.status_code == 200

    def test_badge_process(self):
        # login
        rv = self.client.post('/login/',
                              data={'username': 'test', 'password': 'test'},
                              follow_redirects=True)
               
        # send request for new badge
        rv = self.client.post('/badge_request/',
                              data={'member': '1', 'badge': '12345'},
                              follow_redirects=True)
        assert u'badge has been activated automatically.' in rv.data.decode('utf-8')
        
        rv = self.client.post('/badge_request/',
                              data={'member': '1', 'badge': '12345'},
                              follow_redirects=True)
        assert u'That badge is already active.' in rv.data.decode('utf-8')
        
        # deactivate badge
        rv = self.client.post('/badges/ajax/update/',
                              data={'status-1': 'Deactivated'},
                              follow_redirects=True)
        assert u'Record was successfully saved.' in rv.data.decode('utf-8')
DEBUG = False
RELOAD = False
THREADED = True

SECRET_KEY = '\x9c\x04*NDT\xfbe:\x80\xc8\xc9\x1bU\xa2S\x08\xb16\xe7b_\xd5\xa0'
SQLALCHEMY_DATABASE_URI = 'mysql://root:test@localhost/dms_crm'

LDAP_SERVER = 'ldap://localhost'
DC_STRING = 'dc=dallasmakerspace,dc=org'
BASE_DN = 'ou=people,' + DC_STRING

# key used by WHMCS to activate/deactivate badges
BADGE_API_KEY = 'secret'

AUTO_AUTH_KEY = 'secret'
ADMIN_EMAIL = 'paul90brown@gmail.com'

WHMCS_URL = 'https://dallasmakerspace.org/accounts/dologin.php'

SMARTWAIVER_KEY = 'bb3c68f7076278f8fa30610ddd60656d-175998'

MANDRILL_API_KEY = 'ZIsYTLnVVGTbOx1YIgdVZQ'

IP_WHITELIST = ['127.0.0.1']

### for _external url_for in emails
SERVER_URL = 'http://104.236.24.168:5000/'
API_URL = 'http://127.0.0.1:5050/?apiKey=' + BADGE_API_KEY + '&action='
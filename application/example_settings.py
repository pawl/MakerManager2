DEBUG = False
RELOAD = False
THREADED = True

SECRET_KEY = 'secret'
SQLALCHEMY_DATABASE_URI = 'mysql://user:pass@localhost/dms_crm'

LDAP_SERVER = 'ldap://localhost'
DC_STRING = 'dc=yourdomain,dc=com'
BASE_DN = 'ou=people,' + DC_STRING

# key used by WHMCS to activate/deactivate badges
BADGE_API_KEY = 'secret'

API_URL = 'https://www.yourdomain.com/accesscontrol/?apiKey=' + BADGE_API_KEY + '&action='

AUTO_AUTH_KEY = 'secret'
ADMIN_EMAIL = 'admin@yourdomain.com'

WHMCS_URL = 'https://yourdomain.com/whmcs/dologin.php'

SMARTWAIVER_KEY = 'secret'

MANDRILL_API_KEY = 'secret'

IP_WHITELIST = ['1.1.1.1', 'localhost']

### for _external url_for in emails
SERVER_URL = 'www.yourdomain.com/makermanager/'

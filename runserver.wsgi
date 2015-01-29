activate_this = '/opt/Envs/prod/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import sys
sys.path.insert(0,'/var/www/makermanager/')

from application import app as application

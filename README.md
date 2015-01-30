MakerManager2
---
Provides a web interface and automation for Dallas Makerspace's access control system.

An overhaul of the original MakerManager, written in Python: https://github.com/pawl/MakerManager

Main Features
---
* Allows users to request and activate their own RFID badges after they've signed a liability waiver.
* Allows administrators to activate and deactivate RFID badges through an easy-to-use web interface.
* Checks Smartwaiver to see if the user signed a liability waiver.
* Provides an API that allows WHMCS to automatically activate and deactivate RFID badges when an user's payment is overdue.
* Provides an easy way for users to access their billing account by using their LDAP credentials.

Screenshots
---
"Manage Badges" page:
![Alt text](https://github.com/pawl/MakerManager2/blob/master/screenshots/makermanager.png "Manage Badges Page")

"Request Badge" page:
![Alt text](https://github.com/pawl/MakerManager2/blob/master/screenshots/badge_request.png "Request Badge Page")

Improvements over MakerManager 1.0
---
* Integration with Smartwaiver. If an admin or badge owner requests a badge and the person has signed a waiver - it will be activated automatically.
* A simpler and more maintainable codebase.
* A new status for "Lost" badges. This helps fix a bug that would activate all of an user's lost badges when they start their membership again.
* Now it sends an e-mail to the person who owns the badge that's being activated.
* The admin interface is much faster. It also has filters, pagination, and a search - thanks to Flask-Admin.
* Improved validation on the badge request form. Including a check for whether a duplicate badge is already active.
* A new "active badges" column to see who has too many badges activated.
* A new "badge activity" log that shows who deactivated/activated a badge and when.

TODO
---
* Write code for creating a test database and a few simple unit tests
* MenuLink items not showing as active when they are selected.
* Simplify the query in _get_filtered_list by using the ORM.
* Add filtering to "Total Products + Addons" and "Active Badges" on admin view.
* Allow deleting pending badges.
* Andrew wants to add a quiz for new members. Someone just needs to write the questions to it.
* Improve feedback for Smartwaiver mismatches (like when the first and last name match but the email doesn't)

Setup
---
First, activate your virtualenv and install the requirements by running: `pip install -r requirements.txt`

Copy `example_settings.py` to `default_settings.py` and modify the following:
* SECRET_KEY - Generate this by running the python shell and typing: import os; os.urandom(24)
* SQLALCHEMY_DATABASE_URI - https://pythonhosted.org/Flask-SQLAlchemy/config.html#configuration-keys
* LDAP settings (these probably going to be very unique for each user):
```
LDAP_SERVER = 'ldap://localhost'
DC_STRING = 'dc=yourdomain,dc=com'
BASE_DN = 'ou=people,' + DC_STRING
```
* BADGE_API_KEY - API key used by the webservice that communicates with the access control system.
* API_URL = URL for the webservice that communicates with the access control system.
* AUTO_AUTH_KEY - Used by WHMCS to refer users directly to their billing account. Described in detail here: http://docs.whmcs.com/AutoAuth
* ADMIN_EMAIL - Email address that "pending" badge requests will be sent to.
* WHMCS_URL = 'https://yourdomain.com/whmcs/dologin.php'
* SMARTWAIVER_KEY - An API key for SmartWaiver that can be requested here: https://www.smartwaiver.com/m/user/sw_login.php?wms_login=1&wms_login_redirect=%2Fm%2Frest%2F
* MANDRILL_API_KEY - Get an API key from the Mandrill settings page, also follow their instructions to set the appropriate DNS settings on your domain. This is required to send email.
* SERVER_URL - The URL for the site, required for sending e-mail with links back to MakerManager.

Usage
---
Once you complete setup, you can run the it using Flask's webserver by typing: `python runserver.py`

Running it on apache (since WHMCS also runs on apache) is described in the `How should I host this?` section of the FAQ.

FAQs
---
### How is this communicating with your access control system?
See these two pages for more details:
* https://github.com/pawl/Chinese-RFID-Access-Control-Library
* https://github.com/pawl/Chinese-RFID-Access-Control-Library/blob/master/examples/webserver.py

### What would I need to implement this myself?
* An access control system mentioned in the step above, or another one that can accept HTTPS requests somehow.
* WHMCS (the billing system)
* A smartwaiver account.

### How can I make WHMCS deactivate badges automatically?
You will need to create a hook in WHMCS like this:
```
<?php

function deactivate_badge($vars) {
	logActivity("Attempting to deactivate badge");
	$apiKey = "secret"
	$userid = $vars['params']['clientsdetails']['userid'];
	$url = 'https://www.yourdomain.com/makermanager/badgeapi/?status=Deactivated&apiKey=' . 
	        $apiKey . '&whmcs_user_id=' . $userid;
	$response = curlCall($url);
	logActivity("WHMCS User ID: " . $userid . ", Response: " . $response);
	if ((strpos($response,'Successfully') == false) or (strpos($response,'No badges found')) {
		$message = 'Unable to remove user ' . $userid . ' from access control due to an error:\r\n' . $response;
		mail('admin@dallasmakerspace.org', 'WHMCS - MakerManager Remove User Failed', $message);
	}
}

//PreModuleTerminate
add_hook("PreModuleSuspend",1,"deactivate_badge");
add_hook("PreModuleTerminate",1,"deactivate_badge");

?>
```

### How should I host this?
I recommend installing mod_wsgi and hosting it alongside WHMCS and adding something similar to this to your apache configuration:
```
WSGIDaemonProcess makermanager user=www-data group=www-data threads=5
WSGIScriptAlias /makermanager /var/www/makermanager/runserver.wsgi

<Directory /var/www/makermanager>
        WSGIProcessGroup makermanager
        WSGIApplicationGroup %{GLOBAL}
        Order deny,allow
        Allow from all
</Directory>

Alias /makermanager/assets /var/www/makermanager/application/static

<Directory /var/www/makermanager/application/static>
        Order allow,deny
        Allow from all
</Directory>

Alias /makermanager/static/admin /opt/Envs/prod/src/flask-admin-master/flask_admin/static/

<Directory /opt/Envs/prod/src/flask-admin-master/flask_admin/static/>
        Order allow,deny
        Allow from all
</Directory>
```

More details on mod_wsgi are available here: http://flask.pocoo.org/docs/0.10/deploying/mod_wsgi/

import ldap
import urllib2

from flask import flash, url_for, redirect, request
from application import app, mandrill, db
from application.models import WHMCSclients, Badges, BadgesHistory
from flask.ext.login import current_user, AnonymousUserMixin
from bs4 import BeautifulSoup
from datetime import datetime


class AnonymousUser(AnonymousUserMixin):
    """ AnonymousUser definition
    """
    def __init__(self):
        self.id = None
        self.first_name = None
        self.last_name = None
        self.email = None
        self.username = None
        self.admin = False


class AdminOnlyMixin(object):
    """ For overriding admin-only views.
    """
    def is_accessible(self):
        return current_user.is_authenticated() and current_user.is_admin()
        
        def _handle_view(self, name, **kwargs):
            if not self.is_accessible():
                if current_user.is_authenticated():
                    flash('Access Denied', 'error')
                    return redirect(url_for('admin.index'))
                else:
                    flash('Please log in to access this page.', 'error')
                    return redirect(url_for('login.index', next=request.url))


class BadgeUpdateException(Exception):
    """ Custom exception class for when change_badge_status fails
    """
    pass


def change_badge_status(status=None, badge_record=None):
    """ Makes an API call to the web service attached to the access controller.
        
        Params:
        `status`: status the badge will be changed tos
        `badge_record`: row object from the Badges model
    """
    user = badge_record.tblclients
    
    # determine add or remove based on status_map
    status_map = {'Active': 'add', 'Deactivated': 'remove', 'Lost': 'remove'}
    try:
        add_or_remove = status_map[status]
    except KeyError:
        return dict(error="Status required. Must be: " + ", ".join(status_map.keys()))
    
    # do not allow badge activation if too many badges are already active
    if ((status == "Active") and (user.active_badges > 
                                  user.active_products_and_addons)):
        return dict(error="User has only paid for %s." % 
                    (user.active_products_and_addons,))
    
    # Send activation/deactivation request to a webservice:
    # https://raw.githubusercontent.com/pawl/Chinese-RFID-Access-Control-Library/master/examples/webserver.py
    response = urllib2.urlopen(app.config['API_URL'] + add_or_remove + '&badge=%s' % str(badge_record.badge))
    html = response.read()
    if response.getcode() == 200:
        if html == "User Added Successfully":
            subject = "DMS Badge Activated"
            message = "%s's badge has been activated." % (user.full_name,)
            send_email(subject, message, user, email_admins=False)
            
            # record activation in log
            record = BadgesHistory(user.id, current_user.email, badge_record.badge, status, datetime.now())
            db.session.add(record)
            db.session.commit()
            
            return dict(message=html)
        elif html == "User Removed Successfully":
            # record deactivation in log
            record = BadgesHistory(user.id, current_user.email, badge_record.badge, status, datetime.now())
            db.session.add(record)
            db.session.commit()
            
            return dict(message=html)
        else:
            return dict(error="Unexpected Response: %s" % (html,))
    else:
        return dict(error="Status Code: %s Response" % (response.getcode(),))


def verify_waiver_signed(firstname=None, lastname=None, email=None):
    """ Make API call to Smartwaiver and see if we have a waiver on file
    """
    
    # Unfortunately Smartwaiver doesn't allow querying by email for firstname too
    xml_response = urllib2.urlopen(
        'https://www.smartwaiver.com/api/v3/?rest_request=%s&'
        'rest_request_lastname=%s&' % (
            app.config['SMARTWAIVER_KEY'], lastname
        )
    )
    soup = BeautifulSoup(xml_response.read())
    
    firstname_match, lastname_match, email_match = (None, None, None)
    
    for participant in soup.participants:
        p_firstname = participant.find('firstname')
        p_lastname = participant.find('lastname')
        p_email = participant.find('primary_email')
        
        # E-mail in Smartwaiver is not required, so it can be None
        if (p_firstname and p_lastname and p_email and firstname and lastname and email):
            firstname_match = (p_firstname.text.strip().lower() == firstname.strip().lower())
            lastname_match = (p_lastname.text.strip().lower() == lastname.strip().lower())
            email_match = (p_email.text.strip().lower() == email.strip().lower())
        
        if (firstname_match and lastname_match and email_match):
            break
        else:
            firstname_match, lastname_match, email_match = (None, None, None)
        
    return (firstname_match and lastname_match and email_match)
    
    
def send_email(subject, message, user, email_admins=True):
    ''' Params:
        `user`: WHMCSclients model record
        `subject`: email subject
        `message`: email body contents
        `email_admins`: prevents spam to admins
    '''
    
    html_template = '''
        <html>
            <head>
                <title>%s</title>
            </head>
            <body>
                %s
            </body>
        </html>
    '''
    html = html_template % (subject, message)

    # prevent duplicate emails if owner is activator
    if (current_user.email == user.email):
        email_addresses = []
    else:
        email_addresses = [{'email': user.email}]
        
    # don't sent email to admins unless it's a pending request
    if email_admins:
        email_addresses = email_addresses + [{'email': app.config['ADMIN_EMAIL']}]
                           
    if email_addresses:
        mandrill.send_email(
            from_email=app.config['ADMIN_EMAIL'],
            subject=subject,
            to=email_addresses,
            html=html
        )

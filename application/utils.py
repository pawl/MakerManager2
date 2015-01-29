import ldap
import urllib2

from flask import flash, url_for, redirect, request
from application import app, mandrill, db
from application.models import WHMCSclients, Badges, BadgesHistory
from flask.ext.login import current_user
from bs4 import BeautifulSoup
from datetime import datetime


class AdminOnlyMixin(object):
    ''' For overriding admin-only views.
    '''
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
    ''' Custom exception class for when change_badge_status fails
    '''
    pass


def change_badge_status(status=None, whmcs_user_id=None, badge=None):
    ''' Makes an API call to the web service attached to the access controller.
    '''
    api_url = app.config['API_URL']
    
    # determine add or remove based on status_map
    status_map = {'Active': 'add', 'Deactivated': 'remove', 'Lost': 'remove'}
    try:
        add_or_remove = status_map[status]
    except KeyError:
        return dict(error="Status required. Must be: " + ", ".join(status_map.keys()))
    
    try:
        float(whmcs_user_id)
    except ValueError, TypeError:
        return dict(error="Invalid WHMCS user ID. Must be a number.")
    
    user = WHMCSclients.query.get(whmcs_user_id)
    if not user:
        return dict(error="Could not find that User ID in WHMCS.")
    
    
    responses = []
    if badge:
        responses.append(urllib2.urlopen(api_url + add_or_remove + '&badge=' + str(badge)))
    # check if user has more deactivated badges than active products
    elif (not badge and (user.deactivated_badges > user.active_products_and_addons) and (status == "Active")):
        return dict(error="User has too many deactivated badges. "
                          "Manual intervention required. "
                          "Some of the badges need to be marked as 'Lost'.")
    else:
        # no badge parameter, and does not require manual intervention
        # request is sent to this webservice hosted at DMS:
        # https://raw.githubusercontent.com/pawl/Chinese-RFID-Access-Control-Library/master/examples/webserver.py
        badges = Badges.query.filter(db.and_(Badges.whmcs_user_id == whmcs_user_id,
                                             Badges.status == "Deactivated")).all()
        if badges:
            for record in badges:
                responses.append(urllib2.urlopen(api_url + add_or_remove + '&badge=%s' % record.badge))
        else:
            return dict(error="No badges found.")
        
    errors = []
    messages = []
    for response in responses:
        html = response.read()
        if response.getcode() == 200:
            if html == "User Added Successfully":
                subject = "DMS Badge Activated"
                message = "%s's badge has been activated." % (user.full_name,)
                send_email(subject, message, user, email_admins=False)
                
                # record activation in log
                record = BadgesHistory(whmcs_user_id, current_user.email, str(badge), status, datetime.now())
                db.session.add(record)
                db.session.commit()
                
                messages.append(html)
            elif html == "User Removed Successfully":
                # record deactivation in log
                record = BadgesHistory(whmcs_user_id, current_user.email, str(badge), status, datetime.now())
                db.session.add(record)
                db.session.commit()
                
                messages.append(html)
            else:
                errors.append("Unexpected Response: %s" % (html,))
        else:
            errors.append("Status Code: %s Response" % (response.getcode(),))
            
    if messages and errors:
        return dict(message=", ".join(messages), error=", ".join(errors))
    elif messages and not errors:
        return dict(message=", ".join(messages))
    else:
        return dict(error=", ".join(errors))

def verify_waiver_signed(firstname=None, lastname=None, email=None):
    ''' Make API call to Smartwaiver and see if we have a waiver on file
    '''
    
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

    # send e-mail to admins, and badge owner
    if current_user.email == user.email:
        # prevent duplicate emails if owner is activator
        email_addresses = []
    else:
        email_addresses = [{'email': user.email}]
        
    if email_admins:
        email_addresses = email_addresses + [{'email': app.config['ADMIN_EMAIL']}]
                           
    if email_addresses:
        mandrill.send_email(
            from_email=app.config['ADMIN_EMAIL'],
            subject=subject,
            to=email_addresses,
            html=html
        )

from application import db
from application.models import Badges, WHMCSclients
from flask import request, flash, url_for, redirect
from flask.ext.admin import BaseView, expose
from flask.ext.login import current_user

from wtforms import Form
from wtforms.fields import IntegerField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from wtforms.validators import ValidationError, DataRequired, InputRequired
from application.utils import (verify_waiver_signed, change_badge_status,
                               send_email)


def rfid_validator(form, field):
    if field.data:
        try:
            number = float(form.badge.data)
        except ValueError:
            raise ValidationError('Not a valid badge number.')
        if number > 16777215:
            raise ValidationError('Not a valid badge number. Must be < 16777215.')
            
        # check if badge is already active
        try:
            obj = (Badges.query.filter(db.and_(Badges.badge == form.badge.data, 
                                               Badges.status == "Active")).one())
            raise ValidationError('That badge is already active.')
        except NoResultFound:
            pass
            
        # check if badge is already active
        try:
            obj = (Badges.query.filter(db.and_(Badges.badge == form.badge.data, 
                                               Badges.whmcs_user_id == form.member.data.id)).one())
            raise ValidationError('That badge already belongs to that user.')
        except NoResultFound:
            pass
        except MultipleResultsFound:
            raise ValidationError('That badge already belongs to that user.')


def waiver_validator(form, field):
    if form.member.data:
        user = form.member.data
        if not verify_waiver_signed(user.firstname, user.lastname, user.email):
            raise ValidationError('A signed liability waiver could not be found for this member. '
                                  'Please use the kiosk near the entrance of the Makerspace.')


def get_users_without_badges():
    # TODO: Simplify this query by using the ORM
    query = db.text('''
    SELECT
          whmcs_user_id as id
    FROM (
      SELECT
        distinct `dms-whmcs`.tblclients.id as whmcs_user_id,
        IF(((IFNULL(active_badge_count,0) >= (IFNULL(s.addon_count,0) + IFNULL(m.product_count,0))) 
            AND 
            ((IFNULL(s.addon_count,0) + IFNULL(m.product_count,0)) >= 0)),
            "Hit Limit", "Under Limit") as limit_status,
        (IFNULL(s.addon_count,0) + IFNULL(m.product_count,0)) as active_products
      FROM `dms-whmcs`.tblclients
      left join ( select
          whmcs_user_id,
          count(*) as active_badge_count
        from `dms_crm`.`tbl_badges`
        where status = "Active"
        group by whmcs_user_id
      ) badges ON `dms-whmcs`.tblclients.id = badges.whmcs_user_id
      left join (
        select 
          id,
          userid, 
          count(*) as product_count
        from `dms-whmcs`.tblhosting
        where (tblhosting.domainstatus = "Active") OR (tblhosting.nextduedate > CURDATE())
        group by userid
      ) m ON m.userid = `dms-whmcs`.tblclients.id
      left join (
        select
          hostingid, 
          count(*) as addon_count
        from `dms-whmcs`.tblhostingaddons 
        where (tblhostingaddons.status = "Active") OR (tblhostingaddons.nextduedate > CURDATE())
        group by hostingid
      ) s ON s.hostingid = m.id
    ) as limit_query
    where (limit_status = "Hit Limit")
    ''')
    active_badges = [ids.id for ids in WHMCSclients.query.from_statement(query).all()]
    return WHMCSclients.query.filter(~WHMCSclients.id.in_(active_badges)).order_by(WHMCSclients.firstname).all()


class BadgeRequestForm(Form):
    member = QuerySelectField(query_factory=get_users_without_badges,
                                  get_pk=lambda a: a.id,
                                  allow_blank=True,
                                  blank_text='',
                                  validators=[DataRequired(), waiver_validator])
    badge = IntegerField(u'Badge', validators=[rfid_validator, InputRequired()])

    
class BadgeRequest(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated()
        
    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login.index', next=request.url))
        
    @expose('/', methods=('GET', 'POST'))
    def index(self):
        form = BadgeRequestForm(request.form)
        
        if (request.method == "POST") and form.validate():
            user = form.member.data
            
            record = Badges(user.id, form.badge.data, 'Pending')
            db.session.add(record)
            db.session.commit()
            
            """
                Auto-activation:
                * The user has signed a waiver at the Smartwaiver kiosk.
                * User is admin it's the requester's own badge.
                
                Set to pending and e-mail admin for action:
                * The user has signed a waiver at the Smartwaiver kiosk.
                * NOT the requester's own badge and is NOT an admin
            """
            if ((current_user.is_admin() or (current_user.email == user.email))):
                result = change_badge_status('Active', record)
                
                if "error" in result:
                    raise Exception("%s" % (result['error']))
                
                record.status = 'Active'
                db.session.commit()
                
                flash("Request Successful: %s's badge has been activated automatically." % (user.full_name,))                
            else:
                message = '''
                    <p>%s's badge has been submitted by %s %s for activation.</p>
                    <p>This user has already signed a waiver.</p>
                    <a href='%s'>Approve</a>
                ''' % (user.full_name, current_user.first_name, current_user.last_name,
                       url_for('badges.index_view', flt0_status_equals='Pending', _external=True))
                subject = 'Badge Pending - Already Signed Waiver'
                send_email(subject, message, user)
                
                flash("Request Successful: %s's badge has been submitted for admin approval." % (user.full_name,))
        
        return self.render('create.html', form=form)

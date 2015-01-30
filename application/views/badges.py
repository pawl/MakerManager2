import logging

from application import db, app
from flask.ext.admin.contrib.sqla import ModelView
from flask import request, redirect, url_for, flash
from flask.ext.login import current_user
from sqlalchemy.exc import IntegrityError
from application.models import Badges, WHMCSclients, WHMCSaddons, WHMCSproducts
from application.utils import (verify_waiver_signed, change_badge_status,
                               AdminOnlyMixin, send_email, BadgeUpdateException)

# validation
from sqlalchemy.orm.exc import NoResultFound
from wtforms.validators import ValidationError, DataRequired, InputRequired

# for editable list_view override
from flask.ext.admin.model.fields import ListEditableFieldList
from flask.ext.admin.model.widgets import XEditableWidget


# adds custom options (active, deactivated, lost) to x-editable
class CustomWidget(XEditableWidget):
    def get_kwargs(self, subfield, kwargs):
        kwargs['data-type'] = 'select'
        kwargs['data-source'] = {'Active': 'Active',
                                 'Deactivated': 'Deactivated',
                                 'Lost': 'Lost'}
        return kwargs


class CustomFieldList(ListEditableFieldList):
    widget = CustomWidget()


class BadgeAdmin(AdminOnlyMixin, ModelView):
    """ Create and view badges with Flask-Admin's ModelView
    """
    
    can_edit = False
    can_delete = False
    
    list_template = 'list.html'
    create_template = 'create.html'
    
    # don't allow users to submit unexpected badge statuses
    def status_validator(form, field):
        allowed_status = ('Active', 'Deactivated', 'Lost')
        if form.status.data and (form.status.data in allowed_status):
            raise ValidationError('Status must be: %s' % ', '.join(allowed_status))
            
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
                obj = (Badges.query.filter(db.and_(Badges.badge == field.data, 
                                                   Badges.status == "Active")).one())
                if not hasattr(form, '_obj') or not form._obj == obj:
                    raise ValidationError('That badge is already active.')
            except NoResultFound:
                pass
                
    def waiver_validator(form, field):
        if form.tblclients.data:
            user = form.tblclients.data
            if not verify_waiver_signed(user.firstname, user.lastname, user.email):
                raise ValidationError('A signed liability waiver could not be found for this member. '
                                      'Please use the kiosk near the entrance of the Makerspace.')
    
    form_args = dict(
        tblclients=dict(validators=[DataRequired(), waiver_validator]),
        badge=dict(validators=[rfid_validator, InputRequired()]),
        status=dict(validators=[status_validator]),
    )
    form_columns = ('tblclients', 'badge')
    
    column_editable_list = ['status']
    
    column_searchable_list = [
        'tblclients.firstname', 
        'tblclients.lastname',
        'tblclients.email'
    ]
    column_list = [
        'tblclients.full_name',
        'tblclients.email', 
        'tblclients.active_products_and_addons',
        'tblclients.active_badges',
        'badge',
        'status'
    ]
    column_labels = {
        'tblclients': 'Member',
        'tblclients.full_name': 'Member Name', 
        'tblclients.email': 'E-mail',
        'tblclients.active_products_and_addons': 'Total Products + Addons',
        'tblclients.active_badges': 'Active Badges'
    }
    
    column_filters = ('status', 'badge')
    
    # keeps links backwards compatible if the order of the filters changes
    named_filter_urls = True
            
    # open create_view to authenticated users
    def is_accessible(self):
        if request.endpoint == "badges.create_view":
            return current_user.is_authenticated()
        else:
            return current_user.is_authenticated() and current_user.is_admin()
    
    # override editable list view for "Active"/"Deactivated" options
    def get_list_form(self):
        if self.form_args:
            # get only validators, other form_args can break FieldList wrapper
            validators = dict(
                (key, {'validators': value["validators"]})
                for key, value in self.form_args.iteritems()
                if value.get("validators")
            )
        else:
            validators = None
        return self.scaffold_list_form(CustomFieldList, validators=validators)
            
    # Hook form creation methods
    def create_form(self):
        return self._use_filtered_list(super(BadgeAdmin, self).create_form())

    # filter tblclients select menus based on the functions below
    def _use_filtered_list(self, form):
        form.tblclients.query_factory = self._get_filtered_list
        return form

    # only show users with (active products + addons) < (active badges) 
    def _get_filtered_list(self):
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
        return WHMCSclients.query.filter(~WHMCSclients.id.in_(active_badges)).all()
        
    # override update_model to give more control over handling exceptions
    def update_model(self, form, model):
        try:
            form.populate_obj(model)
            
            # Begin override update_model behavior
            #if model.status == "Delete":
            result = change_badge_status(model.status, model.tblclients.id, model.badge)
            if "error" in result:
                raise BadgeUpdateException("%s" % (result['error']))
            # End custom override code
            
            self._on_model_change(form, model, False)
            self.session.commit()
        except Exception as ex:
            if (not self.handle_view_exception(ex)) or isinstance(ex, BadgeUpdateException):
                flash('Failed to update badge status. %s' % (str(ex)), 'error')
                logging.exception('Failed to update badge status.')

            self.session.rollback()

            return False
        else:
            self.after_model_change(form, model, False)

        return True
        
    # override create_model to give more control over handling exceptions
    def create_model(self, form):
        try:
            model = self.model()
            form.populate_obj(model)
            
            # Begin override create_model behavior
            user = model.tblclients
            
            """
            Auto-activation:
            * The user has signed a waiver at the Smartwaiver kiosk.
            * User is admin it's the requester's own badge.
            
            Set to pending and e-mail admin for action:
            * The user has signed a waiver at the Smartwaiver kiosk.
            * NOT the requestor's own badge and is NOT an admin
            """
            
            if ((current_user.is_admin() or (current_user.email == user.email))):
                model.status = "Active"
                result = change_badge_status(model.status, user.id, model.badge)
                
                if "error" in result:
                    raise BadgeUpdateException("%s" % (result['error']))
                    
                flash("%s's badge has been activated automatically" % (user.full_name,))                
            else:
                # if an non-admin submit's another person's badge for activation
                # require admins to verify even if user signed a waiver
                model.status = "Pending"
                message = '''
                    <p>%s's badge has been submitted by %s %s for activation.</p>
                    <p>This user has already signed a waiver.</p>
                    <a href='%s'>Approve</a>
                ''' % (user.full_name, current_user.first_name, current_user.last_name,
                       url_for('badges.index_view', flt0_status_equals='Pending', _external=True))
                subject = 'Badge Pending - Already Signed Waiver'
                send_email(subject, message, user)
                
                flash("%s's badge has been submitted for admin approval." % (user.full_name,))
            # End custom override code
            
            self.session.add(model)
            self._on_model_change(form, model, True)
            self.session.commit()
        except Exception as ex:
            if (not self.handle_view_exception(ex)) or isinstance(ex, BadgeUpdateException):
                flash('Failed to submit badge request. %s' % (str(ex)), 'error')
                logging.exception('Failed to create record.')

            self.session.rollback()

            return False
        else:
            self.after_model_change(form, model, True)

        return True

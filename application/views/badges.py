import logging

from application import db, app
from flask.ext.admin.contrib.sqla import ModelView
from flask import request, flash
from flask.ext.login import current_user
from application.utils import (change_badge_status, AdminOnlyMixin,
                               BadgeUpdateException)

# validation
from wtforms.validators import ValidationError

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
    can_create = False
    
    list_template = 'list.html'
    
    # don't allow users to submit unexpected badge statuses
    def status_validator(form, field):
        allowed_status = ('Active', 'Deactivated', 'Lost')
        if form.status.data and (form.status.data in allowed_status):
            raise ValidationError('Status must be: %s' % ', '.join(allowed_status))
    
    form_args = {'status': {'validators': [status_validator]}}
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
    
    # override editable list view with CustomFieldList for "Active"/"Deactivated" options
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
        
    # override update_model to give more control over handling exceptions
    def update_model(self, form, model):
        try:
            form.populate_obj(model)
            
            # Begin override update_model behavior
            result = change_badge_status(model.status, model)
            if "error" in result:
                raise BadgeUpdateException("%s" % (result['error']))
            # End custom override code
            
            self._on_model_change(form, model, False)
            self.session.commit()
        except Exception as ex:
            if (not self.handle_view_exception(ex)) or isinstance(ex, BadgeUpdateException):
                flash(str(ex), 'error')
                logging.exception('Failed to update badge status: %s' % (str(ex),))

            self.session.rollback()

            return False
        else:
            self.after_model_change(form, model, False)

        return True
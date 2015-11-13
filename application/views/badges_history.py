from flask.ext.admin.contrib.sqla import ModelView
from application.utils import AdminOnlyMixin


class BadgesHistoryAdmin(AdminOnlyMixin, ModelView):
    """ View history of badge changes with Flask-Admin's ModelView
    """

    can_edit = False
    can_delete = False
    can_create = False
    can_export = True

    list_template = 'list.html'

    column_default_sort = ('change_date', True)
    column_searchable_list = [
        'tblclients.firstname',
        'tblclients.lastname',
        'tblclients.email',
        'changed_by'
    ]
    column_list = [
        'tblclients.full_name',
        'tblclients.email',
        'badge',
        'changed_by',
        'changed_to',
        'change_date'
    ]
    column_labels = {
        'tblclients.full_name': 'Member Name',
        'tblclients.email': 'E-mail'
    }

    column_filters = ['badge', 'changed_to', 'change_date']

    # keeps links backwards compatible if the order of the filters changes
    named_filter_urls = True

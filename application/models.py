import ldap

from application import db, app
from flask.ext.login import UserMixin
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import date
from sqlalchemy.ext.associationproxy import association_proxy


# inspired by http://imil.net/wp/tag/ldap/
class User(UserMixin):
    ''' Used by Flask-Login
        Queries LDAP each page load rather checking in MySQL
    '''
    def __init__(self, uid=None, username=None, password=None):
        self.active = False
        self.admin = False
        
        ldap_result = self.ldap_fetch(uid=uid, username=username, password=password)
        
        if ldap_result is not None:
            self.first_name = ldap_result['first_name']
            self.last_name = ldap_result['last_name']
            self.email = ldap_result['email']
            self.id = ldap_result['id']
            self.username = ldap_result['username']
            self.admin = ldap_result['admin']
            
            self.active = True
            
    def is_active(self):
        return self.active
        
    def is_admin(self):
        return self.admin
        
    # inspired by http://imil.net/wp/tag/ldap/
    def ldap_fetch(self, uid=None, username=None, password=None):
        try:
            ld = ldap.initialize(app.config['LDAP_SERVER'])
            
            if username and password:
                # first login
                ld.simple_bind_s('uid=%s,%s' % (username, app.config['BASE_DN']), password)
                r = ld.search_s(app.config['BASE_DN'], 
                                ldap.SCOPE_SUBTREE,
                                '(uid=%s)' % (username), 
                                ['cn', 'sn', 'uid','uidNumber', 'mail'])
            else:
                # subsequent page visits (used by load_user in hooks.py)
                r = ld.search_s(app.config['BASE_DN'],
                                ldap.SCOPE_SUBTREE,
                                '(uidNumber=%s)' % (uid), 
                                ['cn', 'sn', 'uid','uidNumber', 'mail'])
            
            # determine if username is in admin group
            username = unicode(r[0][1]['uid'][0])
            admins = ld.search_s(app.config['DC_STRING'], ldap.SCOPE_SUBTREE, 'cn=admins', ['memberUid'])
            admin_status = any([True for admin in admins[0][1]['memberUid']
                                if (username.lower() == admin.lower())])

            return {
                'first_name': r[0][1]['cn'][0],
                'last_name': r[0][1]['sn'][0],
                'email': r[0][1]['mail'][0],
                'username': username,
                'id': int(r[0][1]['uidNumber'][0]),
                'admin': admin_status
            }
        except:
            return None


class Badges(db.Model):
    __tablename__ = 'tbl_badges'
    
    id = db.Column(db.Integer, primary_key=True)
    whmcs_user_id = db.Column(db.Integer, db.ForeignKey('dms-whmcs.tblclients.id'))
    badge = db.Column(db.Integer)
    status = db.Column(db.String(16))
    
    def __init__(self, whmcs_user_id=None, badge=None, status=None):
        self.whmcs_user_id = whmcs_user_id
        self.badge = badge
        self.status = status
        
    def __str__(self):
        return self.badge
        
    def __unicode__(self):
        return self.badge
        

class BadgesHistory(db.Model):
    __tablename__ = 'tbl_badges_history'
    
    id = db.Column(db.Integer, primary_key=True)
    whmcs_user_id = db.Column(db.Integer, db.ForeignKey('dms-whmcs.tblclients.id'))
    changed_by = db.Column(db.String(255), nullable=True)
    badge = db.Column(db.Integer)
    changed_to = db.Column(db.String(16))
    change_date = db.Column(db.DateTime)
    
    def __init__(self, whmcs_user_id=None, changed_by=None, badge=None,
                 changed_to=None, change_date=None):
        self.whmcs_user_id = whmcs_user_id
        self.changed_by = changed_by
        self.badge = badge
        self.changed_to = changed_to
        self.change_date = change_date
    
    def __str__(self):
        return self.badge
        
    def __unicode__(self):
        return self.badge


class WHMCSclients(db.Model):
    ''' Table inside WHMCS Database (the billing system)
        This table contains a list of all users in the billing system.
    '''
    __tablename__ = u'tblclients'
    __table_args__ = (
        db.Index(u'firstname_lastname', u'firstname', u'lastname'),
        {'schema': 'dms-whmcs'}
    )

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.Text, nullable=False)
    lastname = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False, index=True)
    
    badges = db.relationship('Badges', backref='tblclients')
    badges_history = db.relationship('BadgesHistory', backref='tblclients')
    products = db.relationship('WHMCSproducts', backref='tblclients')
    addons = association_proxy('products', 'addons')
    
    @hybrid_property
    def full_name(self):
        return self.firstname + ' ' + self.lastname
        
    @hybrid_property
    def active_badges(self):
        return len([badge for badge in self.badges if badge.status == "Active"])
        
    @active_badges.expression
    def active_badges(cls):
        return db.select([
                    db.func.count(Badges.id),
                    Badges.status=='Active'
                ]).as_scalar()
                
    @hybrid_property
    def deactivated_badges(self):
        return len([badge for badge in self.badges if badge.status == "Deactivated"])
        
    @deactivated_badges.expression
    def deactivated_badges(cls):
        return db.select([
                    db.func.count(Badges.id),
                    Badges.status=='Deactivated'
                ]).as_scalar()
                
    @hybrid_property
    def active_products_and_addons(self):
        product_count = 0
        for product in self.products:
            if (product.domainstatus == "Active") and ((not product.nextduedate) or (product.nextduedate > date.today())):
                product_count += 1
            for addon in product.addons:
                if (addon.status == "Active") and ((not addon.nextduedate) or (addon.nextduedate > date.today())):
                    product_count += 1
        return product_count
    
    '''
    @hybrid_property
    def active_products(self):
        product_count = 0
        for product in self.products:
            if (product.domainstatus == "Active") and ((not product.nextduedate) or (product.nextduedate > date.today())):
                product_count += 1
        return product_count
        
    @active_products.expression
    def active_products(self):
        return db.select([
                db.func.count(WHMCSproducts)
            ]).where(db.or_(WHMCSproducts.domainstatus=='Active', WHMCSproducts.nextduedate > date.today())).as_scalar()
            
    @hybrid_property
    def active_addons(self):
        addon_count = 0
        for association in self.addons:
            for addon in association:
                if (addon.status == "Active") and ((not addon.nextduedate) or (addon.nextduedate > date.today())):
                    addon_count += 1
            
        return addon_count
        
    @active_addons.expression
    def active_addons(self):
        return db.select([
                db.func.count(WHMCSaddons)
            ]).where(db.or_(WHMCSaddons.status=='Active', WHMCSaddons.nextduedate > date.today())).as_scalar()
    '''

    def __str__(self):
        return self.firstname + ' ' + self.lastname + ' - ' + self.email
        
    def __unicode__(self):
        return self.firstname + ' ' + self.lastname + ' - ' + self.email

class WHMCSproducts(db.Model):
    ''' Table inside WHMCS Database (the billing system)
        This table contains a list of all regular memberships, but not all family members.
    '''
    __tablename__ = u'tblhosting'
    __table_args__ = {'schema': 'dms-whmcs'}

    id = db.Column(db.Integer, primary_key=True, index=True)
    userid = db.Column(db.Integer, db.ForeignKey('tbl_badges.whmcs_user_id'),
                       db.ForeignKey('dms-whmcs.tblclients.id'), nullable=False,
                       index=True)
    nextduedate = db.Column(db.Date)
    domainstatus = db.Column(db.Enum(u'Pending', u'Active', u'Suspended', u'Terminated', u'Cancelled', u'Fraud'), nullable=False, index=True)
    
    addons = db.relationship('WHMCSaddons', backref='tblhosting')


class WHMCSaddons(db.Model):
    ''' Table inside WHMCS Database (the billing system)
        Contains a list of family memberships.
    '''
    __tablename__ = u'tblhostingaddons'
    __table_args__ = {'schema': 'dms-whmcs'}

    id = db.Column(db.Integer, primary_key=True)
    hostingid = db.Column(db.Integer, db.ForeignKey('dms-whmcs.tblhosting.id'), nullable=False, index=True)
    status = db.Column(db.Enum(u'Pending', u'Active', u'Suspended', u'Terminated', u'Cancelled', u'Fraud'), nullable=False, index=True, server_default=db.text("'Pending'"))
    nextduedate = db.Column(db.Date)
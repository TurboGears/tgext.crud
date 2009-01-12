"""Main Controller"""
from tgtest.lib.base import BaseController
from tg import expose, flash, require, tmpl_context
from tg.controllers import RestController
from pylons.i18n import ugettext as _
from tg import redirect, validate
from tgtest.model import metadata, User, Group, Permission, DBSession
from repoze.what import predicates
import pylons

from formencode import Invalid

from sprox.saormprovider import SAORMProvider
try:
    import tw.dojo
    from catwalk.tg2.dojo_controller import DojoCatwalk as Catwalk
except ImportError:
    from catwalk.tg2 import Catwalk

from tgtest.lib.base import BaseController
from tgtest.widgets.admin import *

class CrudRestController(RestController):
    """
    Set the following in your child classes.
    table = None
    table_filler = None
    model = None
    edit_form = None
    edit_filler = None
    new_form = None
    """
    def __init__(self, session):
        self.provider = SAORMProvider(session)

        #assign the validators since they are none from the parent class
        self.post.decoration.validation.validators = self.new_form
        self.put.decoration.validation.validators  = self.edit_form

    @expose('tgtest.templates.admin.list')
    @expose('json')
    def get(self, *args, **kw):
        if pylons.request.response_type == 'application/json':
            return self.table_filler.get_value(**kw)
        if not pylons.request.url.endswith('/'):
            redirect(pylons.request.url+'/')
        if len(args)  == 0:
            pylons.c.widget = self.table
            return dict(model=self.model.__name__)
        else:
            #this would probably only be realized as a json stream
            pylons.c.widget = self.edit_form
            pks = self.provider.get_primary_fields(self.model)
            kw = {}
            for i, pk in  enumerate(pks):
                kw[pk] = args[i]
            value = self.edit_filler.get_value(kw)
            return dict(value=value)

    @expose('genshi:tgtest.templates.admin.edit')
    def edit(self, *args, **kw):
        pylons.c.widget = self.edit_form
        pks = self.provider.get_primary_fields(self.model)
        kw = {}
        for i, pk in  enumerate(pks):
            kw[pk] = args[i]
        value = self.edit_filler.get_value(kw)
        value['_method'] = 'PUT'
        return dict(value=value, model=self.model.__name__)

    @expose('genshi:tgtest.templates.admin.new')
    def new(self, *args, **kw):
        if pylons.request.url.endswith('/'):
            redirect(pylons.request.url[:-1])
        pylons.c.widget = self.new_form
        return dict(value=kw, model=self.model.__name__)

    @expose()
    @validate(None, error_handler=edit)
    def put(self, *args, **kw):
        pks = self.provider.get_primary_fields(self.model)
        params = pylons.request.params.copy()
        for i, pk in  enumerate(pks):
            if pk not in kw and i < len(args):
                params[pk] = args[i]

        self.provider.update(self.model, params=params)
        redirect('../')

    @expose()
    def delete(self, *args, **kw):
        id = int(args[0])
        obj = DBSession.query(self.model).get(id)
        DBSession.delete(obj)
        redirect('./')

    @expose()
    @validate(None, error_handler=new)
    def post(self, *args, **kw):
        self.provider.create(self.model, params=kw)
        raise redirect('./')


class UserController(CrudRestController):
    table = user_table
    table_filler = user_table_filler
    model = User
    new_form  = user_new_form
    edit_form = user_edit_form
    edit_filler = user_edit_filler

"""
class GroupController(CrudRestController):
    table = group_table
    table_filler = group_table_filler
    model = Group

class PermissionController(CrudRestController):
    table = permission_table
    table_filler = permission_table_filler
    model = Permission
"""
class AdminController(BaseController):
    """
    This is the controller where you can define all of your administrative tasks.
    Notice that Catwalk is instantiated here.
    """

    catwalk = Catwalk(DBSession, metadata)

    @expose('tgtest.templates.admin.index')
    def index(self):
        if not pylons.request.url.endswith('/'):
            redirect(pylons.request.url+'/')
        return dict(page='index')

    users = UserController(DBSession)
   # groups = GroupController(DBSession)
   # permissions = PermissionController(DBSession)
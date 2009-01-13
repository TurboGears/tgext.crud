"""
"""
from tg import expose, flash, redirect
from tg.controllers import RestController
import pylons

from sprox.saormprovider import SAORMProvider
try:
    import chameleon.genshi
    engine = 'chameleon_genshi'
except ImportError:
    engine = genshi

class CrudRestController(RestController):
    """
    Set the following attributes in your child classes:
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

    @expose(engine+':tgext.crud.templates.get_all')
    @expose('json')
    def get_all(self, *args, **kw):
        """Return all records.
           Pagination is done by offset/limit in the filler method.
           Returns an HTML page with the records if not json.
        """
        if pylons.request.response_type == 'application/json':
            return self.table_filler.get_value(**kw)
        if not pylons.request.url.endswith('/'):
            redirect(pylons.request.url+'/')
        pylons.c.widget = self.table
        return dict(model=self.model.__name__)

    @expose(engine+':tgext.crud.templates.get_one')
    @expose('json')
    def get_one(self, *args, **kw):
        """get one record, returns HTML or json"""
        #this would probably only be realized as a json stream
        pylons.c.widget = self.edit_form
        pks = self.provider.get_primary_fields(self.model)
        kw = {}
        for i, pk in  enumerate(pks):
            kw[pk] = args[i]
        value = self.edit_filler.get_value(kw)
        return dict(value=value)

    @expose(engine+':tgext.templates.edit')
    def edit(self, *args, **kw):
        """Display a page to edit the record."""
        pylons.c.widget = self.edit_form
        pks = self.provider.get_primary_fields(self.model)
        kw = {}
        for i, pk in  enumerate(pks):
            kw[pk] = args[i]
        value = self.edit_filler.get_value(kw)
#        value['_method'] = 'PUT'
        return dict(value=value, model=self.model.__name__)

    @expose(engine+':tgext.templates.new')
    def new(self, *args, **kw):
        """Display a page to show a new record."""
        if pylons.request.url.endswith('/'):
            redirect(pylons.request.url[:-1])
        pylons.c.widget = self.new_form
        return dict(value=kw, model=self.model.__name__)

    @expose()
    @validate(None, error_handler=edit)
    def put(self, *args, **kw):
        """update"""
        pks = self.provider.get_primary_fields(self.model)
        params = pylons.request.params.copy()
        for i, pk in  enumerate(pks):
            if pk not in kw and i < len(args):
                params[pk] = args[i]

        self.provider.update(self.model, params=params)
        redirect('../')

    @expose()
    def post_delete(self, *args, **kw):
        """This is the code that actually deletes the record"""
        id = int(args[0])
        obj = DBSession.query(self.model).get(id)
        DBSession.delete(obj)
        redirect('./')

    @expose(engine+':tgext.crud.templates.get_delete')
    def get_delete(self, *args, **kw):
        """This is the code that creates a confirm_delete page"""
        return dict(args=args)

    @expose()
    @validate(None, error_handler=new)
    def post(self, *args, **kw):
        self.provider.create(self.model, params=kw)
        raise redirect('./')

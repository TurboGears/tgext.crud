"""
"""
from tg import expose, flash, redirect
from tg.decorators import without_trailing_slash, with_trailing_slash
from tg.controllers import RestController
import pylons

from decorators import registered_validate, register_validators, catch_errors

from sprox.saormprovider import SAORMProvider
engine = 'genshi'
try:
    import chameleon.genshi
    import pylons.config
    if 'renderers' in pylons.config and 'chameleon_genshi' in pylons.config['renderers']:
        engine = 'chameleon_genshi'
except ImportError:
    pass

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
        self.session = session
        self.validators = {}
        
        #register the validators since they are none from the parent class
        register_validators(self, 'post', self.new_form)
        register_validators(self, 'put', self.edit_form)

    @with_trailing_slash
    @expose(engine+':tgext.crud.templates.get_all')
    @expose('json')
    def get_all(self, *args, **kw):
        """Return all records.
           Pagination is done by offset/limit in the filler method.
           Returns an HTML page with the records if not json.
        """
        if pylons.request.response_type == 'application/json':
            return self.table_filler.get_value(**kw)
        
        values = []
        try:
            import tw.dojo
            from sprox.dojo.tablebase import DojoTableBase as TableBase
            from sprox.dojo.fillerbase import DojoTableFiller as TableFiller
        except ImportError:
            import warnings
            warnings.warn("""tgext.crud does not support pagination without dojo, so for your safety we have limited the
            number of records displayed to 10.""")
            values = self.table_filler.get_value(limit=10)
        pylons.c.widget = self.table
        return dict(model=self.model.__name__, values=values)

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

    @expose(engine+':tgext.crud.templates.edit')
    def edit(self, *args, **kw):
        """Display a page to edit the record."""
        pylons.c.widget = self.edit_form
        pks = self.provider.get_primary_fields(self.model)
        kw = {}
        for i, pk in  enumerate(pks):
            kw[pk] = args[i]
        value = self.edit_filler.get_value(kw)
        value['_method'] = 'PUT'
        return dict(value=value, model=self.model.__name__)

    @without_trailing_slash
    @expose(engine+':tgext.crud.templates.new')
    def new(self, *args, **kw):
        """Display a page to show a new record."""
        pylons.c.widget = self.new_form
        return dict(value=kw, model=self.model.__name__)

    @expose()
    @registered_validate(error_handler=new)
    def post(self, *args, **kw):
        self.provider.create(self.model, params=kw)
        raise redirect('./')
    
    @expose()
    @registered_validate(error_handler=edit)
    def put(self, *args, **kw):
        """update"""
        pks = self.provider.get_primary_fields(self.model)
        for i, pk in enumerate(pks):
            if pk not in kw and i < len(args):
                kw[pk] = args[i]

        self.provider.update(self.model, params=kw)
        redirect('../')

    @expose()
    def post_delete(self, *args, **kw):
        """This is the code that actually deletes the record"""
        id = int(args[0])
        obj = self.session.query(self.model).get(id)
        self.session.delete(obj)
        redirect('./')

    @expose(engine+':tgext.crud.templates.get_delete')
    def get_delete(self, *args, **kw):
        """This is the code that creates a confirm_delete page"""
        return dict(args=args)



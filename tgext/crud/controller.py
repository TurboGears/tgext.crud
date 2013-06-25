"""
"""
import tg
from tg import expose, flash, redirect, tmpl_context, request, abort
from tg.decorators import without_trailing_slash, with_trailing_slash, before_validate
from tg.controllers import RestController

from tgext.crud.decorators import (registered_validate, register_validators, catch_errors,
                                   optional_paginate)
from tgext.crud.utils import (SmartPaginationCollection, RequestLocalTableFiller, create_setter,
                              set_table_filler_getter, SortableTableBase, map_args_to_pks,
                              adapt_params_for_pagination, allow_json_parameters)
from sprox.providerselector import ProviderTypeSelector
from sprox.fillerbase import TableFiller
from sprox.formbase import AddRecordForm, EditableForm
from sprox.fillerbase import RecordFiller, AddFormFiller
from markupsafe import Markup

errors = ()
try:
    from sqlalchemy.exc import IntegrityError, DatabaseError, ProgrammingError
    errors =  (IntegrityError, DatabaseError, ProgrammingError)
except ImportError:
    pass

import urlparse, cgi, inspect

class CrudRestControllerHelpers(object):
    def make_link(self, where, pk_count=0):
        if not where.startswith('/'):
            where = '../' * (1 + pk_count) + where
        return where

class CrudRestController(RestController):
    """
    :variables:

    session
      database session (drives drop-down menus

    menu_items
      Dictionary of links to other models in the form model_items[lower_model_name] = Model

    title
      Title to be used for each page.  default: Turbogears Admin System

    :modifiers:

    model
      Model this class is associated with

    table
      Widget for the table display

    table_filler
      Class instance with get_value() that defines the JSon stream for the table

    edit_form
      Form to be used for editing the model

    edit_filler
      Class instance with a get_value() that defines how we get information for a single
      existing record

    new_form
      Form that defines how we create a form for new data entry.

    :Attributes:

      menu_items
        Dictionary of associated Models (used for menu)
      provider
        sprox provider for data manipulation
      session
        link to the database
    """

    title = "Turbogears Admin System"
    keep_params = None
    remember_values = []
    substring_filters = []
    search_fields = True  # True for automagic
    json_dictify = False # True is slower but provides relations
    conditional_update_field = None
    pagination = {'items_per_page': 7}
    style = Markup('''
#menu_items {
  padding:0px 12px 0px 2px;
  list-style-type:None;
  padding-left:0px;
}

#crud_leftbar {
    float:left;
    padding-left:0px;
}

#crud_content {
    float:left;
    width:80%;
}

#crud_content > h1,
.crud_edit > h2,
.crud_add > h2 {
    margin-top: 1px;
}

#crud_btn_new {
    margin:1ex 0;
}

#crud_btn_new > span {
    margin-left:2em;
}

#crud_search {
    float: right;
}

#crud_search input {
    border: 1px solid #CCC;
    background-color: white;
}

#crud_search input:hover {
    background-color: #EFEFEF;
}
''')

    def _before(self, *args, **kw):
        tmpl_context.title = self.title
        tmpl_context.menu_items = self.menu_items
        tmpl_context.kept_params = self._kept_params()
        tmpl_context.crud_helpers = self.helpers
        tmpl_context.crud_style = self.style

    __before__ = _before #This can be removed since 2.2

    def _mount_point(self):
        try:
            mount_point = self.mount_point
        except:
            mount_point = None

        if not mount_point:
            #non statically mounted or Old TurboGears, use relative URL
            mount_point = '.'

        return mount_point

    def _kept_params(self):
        if not self.keep_params:
            return {}

        if not request.referer:
            from_referer = {}
        else:
            parsed = urlparse.urlparse(request.referer)
            from_referer = dict(cgi.parse_qsl(parsed.query))
        from_referer.update(request.params)

        pass_params = {}
        for k in self.keep_params:
            if k in from_referer:
                pass_params[k] = from_referer[k]
        return pass_params

    def _adapt_menu_items(self, menu_items):
        adapted_menu_items = type(menu_items)()

        for link, model in menu_items.iteritems():
            if inspect.isclass(model):
                adapted_menu_items[link + 's'] = model.__name__
            else:
                adapted_menu_items[link] = model
        return adapted_menu_items

    def _get_search_fields(self, kw):
        if self.search_fields is True:
            return [
                (field, self.table.__headers__.get(field, field), kw.get(field, False))
                    for field in self.table.__fields__
                        if field != '__actions__'
                ]
        elif self.search_fields:
            # This allows for customizing the search fields to be shown in the table definition
            # search_fields can be either a list of tuples with (field, name) or just a string field = name
            search_fields = []
            for field in self.search_fields:
                if isinstance(field, basestring):
                    search_fields.append((field, field), kw.get(field, False))
                else:
                    search_fields.append(field[0:2], kw.get(field, False))
            return search_fields
        else:
            # This would be where someone explicitly disabled the search functionality
            return []

    def _get_current_search(self, search_fields):
        for field, _, value in search_fields:
            if value is not False:
                return (field, value)
        return (search_fields[0][0], '')

    def _dictify(self, value, length=None):
        json_dictify = self.json_dictify
        if json_dictify is False:
            return value

        def _dictify(entity):
            if hasattr(entity, '__json__'):
                return entity.__json__()
            else:
                return self.provider.dictify(entity, **json_dictify)

        if length is not None:
            #return a generator, we don't want to consume the whole query if it is paginated
            return (_dictify(entity) for entity in value)
        else:
            return _dictify(value)

    def __init__(self, session, menu_items=None):
        if menu_items is None:
            menu_items = {}
        self.menu_items = self._adapt_menu_items(menu_items)
        self.helpers = CrudRestControllerHelpers()
        self.provider = ProviderTypeSelector().get_selector(self.model).get_provider(self.model, hint=session)
        
        self.session = session

        self.pagination_enabled = (self.pagination and isinstance(self.table_filler, RequestLocalTableFiller))
        if self.json_dictify is True:
            self.json_dictify = {}

        #this makes crc declarative
        check_types = ['new_form', 'edit_form', 'table', 'table_filler', 'edit_filler']
        for type_ in check_types:
            if not hasattr(self, type_) and hasattr(self, type_+'_type'):
                setattr(self, type_, getattr(self, type_+'_type')(self.session))

        if hasattr(self, 'new_form'):
            #register the validators since they are none from the parent class
            register_validators(self, 'post', self.new_form)
        if hasattr(self, 'edit_form'):
            register_validators(self, 'put', self.edit_form)

    @with_trailing_slash
    @expose('genshi:tgext.crud.templates.get_all')
    @expose('mako:tgext.crud.templates.get_all')
    @expose('jinja:tgext.crud.templates.get_all')
    @expose('json:')
    @optional_paginate('value_list')
    def get_all(self, *args, **kw):
        """Return all records.
           Pagination is done by offset/limit in the filler method.
           Returns an HTML page with the records if not json.
        """
        if self.pagination:
            paginator = request.paginators['value_list']
            paginator.paginate_items_per_page = self.pagination['items_per_page']
        else:
            paginator = request.paginators['value_list']
            paginator.paginate_items_per_page = -1
            paginator.paginate_page = 0

        if tg.request.response_type == 'application/json':
            adapt_params_for_pagination(kw, self.pagination_enabled)
            try:
                count, values = self.table_filler._do_get_provider_count_and_objs(**kw)
            except Exception as e:
                abort(400, detail=unicode(e))
            values = self._dictify(values, length=count)
            if self.pagination_enabled:
                values = SmartPaginationCollection(values, count)
            return dict(value_list=values)

        if not getattr(self.table.__class__, '__retrieves_own_value__', False):
            kw.pop('substring_filters', None)
            if self.substring_filters is True:
                substring_filters = kw.keys()
            else:
                substring_filters = self.substring_filters

            adapt_params_for_pagination(kw, self.pagination_enabled)
            try:
                values = self.table_filler.get_value(substring_filters=substring_filters, **kw)
            except Exception as e:
                flash(u'Invalid search query "%s": %s' % (request.query_string, e), 'warn')
                # Reset all variables to sane defaults
                kw = {}
                values = []
                self.table_filler.__count__ = 0
            if self.pagination_enabled:
                values = SmartPaginationCollection(values, self.table_filler.__count__)
        else:
            values = []

        tmpl_context.widget = self.table
        search_fields = self._get_search_fields(kw)
        current_search = self._get_current_search(search_fields)
        return dict(model=self.model.__name__, value_list=values,
                    mount_point=self._mount_point(),
                    headers=search_fields,  # Just for backwards compatibility
                    search_fields=search_fields, current_search=current_search)

    @expose('genshi:tgext.crud.templates.get_one')
    @expose('mako:tgext.crud.templates.get_one')
    @expose('jinja:tgext.crud.templates.get_one')
    @expose('json:')
    def get_one(self, *args, **kw):
        """get one record, returns HTML or json"""
        #this would probably only be realized as a json stream
        kw = map_args_to_pks(args, {})

        if tg.request.response_type == 'application/json':
            obj = self.provider.get_obj(self.model, kw)
            if obj is None:
                tg.response.status_code = 404
            elif self.conditional_update_field is not None:
                tg.response.last_modified = getattr(obj, self.conditional_update_field)

            return dict(model=self.model.__name__,
                        value=self._dictify(obj))

        tmpl_context.widget = self.edit_form
        value = self.edit_filler.get_value(kw)
        return dict(value=value, model=self.model.__name__)

    @expose('genshi:tgext.crud.templates.edit')
    @expose('mako:tgext.crud.templates.edit')
    @expose('jinja:tgext.crud.templates.edit')
    def edit(self, *args, **kw):
        """Display a page to edit the record."""
        pks = self.provider.get_primary_fields(self.model)
        kw = map_args_to_pks(args, {})

        tmpl_context.widget = self.edit_form
        value = self.edit_filler.get_value(kw)
        value['_method'] = 'PUT'
        return dict(value=value, model=self.model.__name__, pk_count=len(pks))

    @without_trailing_slash
    @expose('genshi:tgext.crud.templates.new')
    @expose('mako:tgext.crud.templates.new')
    @expose('jinja:tgext.crud.templates.new')
    def new(self, *args, **kw):
        """Display a page to show a new record."""
        tmpl_context.widget = self.new_form
        return dict(value=kw, model=self.model.__name__)

    @expose(content_type='text/html')
    @expose('json:', content_type='application/json')
    @before_validate(allow_json_parameters)
    @catch_errors(errors, error_handler=new)
    @registered_validate(error_handler=new)
    def post(self, *args, **kw):
        obj = self.provider.create(self.model, params=kw)

        if tg.request.response_type == 'application/json':
            if obj is not None and self.conditional_update_field is not None:
                tg.response.last_modified = getattr(obj, self.conditional_update_field)

            return dict(model=self.model.__name__,
                        value=self._dictify(obj))

        return redirect('./', params=self._kept_params())

    @expose(content_type='text/html')
    @expose('json:', content_type='application/json')
    @before_validate(allow_json_parameters)
    @before_validate(map_args_to_pks)
    @registered_validate(error_handler=edit)
    @catch_errors(errors, error_handler=edit)
    def put(self, *args, **kw):
        """update"""
        omit_fields = []
        if getattr(self, 'edit_form', None):
            omit_fields.extend(self.edit_form.__omit_fields__)

        for remembered_value in self.remember_values:
            value = kw.get(remembered_value)
            if value is None or value == '':
                omit_fields.append(remembered_value)

        obj = self.provider.get_obj(self.model, kw)

        #This should actually by done by provider.update to make it atomic
        can_modify = True
        if obj is not None and self.conditional_update_field is not None and \
           tg.request.if_unmodified_since is not None and \
           tg.request.if_unmodified_since < getattr(obj, self.conditional_update_field):
                can_modify = False

        if obj is not None and can_modify:
            obj = self.provider.update(self.model, params=kw, omit_fields=omit_fields)

        if tg.request.response_type == 'application/json':
            if obj is None:
                tg.response.status_code = 404
            elif can_modify is False:
                tg.response.status_code = 412
            elif self.conditional_update_field is not None:
                tg.response.last_modified = getattr(obj, self.conditional_update_field)

            return dict(model=self.model.__name__,
                        value=self._dictify(obj))

        pks = self.provider.get_primary_fields(self.model)
        return redirect('../' * len(pks), params=self._kept_params())

    @expose(content_type='text/html')
    @expose('json:', content_type='application/json')
    def post_delete(self, *args, **kw):
        """This is the code that actually deletes the record"""
        kw = map_args_to_pks(args, {})

        obj = None
        if kw:
            obj = self.provider.get_obj(self.model, kw)

        if obj is not None:
            self.provider.delete(self.model, kw)

        if tg.request.response_type == 'application/json':
            return dict()

        pks = self.provider.get_primary_fields(self.model)
        return redirect('./' + '../' * (len(pks) - 1), params=self._kept_params())

    @expose('genshi:tgext.crud.templates.get_delete')
    @expose('jinja:tgext.crud.templates.get_delete')
    def get_delete(self, *args, **kw):
        """This is the code that creates a confirm_delete page"""
        return dict(args=args)

class EasyCrudRestController(CrudRestController):
    def __init__(self, session, menu_items=None):
        if not hasattr(self, 'table'):
            class Table(SortableTableBase):
                __entity__=self.model
            self.table = Table(session)

        if not hasattr(self, 'table_filler'):
            class MyTableFiller(RequestLocalTableFiller):
                __entity__ = self.model
            self.table_filler = MyTableFiller(session)

        if not hasattr(self, 'edit_form'):
            class EditForm(EditableForm):
                __entity__ = self.model
            self.edit_form = EditForm(session)

        if not hasattr(self, 'edit_filler'):
            class EditFiller(RecordFiller):
                __entity__ = self.model
            self.edit_filler = EditFiller(session)

        if not hasattr(self, 'new_form'):
            class NewForm(AddRecordForm):
                __entity__ = self.model
            self.new_form = NewForm(session)

        if not hasattr(self, 'new_filler'):
            class NewFiller(AddFormFiller):
                __entity__ = self.model
            self.new_filler = NewFiller(session)
        
        super(EasyCrudRestController, self).__init__(session, menu_items)

        #Permit to quickly customize form options
        if hasattr(self, '__form_options__'):
            for name, value in self.__form_options__.iteritems():
                for form in (self.edit_form, self.new_form):
                    if form:
                        setattr(form, name, value)

        #Permit to quickly create custom actions to set values
        if hasattr(self, '__setters__'):
            for name, config in self.__setters__.iteritems():
                setattr(self, name, create_setter(self, self.get_all, config))


        #Permit to quickly customize table options
        if hasattr(self, '__table_options__'):
            for name, value in self.__table_options__.iteritems():
                if name.startswith('__') and name != '__actions__':
                    for table_object in (self.table_filler, self.table):
                        if table_object:
                            setattr(table_object, name, value)
                else:
                    if self.table_filler:
                        set_table_filler_getter(self.table_filler, name, value)

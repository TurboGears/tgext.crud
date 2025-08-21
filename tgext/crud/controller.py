"""
"""
import logging
from itertools import chain
import urllib

import tg
from tg import expose, flash, redirect, tmpl_context, request, abort
from tg.decorators import without_trailing_slash, with_trailing_slash, before_validate, before_render
from tg.controllers import RestController

from tgext.crud.decorators import (registered_validate, register_validators, catch_errors,
                                   optional_paginate, apply_default_filters, map_primary_keys)
from tgext.crud.utils import (SmartPaginationCollection, RequestLocalTableFiller,
                              set_table_filler_getter, SortableTableBase, map_args_to_pks,
                              adapt_params_for_pagination, allow_json_parameters, 
                              force_response_type, redirect_on_completion, _addoptsdict,
                              _addoptslist)
from sprox.providerselector import ProviderTypeSelector
from sprox.formbase import AddRecordForm, EditableForm
from sprox.fillerbase import RecordFiller, AddFormFiller
from .resources import CSSSource, crud_style, crud_script
import warnings

errors = ()
try:
    from sqlalchemy.exc import IntegrityError, DatabaseError, ProgrammingError
    errors = (IntegrityError, DatabaseError, ProgrammingError)
except ImportError:
    pass

import cgi, inspect
from tgext.crud._compat import url_parse, string_type, unicode_text

log = logging.getLogger('tgext.crud')

class CrudRestControllerHelpers(object):
    def make_link(self, where, pk_count=0):
        if not where.startswith('/'):
            where = '../' * (1 + pk_count) + where
        return where

class CrudRestController(RestController):
    """
    :initialization options:

        **session**
              database session 

        **menu_items**
            Dictionary or mapping type of links to other CRUD sections.
            This is used to generate the links sidebar of the CRUD interface.
            Can be specified in the form ``model_items['lower_model_name'] = ModelClass`` or
            ``model_items['link'] = 'Name'``.

    :class attributes:

        **title**
            Title to be used for each page.  default: ``'Turbogears Admin System'``

        **model**
            Model this class is associated with.

        **remember_values**
            List of model attributes that need to keep previous value when not provided
            on submission instead of replacing the existing value with an empty one.
            It's commonly used with file fields to avoid having to reupload the file
            again when the model is edited.

        **keep_params**
            List of URL parameters that need to be kept around when redirecting between
            the various pages of the CRUD controller. Can be used to keep around filters
            or sorting when editing a subset of the models.

        **filters**
            Dictionary of filters that must be applied to queries. Those are only "equals to"
            filters that can be used to limit objects to a subset of entries that have that
            value. Filters are also applied on POST method to create new object which by
            default have the value specified by the filter. If filter is callable it will
            be called to retrieve the filter value.

            For example to display a crud that only shows, creates and edits entities
            owned by logged user through a user_id ForeignKey you can use a filter like::

                {'user_id': lambda: request.identity['user'].user_id}

        **search_fields**
            Enables searching on some fields, can be ``True``, ``False`` or a list
            of fields for which searching should be enabled.

        **substring_filters**
            Enable substring filtering for some fields, by default is disabled.
            Pass ``True`` to enable it on all fields or pass a list of field
            names to enable it only on some fields.

        **json_dictify**
            ``True`` or ``False``, enables advanced dictification of retrieved models
            when providing JSON responses. This also enables JSON encoding of related entities
            for the returned model.

        **conditional_update_field**
            Name of the field used to perform conditional updates when ``PUT`` method is
            used as a REST API. ``None`` disables conditional updates (which is the default).

        **pagination**
            Dictionary of options for pagination. ``False`` disables pagination.
            By default ``{'items_per_page': 7}`` is provided.
            Currently the only supported option is ``items_per_page``.

        **response_type**
            Limit response to a single format, can be: 'application/json' or 'text/html'. 
            By default tgext.crud will detect expected response from Accept header and 
            will provide response content according to the expected one. If you want
            to avoid HTML access to a plain JSON API you can use this option to limit
            valid responses to application/json.
            
        **provider_type_selector_type**
            Use a custom provider type selector class.
            By default the ``sprox.providerselector.ProviderTypeSelector`` class will
            be used to instantiate a provider selector that can select the right provider
            for ming and sqlalchemy. In case you are not using ming or sqlalchemy or you just
            want to change the default behavior of the provider selector, you can override this.

        **resources**
            A list of CSSSource / JSSource that have to be injected inside CRUD
            pages when rendering. By default ``tgext.crud.resources.crud_style`` and
            ``tgext.crud.resources.crud_script`` are injected.

        **table**
            The ``sprox.tablebase.TableBase`` Widget instance used to display the table.
            By default ``tgext.crud.utils.SortableTableBase`` is used which permits to sort
            table by columns.

        **table_filler**
            The ``sprox.fillerbase.TableFiller`` instance used to retrieve data for the table.
            If you want to customize how data is retrieved override the 
            ``TableFiller._do_get_provider_count_and_objs`` method to return different entities and count.
            By default ``tgext.crud.utils.RequestLocalTableFiller`` is used which keeps
            track of the numer of entities retrieved during the current request to enable pagination.

        **edit_form**
            Form to be used for editing an existing model. 
            By default ``sprox.formbase.EditForm`` is used.

        **edit_filler**
            ``sprox.fillerbase.RecordFiller`` subclass used to load the values for
            an entity that need to be edited. Override the ``RecordFiller.get_value``
            method to provide custom values.

        **new_form**
            Form that defines how to create a new model.
            By default ``sprox.formbase.AddRecordForm`` is used.
    """
    title = "Turbogears Admin System"
    keep_params = None
    remember_values = []
    substring_filters = []
    search_fields = True  # True for automagic
    json_dictify = False  # True is slower but provides relations
    conditional_update_field = None
    response_type = None
    provider_type_selector_type = ProviderTypeSelector
    filters = {}
    pagination = {'items_per_page': 7}
    resources = ( crud_style,
                  crud_script )

    def _before(self, *args, **kw):
        tmpl_context.title = self.title
        tmpl_context.menu_items = self.menu_items
        tmpl_context.kept_params = self._kept_params()
        tmpl_context.crud_helpers = self.helpers

        for resource in self.resources:
            resource.inject()

        force_response_type(self.response_type)

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
            parsed = url_parse(request.referer)
            from_referer = dict(urllib.parse.parse_qsl(parsed.query))
        from_referer.update(request.params)

        pass_params = {}
        for k in self.keep_params:
            if k in from_referer:
                pass_params[k] = from_referer[k]
        return pass_params

    def _adapt_menu_items(self, menu_items):
        adapted_menu_items = type(menu_items)()

        for link, model in menu_items.items():
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
                if isinstance(field, string_type):
                    search_fields.append((field, field, kw.get(field, False)))
                else:
                    search_fields.append((field[0], field[1], kw.get(field[0], False)))
            return search_fields
        else:
            # This would be where someone explicitly disabled the search functionality
            return []

    def _get_current_search(self, search_fields):
        if not search_fields:
            return None

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

    def _get_object(self, params):
        if self.filters:
            queryfields = set(chain(self.provider.get_primary_fields(self.model),
                                    self.filters.keys()))
            filters = dict(t for t in params.items() if t[0] in queryfields)
            _, val = self.provider.query(self.model, filters=filters, limit=1)
            val = next(iter(val), None)
        else:
            val = self.provider.get_obj(self.model, params)
        return val

    def __init__(self, session, menu_items=None):
        if hasattr(self, 'style'):
            warnings.warn('style attribute is not supported anymore, '
                          'resources attribute replaces it', DeprecationWarning,
                          stacklevel=2)
            self.resources = (crud_script,
                              CSSSource(location='headbottom',
                                        src=self.style))

        if menu_items is None:
            menu_items = {}

        self.menu_items = self._adapt_menu_items(menu_items)
        self.helpers = CrudRestControllerHelpers()
        self.provider = self.provider_type_selector_type().get_selector(self.model).get_provider(self.model, hint=session)
        self.session = session

        if self.json_dictify is True:
            self.json_dictify = {}

        #this makes crc declarative
        check_types = ['new_form', 'edit_form', 'table', 'table_filler', 'edit_filler']
        for type_ in check_types:
            if not hasattr(self, type_) and hasattr(self, type_+'_type'):
                setattr(self, type_, getattr(self, type_+'_type')(self.session))

        # Enable pagination only if table_filler has support for request local __count__
        self.pagination_enabled = (self.pagination and isinstance(self.table_filler, RequestLocalTableFiller))

        # Register forms that need to be validated for each action.
        if hasattr(self, 'new_form'):
            register_validators(self, 'post', self.new_form)
        if hasattr(self, 'edit_form'):
            register_validators(self, 'put', self.edit_form)

    @with_trailing_slash
    @expose('genshi:tgext.crud.templates.get_all')
    @expose('mako:tgext.crud.templates.get_all')
    @expose('jinja:tgext.crud.templates.get_all')
    @expose('kajiki:tgext.crud.templates.get_all')
    @expose('json:')
    @optional_paginate('value_list')
    @apply_default_filters
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
                log.exception('Failed to retrieve table data')
                abort(400, detail=unicode_text(e))
            values = self._dictify(values, length=count)
            if self.pagination_enabled:
                values = SmartPaginationCollection(values, count)
            return dict(value_list=values)

        if not getattr(self.table.__class__, '__retrieves_own_value__', False):
            kw.pop('substring_filters', None)
            if self.substring_filters is True:
                substring_filters = list(set(kw.keys()) - set(['limit', 'offset', 'order_by', 'desc']))
            else:
                substring_filters = self.substring_filters

            adapt_params_for_pagination(kw, self.pagination_enabled)
            try:
                values = self.table_filler.get_value(substring_filters=substring_filters, **kw)
            except Exception as e:
                log.exception('Failed to retrieve table data')
                flash('Unable to retrieve data (Filter "%s": %s)' % (request.query_string, e), 'warn')
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
    @expose('kajiki:tgext.crud.templates.get_one')
    @expose('json:')
    @map_primary_keys(argsonly=True)
    @apply_default_filters
    def get_one(self, *args, **kw):
        """get one record, returns HTML or json"""
        obj = self._get_object(kw)

        if tg.request.response_type == 'application/json':
            if obj is None:
                tg.response.status_code = 404
            elif self.conditional_update_field is not None:
                tg.response.last_modified = getattr(obj, self.conditional_update_field)

            return dict(model=self.model.__name__,
                        value=self._dictify(obj))

        if obj is None:
            abort(404)

        tmpl_context.widget = self.edit_form
        value = self.edit_filler.get_value(kw)
        return dict(value=value, model=self.model.__name__)

    @expose('genshi:tgext.crud.templates.edit')
    @expose('mako:tgext.crud.templates.edit')
    @expose('jinja:tgext.crud.templates.edit')
    @expose('kajiki:tgext.crud.templates.edit')
    @map_primary_keys(argsonly=True)
    @apply_default_filters
    def edit(self, *args, **kw):
        """Display a page to edit the record."""
        if getattr(self, 'edit_form', None) is None:
            abort(404)

        obj = self._get_object(kw)
        if obj is None:
            abort(404)

        tmpl_context.widget = self.edit_form
        value = self.edit_filler.get_value(kw)
        value['_method'] = 'PUT'
        return dict(value=value, model=self.model.__name__,
                    pk_count=len(self.provider.get_primary_fields(self.model)))

    @without_trailing_slash
    @expose('genshi:tgext.crud.templates.new')
    @expose('mako:tgext.crud.templates.new')
    @expose('jinja:tgext.crud.templates.new')
    @expose('kajiki:tgext.crud.templates.new')
    def new(self, *args, **kw):
        """Display a page to show a new record."""
        if getattr(self, 'new_form', None) is None:
            abort(404)

        tmpl_context.widget = self.new_form
        return dict(value=kw, model=self.model.__name__)

    @expose(content_type='text/html')
    @expose('json:', content_type='application/json')
    @before_validate(allow_json_parameters)
    @apply_default_filters
    @before_render(redirect_on_completion)
    @registered_validate(error_handler='new')
    @catch_errors(errors, error_handler='new')
    def post(self, *args, **kw):
        obj = self.provider.create(self.model, params=kw)

        if tg.request.response_type == 'application/json':
            if obj is not None and self.conditional_update_field is not None:
                tg.response.last_modified = getattr(obj, self.conditional_update_field)

            return dict(model=self.model.__name__,
                        value=self._dictify(obj))

        return dict(obj=obj,
                    redirect=dict(base_url='./', params=self._kept_params()))

    @expose(content_type='text/html')
    @expose('json:', content_type='application/json')
    @before_validate(allow_json_parameters)
    @map_primary_keys()
    @apply_default_filters
    @before_render(redirect_on_completion)
    @registered_validate(error_handler='edit')
    @catch_errors(errors, error_handler='edit')
    def put(self, *args, **kw):
        """update"""
        omit_fields = []
        if getattr(self, 'edit_form', None):
            omit_fields.extend(self.edit_form.__omit_fields__)

        for remembered_value in self.remember_values:
            value = kw.get(remembered_value)
            if value is None or value == '':
                omit_fields.append(remembered_value)

        obj = self._get_object(kw)

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

        if obj is None:
            abort(404)

        pks = self.provider.get_primary_fields(self.model)
        return dict(obj=obj,
                    redirect=dict(base_url='../' * len(pks), params=self._kept_params()))

    @expose(content_type='text/html')
    @expose('json:', content_type='application/json')
    @map_primary_keys(argsonly=True)
    @apply_default_filters
    @before_render(redirect_on_completion)
    def post_delete(self, *args, **kw):
        """This is the code that actually deletes the record"""
        obj = None
        if kw:
            obj = self._get_object(kw)

        if obj is not None:
            self.provider.delete(self.model, kw)

        if tg.request.response_type == 'application/json':
            return dict()

        pks = self.provider.get_primary_fields(self.model)
        return dict(obj=obj,
                    redirect=dict(base_url='./' + '../' * (len(pks) - 1),
                                  params=self._kept_params()))

    @expose('genshi:tgext.crud.templates.get_delete')
    @expose('jinja:tgext.crud.templates.get_delete')
    def get_delete(self, *args, **kw):
        """This is the code that creates a confirm_delete page"""
        return dict(args=args)


class EasyCrudRestController(CrudRestController):
    """A CrudRestController that provides a quick way to setup Sprox forms and Table.

    Form options are available through the ``__form_options__`` dictionary which
    can contain any option accepted by sprox :class:`FormBase`. Options specific to
    *NewForm* and *EditForm*  can be provided through ``__form_new_options__`` and
    ``__form_edit_options__``.

    Table options are available through the ``__table_options__`` dictionary which
    can contain any option accepted by sprox :class:`TableBase`. Dictionary keys
    that do not start with **__** will be threated as :class:`TableFiller` attributes
    apart from ``__actions__`` which is always assigned to the :class:`TableFiller`.

    Usually ``_options`` fields will replace the previous values with theirs
    in case a parent class provided previous values. You can avoid this behaviour
    and extend the previous values using :func:`.addopts` instead of dictionaries
    and lists as the option values.

    :class attributes:

        **__form_options__**
            Sprox options that need to be applied to both EditableForm and AddRecordForm forms

        **__form_new_options__**
            Options that need to be applied only to AddRecordForm form

        **__form_edit_options__**
            Options that need to be applied only to EditableForm form

        **__table_options__**
            Options that need to be applied to TableBase and TableFiller
    
    """
    def __init__(self, session, menu_items=None):
        if not (hasattr(self, 'table') or hasattr(self, 'table_type')):
            class Table(SortableTableBase):
                __entity__=self.model
            self.table = Table(session)

        if not (hasattr(self, 'table_filler') or hasattr(self, 'table_filler_type')):
            class MyTableFiller(RequestLocalTableFiller):
                __entity__ = self.model
            self.table_filler = MyTableFiller(session)

        if not (hasattr(self, 'edit_form') or hasattr(self, 'edit_form_type')):
            class EditForm(EditableForm):
                __entity__ = self.model
            self.edit_form = EditForm(session)

        if not (hasattr(self, 'edit_filler') or hasattr(self, 'edit_filler_type')):
            class EditFiller(RecordFiller):
                __entity__ = self.model
            self.edit_filler = EditFiller(session)

        if not (hasattr(self, 'new_form') or hasattr(self, 'new_form_type')):
            class NewForm(AddRecordForm):
                __entity__ = self.model
            self.new_form = NewForm(session)

        if not (hasattr(self, 'new_filler') or hasattr(self, 'new_filler_type')):
            class NewFiller(AddFormFiller):
                __entity__ = self.model
            self.new_filler = NewFiller(session)
        
        super(EasyCrudRestController, self).__init__(session, menu_items)

        # Permit to quickly customize form options
        if hasattr(self, '__form_options__'):
            for form in (self.edit_form, self.new_form):
                if form:
                    for name, value in self.__form_options__.items():
                        if isinstance(value, (_addoptsdict, _addoptslist)):
                            value.extend_option(form, name)
                        else:
                            setattr(form, name, value)

        if hasattr(self, '__form_new_options__') and self.new_form:
            for name, value in self.__form_new_options__.items():
                if isinstance(value, (_addoptsdict, _addoptslist)):
                    value.extend_option(self.new_form, name)
                else:
                    setattr(self.new_form, name, value)

        if hasattr(self, '__form_edit_options__') and self.edit_form:
            for name, value in self.__form_edit_options__.items():
                if isinstance(value, (_addoptsdict, _addoptslist)):
                    value.extend_option(self.edit_form, name)
                else:
                    setattr(self.edit_form, name, value)

        if hasattr(self, '__setters__'):
            raise ValueError('__setters__ are deprecated and no longer supported.')

        # Permit to quickly customize table options
        if hasattr(self, '__table_options__'):
            if self.table_filler:
                for name, value in self.__table_options__.items():
                    if name == '__actions__':
                        set_table_filler_getter(self.table_filler, name, value)
                    elif name.startswith('__'):
                        setattr(self.table_filler, name, value)
                    else:
                        set_table_filler_getter(self.table_filler, name, value)

            if self.table:
                for name, value in self.__table_options__.items():
                    if name.startswith('__') and name != '__actions__':
                        setattr(self.table, name, value)

from tg import expose, validate, redirect, request, url, tmpl_context
from sprox.tablebase import TableBase
from sprox.fillerbase import TableFiller
from markupsafe import Markup
from markupsafe import escape_silent as escape
from tgext.crud._compat import PY2

try:
    from tw2.core import Widget as Tw2Widget
except ImportError:
    class Tw2Widget(object):
        pass

from sprox.widgets import Widget as SproxWidget

def sprox_with_tw2():
    return SproxWidget is Tw2Widget

if sprox_with_tw2():
    from tw2.forms.datagrid import Column
else:
    from tw.forms.datagrid import Column

def set_table_filler_getter(filler, name, function):
    meth = function.__get__(filler, filler.__class__)
    setattr(filler, name, meth)

class SortableColumn(Column):
    def __init__(self, name, *args, **kw):
        super(SortableColumn, self).__init__(name, *args, **kw)
        self._title_ = kw.get('title', name.capitalize())

    def set_title(self, title):
        self._title_ = title

    def get_title(self):
        current_ordering = request.GET.get('order_by')
        if current_ordering == self.options['sort_field'] and not request.GET.get('desc'):
            desc = 1
        else:
            desc = 0

        new_params = dict(request.GET)
        if desc:
            new_params['desc'] = 1
        else:
            new_params.pop('desc', None)
        new_params['order_by'] = self.options['sort_field']

        return Markup('<a href="%s">%s</a>' % (escape(url(request.path_url, params=new_params)),
                                               escape(self._title_)))

    title = property(get_title, set_title)

    def get_field(self, row, displays_on=None):
        res = super(SortableColumn, self).get_field(row, displays_on)
        if self.options['xml']:
            res = Markup(res)
        return res

class SortableTableBase(TableBase):
    def _do_get_widget_args(self):
        args = super(SortableTableBase, self)._do_get_widget_args()

        entity_fields = self.__provider__.get_fields(self.__entity__)
        adapted_fields = []
        for field in args['fields']:
            if isinstance(field, Column):
                options = {'sort_field':field.name, 'xml':field.name in args['xml_fields']}
                options.update(field.options)
                field_info = {'name':field.name, 'getter':field.getter, 'title':field.title, 'options':options}
            else:
                options = {'sort_field':field[0], 'xml':field[0] in args['xml_fields']}
                field_info = {'name':field[0], 'getter':field[1], 'title':field[0], 'options':options}

            if field_info['name'] in entity_fields:
                field = SortableColumn(field_info['name'],
                                       getter=field_info['getter'],
                                       title=field_info['title'],
                                       options=field_info['options'])

            adapted_fields.append(field)

        args['fields'] = adapted_fields
        return args

class SmartPaginationCollection():
    def __init__(self, data, total):
        self.data = data

        self.total = int(total)

        if PY2:
            # NOTE: This workaround is not needed nor supported in python3
            # Verify that the total count is an int, because __len__ protocol
            # only accepts ints in Python2, when using tgext.admin with psycopg2
            # backend, total is passed as a long.
            if isinstance(self.total, long):
                raise OverflowError("Exceeded length pagination limit")

    def __getitem__(self, item):
        if not isinstance(item, slice):
            raise TypeError('SmartPaginationCollection can only be sliced, not indexed')
        return self.data

    def __len__(self):
        return self.total

    def __iter__(self):
        raise NotImplementedError('SmartPaginationCollection can only be sliced, not iterated')

class RequestLocalTableFiller(TableFiller):
    """Work-around for the fact that sprox stores count of retrieved
       entities inside the table_filler itself leading to a race condition"""

    def __init__(self, *args, **kw):
        super(RequestLocalTableFiller, self).__init__(*args, **kw)
        self._id = id(self)

    def set_request_local_count(self, value):
        if not hasattr(request, '_tgext_crud_reqlocal_tfiller_count'):
            request._tgext_crud_reqlocal_tfiller_count = {}
        request._tgext_crud_reqlocal_tfiller_count.setdefault(self._id, value)

    def get_request_local_count(self):
        return request._tgext_crud_reqlocal_tfiller_count.get(self._id, 0)

    __count__ = property(get_request_local_count, set_request_local_count)

class DisabledPager(object):
    def pager(self, *args, **kw):
        return ''

def map_args_to_pks(remainder, params):
    controller = request.controller_state.controller

    pks = controller.provider.get_primary_fields(controller.model)
    for i, pk in enumerate(pks):
        if pk not in params and i < len(remainder):
            params[pk] = remainder[i]

    return params

def adapt_params_for_pagination(params, pagination_enabled=True):
    params.pop('limit', None)
    params.pop('offset', None)

    if pagination_enabled:
        paginator = request.paginators['value_list']
        page = paginator.paginate_page - 1

        params['offset'] = page*paginator.paginate_items_per_page
        params['limit'] = paginator.paginate_items_per_page

def allow_json_parameters(remainder, params):
    if request.content_type == 'application/json':
        params.update(request.json_body)

def force_response_type(response_type):
    if response_type is not None:
        request._response_type = response_type

def redirect_on_completion(remainder, params, output):
    redirection = output.get('redirect')
    if redirection is not None:
        redirect(**redirection)


def addopts(*args, **kwargs):
    """Specifies options to be added to __form_options__ and __table_options__.

    When options are specified using addopts like::

        __form_options__ = {
            '__omit_fields__': addopts('name', 'surname')
        }

    they get added to the current option value instead of replacing it.

    In case of lists they always extend the list, so it's not possible to
    change the order of the elements.

    In case of dictionaries keys already in the option the value of the option
    will be merged too if it's a dictionary or a list.
    """
    if args and kwargs:
        raise ValueError('You cannot mix position and named arguments in addopts')

    if args:
        return _addoptslist(args)
    elif kwargs:
        return _addoptsdict(kwargs)
    else:
        raise ValueError('not positional or named arguments provided in addopts.')


class _addoptslist(list):
    def extend_option(self, obj, name):
        value = getattr(obj, name, []) + self
        setattr(obj, name, value)


class _addoptsdict(dict):
    def extend_option(self, obj, name):
        value = getattr(obj, name, {}).copy()
        for optname, optval in self.items():
            curval = value.get(optname)
            if isinstance(curval, list):
                curval.extend(optval)
            elif isinstance(curval, dict):
                curval.update(optval)
            else:
                value[optname] = optval

        setattr(obj, name, value)


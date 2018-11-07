"""
"""
from decorator import decorator
from tg.decorators import validate as tgValidate, before_validate
from tg import flash, config, request, response, tmpl_context
from tgext.crud.validators import report_json_error
from tgext.crud.utils import DisabledPager
from tg.decorators import paginate
from tg.util import Bunch
from tg.exceptions import HTTPOk
from tgext.crud._compat import im_func, im_self, string_type, unicode_text
from .utils import map_args_to_pks

try:
    import transaction
except ImportError:
    transaction = None

class registered_validate(tgValidate):
    """
    Use a validator registered within the controller to validate.
    This is especially useful when you have a controller lookup that instantiates
    a controller who's forms are created at execution time.  This
    allows controller methods to validate on forms which are different.
    Otherwise, each method of the controller would have to share the 
    same method of validation.
    
    :Usage:
     
    >>> from tg.controllers import TGController
    >>> class MyController(TGController):
    >>>     
    >>>     def __init__(self, params):
    >>>         self.form = MyForm(params)
    >>>         register_validators(self, 'eval_form', self.form)
    >>>     
    >>>     @expose('myproject.templates.error_handler')
    >>>     def render_form(self):
    >>>         tg.tg_context.form = self.form
    >>>         return
    >>>     
    >>>     @registered_validate(error_controller=render_form)
    >>>     @expose()
    >>>     def eval_form(self):
    >>>         raise Exception
    """
    def __init__(self, error_handler=None, *args,**kw):
        if not isinstance(error_handler, string_type):
            raise ValueError('error_handle must be a string containing method name.')

        self._error_handler = error_handler
        self.needs_controller = True
        self.chain_validation = False
        class Validators(object):
            def validate(self, controller, params, state):
                func_name = im_func(controller).__name__
                validators = im_self(controller).__validators__
                if func_name in validators:
                    v = validators[func_name].validate(params, state)
                    return v
        self.validators = Validators()

    @property
    def error_handler(self):
        try:
            response_type = request.response_type
        except:
            response_type = None

        if response_type == 'application/json':
            return report_json_error
        else:
            # Get method named as the error handler from current controller.
            controller = request.controller_state.controller
            action = getattr(controller, self._error_handler)
            return getattr(action, '__func__', getattr(action, 'im_func', action))

        
def register_validators(controller, name, validators):
    """
    Helper function which sets the validator lookup for the controller.
    """
    if not hasattr(controller, '__validators__'):
        controller.__validators__ = {}
    controller.__validators__[name] = validators

try:
    from sqlalchemy.exc import IntegrityError, DatabaseError, ProgrammingError
    sqla_errors =  (IntegrityError, DatabaseError, ProgrammingError)
except ImportError:
    sqla_errors = ()

def catch_errors(error_types=None, error_handler=None):
    """
    A validator which catches the Exceptions in the error_types.
    When an exception occurs inside the decorated function, the error_handler
    is called, and the message from the exception is flashed to the screen.
    
    :Usage:
    
    >>> from tg.controllers import TGController
    >>> class MyController(TGController):
    >>>     @expose('myproject.templates.error_handler')
    >>>     def error_handler(self):
    >>>         return
    >>>     
    >>>     @catch_errors(Exception, error_handler='error_handler')
    >>>     @expose()
    >>>     def method_with_exception(self):
    >>>         raise Exception
    """
    if not isinstance(error_handler, string_type):
        raise ValueError('error_handle must be a string containing method name.')

    def wrapper(func, self, *args, **kwargs):
        """Decorator Wrapper function"""
        try:
            return func(self, *args, **kwargs)
        except error_types as e:
            try:
                message = unicode_text(e)
            except:
                message = 'Unknown Error'

            if request.response_type == 'application/json':
                response.status_code = 400
                return dict(message=message)

            if isinstance(e, sqla_errors):
                #if the error is a sqlalchemy error suppose we need to rollback the transaction
                #so that the error handler can perform queries.
                if transaction is not None and config.get('tgext.crud.abort_transactions', False):
                    #This is in case we need to support multiple databases or two phase commit.
                    transaction.abort()
                else:
                    self.session.rollback()

            flash(message, status="status_alert")

            # Get the instance that matches the error handler.
            # This is not a great solution, but it's what we've got for now.
            func = getattr(self, error_handler)
            raise HTTPOk(body=self._call(func, params=kwargs, remainder=list(args)))
    return decorator(wrapper)


class optional_paginate(paginate):
    def before_render(self, remainder, params, output):
        paginator = request.paginators[self.name]
        if paginator.paginate_items_per_page < 0:
            if not getattr(tmpl_context, 'paginators', None):
                tmpl_context.paginators = Bunch()
            tmpl_context.paginators[self.name] = DisabledPager()
            return

        super(optional_paginate, self).before_render(remainder, params, output)


class map_primary_keys(before_validate):
    def __init__(self, argsonly=False):
        if argsonly:
            func = self.do_without_params
        else:
            func = self.do_with_params
        super(map_primary_keys, self).__init__(func)

    def do_without_params(self, remainder, params):
        params.update(map_args_to_pks(remainder, {}))

    def do_with_params(self, remainder, params):
        params.update(map_args_to_pks(remainder, params))


@before_validate
def apply_default_filters(remainder, params):
    controller = request.controller_state.controller
    if controller.filters:
        filters = {}
        for key, value in controller.filters.items():
            if callable(value):
                filters[key] = value()
            else:
                filters[key] = value
        params.update(filters)

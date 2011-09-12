"""
"""
from decorator import decorator
from tg.decorators import validate as tgValidate
from tg import flash

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
    >>>         pylons.c.form = self.form
    >>>         return
    >>>     
    >>>     @registered_validate(error_controller=render_form)
    >>>     @expose()
    >>>     def eval_form(self):
    >>>         raise Exception
    """
    def __init__(self, error_handler=None, *args,**kw):
        self.error_handler = error_handler
        self.needs_controller = True
        class Validators(object):
            def validate(self, controller, params, state):
                func_name = controller.im_func.__name__
                validators = controller.im_self.__validators__
                if func_name in validators:
                    v = validators[func_name].validate(params)
                    return v
        self.validators = Validators()
        
def register_validators(controller, name, validators):
    """
    Helper function which sets the validator lookup for the controller.
    """
    if not hasattr(controller, '__validators__'):
        controller.__validators__ = {}
    controller.__validators__[name] = validators

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
    >>>     return
    >>>     
    >>>     @catch_errors(Exception, error_handler=error_handler)
    >>>     @expose()
    >>>     def method_with_exception(self):
    >>>         raise Exception
    """
    def wrapper(func, self, *args, **kwargs):
        """Decorator Wrapper function"""
        try:
            value = func(self, *args, **kwargs)
        except error_types, e:
            message=None
            if hasattr(e,"message"):
                message=e.message
            if isinstance(message,str):
                try:
                    message=message.decode('utf-8')
                except:
                    message=None
            if message:
                flash(message,status="status_alert")
                # have to get the instance that matches the error handler.  This is not a great solution, but it's 
                # what we've got for now.
                if isinstance(error_handler, basestring):
                    name = error_handler
                else:
                    name = error_handler.__name__
                func = getattr(self, name)
                remainder = []
                remainder.extend(args)
                return self._call(func, params=kwargs, remainder=remainder)

        return value
    return decorator(wrapper)


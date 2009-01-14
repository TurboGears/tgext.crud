"""
"""
from decorator import decorator
from tg.decorators import validate as tgValidate
from tg import flash

from sprox.saormprovider import SAORMProvider
engine = 'genshi'
try:
    import chameleon.genshi
    import pylons.config
    if 'chameleon_genshi' in pylons.config['renderers']:
        engine = 'chameleon_genshi'
except ImportError:
    pass

class registered_validate(tgValidate):
    def __init__(self, error_handler=None, *args,**kw):
        self.error_handler = error_handler
        self.needs_controller = True
        class Validators(object):
            def validate(self, controller, params):
                func_name = controller.im_func.__name__
                validators = controller.im_self.__validators__
                if func_name in validators:
                    return validators[func_name].validate(params)
                #return sprocket.view.__widget__.validate(params)
        self.validators = Validators()
        
def register_validators(controller, name, validators):
    if not hasattr(controller, '__validators__'):
        controller.__validators__ = {}
    controller.__validators__[name] = validators

def catch_crud_errors(error_types=None, error_handler=None):
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
                return self._perform_call(None, dict(url=error_handler.__name__+'/'+'/'.join(args), params=kwargs))
        return value
    return decorator(wrapper)

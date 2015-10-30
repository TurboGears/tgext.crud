from tg import expose, response, tmpl_context
from formencode import FancyValidator, Invalid

@expose('json:', content_type='application/json')
def report_json_error(*args, **kw):
    response.status_code = 400
    return tmpl_context.form_errors

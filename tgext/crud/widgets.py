from tw.forms import TextField

try:
    import tw.dojo
    from sprox.dojo.tablebase import DojoTableBase as TableBase
    from sprox.dojo.fillerbase import DojoTableFiller as TableFiller
except ImportError:
    from sprox.tablebase import TableBase
    from sprox.fillerbase import TableFiller

from sprox.fillerbase import RecordFiller
from sprox.formbase import AddRecordForm, EditableForm

class CrudTable(TableBase):
#    __model__ = User
    #__limit_fields__ = ['display_name', 'email_address']
    __omit_fields__ = ['crud_id', '_password', 'password', 'town_id']
    __url__ = '../users.json'
crud_table = UserTable(DBSession)

class CrudTableFiller(TableFiller):
#    __model__ = User
#    __limit_fields__ = ['crud_id', 'display_name', 'email_address']
    __omit_fields__ = ['_password', 'password', 'town_id']
crud_table_filler = UserTableFiller(DBSession)

class CrudEditForm(EditableForm):
#    __model__ = User
    __require_fields__     = ['crud_name', 'email_address']
    __omit_fields__        = ['_password', 'created', 'password']
    __hidden_fields__      = ['crud_id']
    __field_order__        = ['crud_name', 'email_address', 'display_name', 'groups']
    email_address          = TextField
    display_name           = TextField

crud_edit_form = UserEditForm(DBSession)

class CrudNewForm(AddRecordForm):
#    __model__ = User
    __require_fields__     = ['crud_name', 'email_address']
    __omit_fields__        = ['_password', 'created', 'password']
    __hidden_fields__      = ['crud_id']
    __field_order__        = ['crud_name', 'email_address', 'display_name', 'groups']
    email_address          = TextField
    display_name           = TextField
crud_new_form = UserNewForm(DBSession)

class CrudEditFiller(RecordFiller):pass
#    __model__ = User
crud_edit_filler = UserEditFiller(DBSession)

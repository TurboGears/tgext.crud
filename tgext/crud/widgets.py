from tw.forms import TextField

from tgtest.model import DBSession, User, Group, Permission
try:
    import tw.dojo
    from sprox.dojo.tablebase import DojoTableBase as TableBase
    from sprox.dojo.fillerbase import DojoTableFiller as TableFiller
except ImportError:
    from sprox.tablebase import TableBase
    from sprox.fillerbase import TableFiller

from sprox.fillerbase import RecordFiller
from sprox.formbase import AddRecordForm, EditableForm

class UserTable(TableBase):
    __model__ = User
    #__limit_fields__ = ['display_name', 'email_address']
    __omit_fields__ = ['user_id', '_password', 'password', 'town_id']
    __url__ = '../users.json'
user_table = UserTable(DBSession)

class UserTableFiller(TableFiller):
    __model__ = User
#    __limit_fields__ = ['user_id', 'display_name', 'email_address']
    __omit_fields__ = ['_password', 'password', 'town_id']
user_table_filler = UserTableFiller(DBSession)

class UserEditForm(EditableForm):
    __model__ = User
    __require_fields__     = ['user_name', 'email_address']
    __omit_fields__        = ['_password', 'created', 'password']
    __hidden_fields__      = ['user_id']
    __field_order__        = ['user_name', 'email_address', 'display_name', 'groups']
    email_address          = TextField
    display_name           = TextField

user_edit_form = UserEditForm(DBSession)

class UserNewForm(AddRecordForm):
    __model__ = User
    __require_fields__     = ['user_name', 'email_address']
    __omit_fields__        = ['_password', 'created', 'password']
    __hidden_fields__      = ['user_id']
    __field_order__        = ['user_name', 'email_address', 'display_name', 'groups']
    email_address          = TextField
    display_name           = TextField
user_new_form = UserNewForm(DBSession)

class UserEditFiller(RecordFiller):
    __model__ = User
user_edit_filler = UserEditFiller(DBSession)

class GroupTable(TableBase):
    __model__ = Group
#    __limit_fields__ = ['display_name', 'email_address']
    __url__ = '../groups.json'
group_table = GroupTable(DBSession)

class GroupTableFiller(TableFiller):
    __model__ = Group
#    __limit_fields__ = ['user_id', 'display_name', 'email_address']
group_table_filler = GroupTableFiller(DBSession)

class PermissionTable(TableBase):
    __model__ = Permission
   # __limit_fields__ = ['display_name', 'email_address']
    __url__ = '../permissions.json'
permission_table = UserTable(DBSession)

class PermissionTableFiller(TableFiller):
    __model__ = Permission
    __limit_fields__ = ['user_id', 'display_name', 'email_address']
permission_table_filler = UserTableFiller(DBSession)

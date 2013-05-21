from tg import TGApp, AppConfig

from webtest import TestApp

from sqlalchemy import Column, ForeignKey, Integer, String, Text, Date
from zope.sqlalchemy import ZopeTransactionExtension
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

maker = sessionmaker(autoflush=True, autocommit=False,
                     extension=ZopeTransactionExtension())
DBSession = scoped_session(maker)
DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata


class Movie(DeclarativeBase):
    __tablename__ = "movies"

    movie_id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    release_date = Column(Date, nullable=True)


class FakeModel(object):
    __file__ = 'model.py'

    movie = Movie
    DBSession = DBSession

    def init_model(self, engine):
        if metadata.bind is None:
            DBSession.configure(bind=engine)
            metadata.bind = engine


class FakePackage(object):
    __file__ = 'package.py'
    __name__ = 'tests'

    model = FakeModel()


class CrudTest(object):
    def setUp(self):
        conf = AppConfig(minimal=True, root_controller=self.controller_factory())
        conf.package = FakePackage()
        conf.model = conf.package.model
        conf.use_dotted_templatenames = True
        conf.renderers = ['json', 'jinja']
        conf.default_renderer = 'jinja'
        conf.use_sqlalchemy = True
        conf.paths = {'controllers':'tests',
                      'templates':['tests']}
        conf.disable_request_extensions = False
        conf.prefer_toscawidgets2 = True
        conf.use_transaction_manager = True
        conf['sqlalchemy.url'] = 'sqlite:///:memory:'

        self.app = TestApp(conf.make_wsgi_app())

        metadata.create_all()

    def tearDown(self):
        metadata.drop_all()
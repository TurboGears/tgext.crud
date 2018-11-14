from tg import TGController, expose, tmpl_context
import transaction
from tgext.crud import EasyCrudRestController
from .base import CrudTest, Movie, DBSession, metadata, Actor, Genre


class TestCrudHTML(CrudTest):
    def controller_factory(self):
        class MovieController(EasyCrudRestController):
            model = Movie

            @expose(inherit=True)
            def post(self, *args, **kw):
                resp = super(MovieController, self).post(*args, **kw)
                tmpl_context.obj = resp['obj']
                return resp

        class CrudHTMLController(TGController):
            movies = MovieController(DBSession)

        return CrudHTMLController()

    def test_post(self):
        result = self.app.post('/movies/', params={'title':'Movie Test'}, status=302)

        movie = DBSession.query(Movie).first()
        assert movie is not None

        assert result.headers['Location'] == 'http://localhost/movies/', result

    def test_post_validation(self):
        result = self.app.post('/movies/')

        assert '<form' in result, result
        assert 'Please enter a value' in result, result
        assert DBSession.query(Movie).first() is None

    def test_post_validation_dberror(self):
        metadata.drop_all(tables=[Movie.__table__])

        result = self.app.post('/movies/', params={'title':'Movie Test'})
        assert '<form' in result, result
        assert 'no such table: movies' in result, result
        assert 'status_alert' in result, result

    def test_post_object_accessible(self):
        result = self.app.post('/movies/', params={'title': 'Movie Test'})
        tmpl_c = result.request.environ['paste.testing_variables']['tmpl_context']

        created_object = DBSession.merge(tmpl_c.obj, load=False)
        movie = DBSession.query(Movie).first()
        assert created_object.movie_id == movie.movie_id, created_object

    def test_search(self):
        result = self.app.get('/movies/')
        assert 'id="crud_search_field"' in result, result

    def test_search_disabled(self):
        self.root_controller.movies.search_fields = False
        result = self.app.get('/movies/')
        assert 'id="crud_search_field"' not in result, result

    def test_search_some(self):
        self.root_controller.movies.search_fields = ['title']
        result = self.app.get('/movies/')
        assert 'id="crud_search_field"' in result, result
        assert 'value="title"' in result, result
        assert 'value="genre"' not in result, result


class TestCrudHTMLSearch(CrudTest):
    def controller_factory(self):
        class MovieController(EasyCrudRestController):
            model = Movie

        class CrudHTMLController(TGController):
            movies = MovieController(DBSession)

        return CrudHTMLController()

    def setUp(self):
        super(TestCrudHTMLSearch, self).setUp()
        genre = Genre(name='action')
        DBSession.add(genre)

        actors = [Actor(name='James Who'), Actor(name='John Doe'), Actor(name='Man Alone')]
        list(map(DBSession.add, actors))

        DBSession.add(Movie(title='First Movie', genre=genre, actors=actors[:2]))
        DBSession.add(Movie(title='Second Movie', genre=genre))
        DBSession.add(Movie(title='Third Movie', genre=genre))
        DBSession.add(Movie(title='Fourth Movie', genre=genre))
        DBSession.add(Movie(title='Fifth Movie'))
        DBSession.add(Movie(title='Sixth Movie'))
        DBSession.flush()
        transaction.commit()

    def test_search_no_filters(self):
        result = self.app.get('/movies/')
        assert 'First Movie' in result
        assert 'Second Movie' in result

    def test_search_by_text(self):
        result = self.app.get('/movies/?title=First%20Movie')
        assert 'First Movie' in result
        assert 'Second Movie' not in result

    def test_search_by_substring(self):
        self.root_controller.movies.substring_filters = ['title']
        result = self.app.get('/movies/?title=d%20Movie')
        assert 'First Movie' not in result
        assert 'Second Movie' in result
        assert 'Third Movie' in result
        assert 'Fourth Movie' not in result

    def test_search_relation(self):
        result = self.app.get('/movies/?actors=James%20Who')
        assert 'First Movie' in result, result
        assert 'Second Movie' not in result, result


class TestCrudHTMLSort(CrudTest):
    def controller_factory(self):
        class MovieController(EasyCrudRestController):
            model = Movie

        class CrudHTMLController(TGController):
            movies = MovieController(DBSession)

        return CrudHTMLController()

    def setUp(self):
        super(TestCrudHTMLSort, self).setUp()
        genre = Genre(name='action')
        DBSession.add(genre)

        actors = [Actor(name='James Who'), Actor(name='John Doe'), Actor(name='Man Alone')]
        list(map(DBSession.add, actors))

        DBSession.add(Movie(title='First Movie', genre=genre, actors=actors[:2]))
        DBSession.add(Movie(title='Second Movie', genre=genre, actors=[actors[2]]))
        DBSession.add(Movie(title='Third Movie', genre=genre))
        DBSession.add(Movie(title='Fourth Movie', genre=genre))
        DBSession.add(Movie(title='Fifth Movie'))
        DBSession.add(Movie(title='Sixth Movie', actors=[actors[0]]))
        DBSession.flush()
        transaction.commit()

    def test_sort_by_text(self):
        result = self.app.get('/movies/?order_by=title')
        movies = [
            line.strip() for line in result.text.split('\n') if 'Movie' in line
        ][2:]
        assert movies == ['Fifth Movie', 'First Movie', 'Fourth Movie',
                          'Second Movie', 'Sixth Movie', 'Third Movie'], movies

    def test_sort_by_relation(self):
        result = self.app.get('/movies/?order_by=actors&desc=1')
        movies = [
            line.strip() for line in result.text.split('\n') if 'Movie' in line
        ][2:]
        assert movies == ['Second Movie', 'First Movie', 'Sixth Movie',
                          'Third Movie', 'Fourth Movie', 'Fifth Movie'], movies

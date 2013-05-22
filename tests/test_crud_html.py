from tg import TGController
from tgext.crud import EasyCrudRestController
from .base import CrudTest, Movie, DBSession, metadata, Actor


class TestCrudHTML(CrudTest):
    def controller_factory(self):
        class MovieController(EasyCrudRestController):
            model = Movie

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

        assert '<form action=' in result
        assert 'Please enter a value' in result
        assert DBSession.query(Movie).first() is None

    def test_post_validation_dberror(self):
        metadata.drop_all(tables=[Movie.__table__])

        result = self.app.post('/movies/', params={'title':'Movie Test'})
        assert '<form action=' in result
        assert '(OperationalError)' in result
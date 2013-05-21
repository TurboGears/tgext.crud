from tg import TGController
from tgext.crud import EasyCrudRestController
from .base import CrudTest, Movie, DBSession, metadata


class TestRestJson(CrudTest):
    def controller_factory(self):
        class MovieController(EasyCrudRestController):
            model = Movie

        class RestJsonController(TGController):
            movies = MovieController(DBSession)

        return RestJsonController()

    def test_post(self):
        result = self.app.post('/movies.json', params={'title':'Movie Test'})

        movie = DBSession.query(Movie).first()
        assert movie is not None, result

        assert movie.movie_id == result.json['movie_id']

    def test_post_validation(self):
        result = self.app.post('/movies.json', status=400)
        assert result.json['title'] is not None #there is an error for required title
        assert result.json['description'] is None #there isn't any error for optional description

        assert DBSession.query(Movie).first() is None

    def test_post_validation_dberror(self):
        metadata.drop_all()

        result = self.app.post('/movies.json', params={'title':'Movie Test'}, status=400)
        assert result.json['message'].startswith('(OperationalError)')
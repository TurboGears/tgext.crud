#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tg import TGController, expose, tmpl_context
import transaction
from tgext.crud import EasyCrudRestController
from .base import CrudTest, Movie, DBSession, metadata, Actor, Genre


class TestFilteredCrud(CrudTest):
    def controller_factory(self):
        class MovieController(EasyCrudRestController):
            model = Movie
            filters = {
                'genre': lambda: DBSession.query(Genre).filter_by(name='action').first()
            }

        class CrudHTMLController(TGController):
            movies = MovieController(DBSession)

        return CrudHTMLController()

    def setUp(self):
        super(TestFilteredCrud, self).setUp()

        genre1 = Genre(name='action')
        DBSession.add(genre1)
        DBSession.add(Movie(title='Action Blockbuster', genre=genre1))

        genre2 = Genre(name='comedy')
        DBSession.add(genre2)
        DBSession.add(Movie(title='Comedy Blockbuster', genre=genre2))
        DBSession.add(Movie(title='Blockbuster Test', genre=genre2))
        DBSession.flush()
        transaction.commit()

    def test_filtered_table(self):
        result = self.app.get('/movies/')
        result = result.text
        assert result.find('Action Blockbuster') != -1, result
        assert result.count('Blockbuster') == 1, result

    def test_post(self):
        action_genre = DBSession.query(Genre).filter_by(name='action').first()

        result = self.app.post('/movies.json',
                               params={'title': 'Blockbuster Test'})
        result = result.json
        assert result['value']['genre_id'] == action_genre.genre_id, result

    def test_post_html(self):
        self.app.post('/movies/', params={'title': 'Blockbuster Test'}, status=302)
        result = self.app.get('/movies/')
        result = result.text
        assert result.count('Blockbuster') == 2, result
        assert result.find('Action Blockbuster') != -1, result
        assert result.find('Blockbuster Test') != -1, result

    def test_search(self):
        self.app.post('/movies.json', params={'title': 'Blockbuster Test'})
        result = self.app.get('/movies/?title=Blockbuster%20Test')
        result = result.text.split('<tbody')[-1]
        assert result.count('Blockbuster') == 1, result

    def test_put(self):
        movie = DBSession.query(Movie).filter_by(title='Action Blockbuster').first()
        result = self.app.put('/movies.json',
                               params={'movie_id': movie.movie_id,
                                       'title': 'RENAMED'})
        assert result.json['value']['title'] == 'RENAMED', result

    def test_put_restriction(self):
        movie = DBSession.query(Movie).filter_by(title='Comedy Blockbuster').first()

        result = self.app.put('/movies.json',
                               params={'movie_id': movie.movie_id,
                                       'title': 'RENAMED'}, status=404)

        result = self.app.put('/movies',
                               params={'movie_id': movie.movie_id,
                                       'title': 'RENAMED'}, status=404)

    def test_get(self):
        movie = DBSession.query(Movie).filter_by(title='Comedy Blockbuster').first()
        result = self.app.get('/movies/%s.json' % movie.movie_id, status=404)
        result = self.app.get('/movies/%s' % movie.movie_id, status=404)

        movie = DBSession.query(Movie).filter_by(title='Action Blockbuster').first()
        result = self.app.get('/movies/%s.json' % movie.movie_id)
        assert result.json['value']['title'] == 'Action Blockbuster', result
        result = self.app.get('/movies/%s' % movie.movie_id)
        assert 'Action Blockbuster' in result.text, result

    def test_delete(self):
        movie = DBSession.query(Movie).filter_by(title='Comedy Blockbuster').first()
        result = self.app.delete('/movies/%s.json' % movie.movie_id)
        DBSession.remove()
        movie = DBSession.query(Movie).filter_by(title='Comedy Blockbuster').first()
        assert movie is not None

        movie = DBSession.query(Movie).filter_by(title='Action Blockbuster').first()
        result = self.app.delete('/movies/%s.json' % movie.movie_id)
        DBSession.remove()
        movie = DBSession.query(Movie).filter_by(title='Action Blockbuster').first()
        assert movie is None

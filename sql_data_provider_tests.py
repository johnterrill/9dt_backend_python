import unittest

from app import flask_app
from data_provider import GameDAO
from pickle import dumps, loads
from sql_data_provider import SQLAlchemyDataProvider, Game, db

EXPECTED_GAME_ID = 'EXPECTED_GAME_MODEL_ID'
EXPECTED_PLAYER_1, EXPECTED_PLAYER_2 = 'EXPECTED_PLAYER_1', 'EXPECTED_PLAYER_2'
EXPECTED_PLAYERS = [EXPECTED_PLAYER_1, EXPECTED_PLAYER_2]
EXPECTED_COLUMNS, EXPECTED_ROWS = 4, 4


def get_test_game_model(game_id=EXPECTED_GAME_ID, columns=4, rows=4, state=0, winner=None,
                        initial_players=EXPECTED_PLAYERS, active_players=EXPECTED_PLAYERS):
    return Game(id=game_id, columns=columns, rows=rows, state=state, winner=winner,
                initial_players=dumps(initial_players), active_players=dumps(active_players))


class BaseTest(unittest.TestCase):
    def setUp(self):
        flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/9dt_test'
        flask_app.config['TESTING'] = True
        self.data_provider = SQLAlchemyDataProvider(flask_app)
        self.app = flask_app
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.session.remove()


class GetAllGameIdsTest(BaseTest):
    def test_get_all_game_ids_initial(self):
        # GIVEN the initial empty state (no games created)
        # WHEN get all game ids is called.
        result = self.data_provider.get_all_game_ids()
        # THEN the result is an EMPTY list
        self.assertEquals(result, [])

    def test_get_all_game_ids(self):
        # GIVEN there is an in-progress game
        with self.app.app_context():
            db.session.add(get_test_game_model())
            db.session.commit()
        # WHEN get all game ids is called.
        result = self.data_provider.get_all_game_ids()
        # THEN the result is an EMPTY list
        self.assertEquals(result, [EXPECTED_GAME_ID])

    def test_create_game(self):
        # WHEN create game is called
        self.data_provider.create_game(EXPECTED_GAME_ID, EXPECTED_COLUMNS, EXPECTED_ROWS, EXPECTED_PLAYERS)
        # THEN the data is saved
        with self.app.app_context():
            game = Game.query.filter_by(id=EXPECTED_GAME_ID).first()
            self.assertEquals(game.columns, EXPECTED_COLUMNS)
            self.assertEquals(game.rows, EXPECTED_ROWS)
            self.assertEquals(loads(game.initial_players), EXPECTED_PLAYERS)
            self.assertEquals(loads(game.active_players), EXPECTED_PLAYERS)
            self.assertEquals(game.current_active_player_index, 0)
            self.assertEquals(game.state, GameDAO.GAME_STATE_IN_PROGRESS)
            self.assertEquals(game.winner, None)
            self.assertEquals(game.moves, [])


class GetGameByIdTest(BaseTest):
    def test_get_game_by_id_initial(self):
        # GIVEN the initial empty state (no games created)
        # WHEN get game by id is called.
        result = self.data_provider.get_game_by_id(EXPECTED_GAME_ID)
        # THEN the result is NONE
        self.assertIsNone(result)

    def test_get_game_by_id(self):
        # GIVEN a valid game exists
        with self.app.app_context():
            db.session.add(get_test_game_model())
            db.session.commit()
        # WHEN get game by id is called.
        result = self.data_provider.get_game_by_id(EXPECTED_GAME_ID)
        # THEN the result contains the valid data
        self.assertEquals(result.columns, EXPECTED_COLUMNS)
        self.assertEquals(result.rows, EXPECTED_ROWS)
        self.assertEquals(result.initial_players_list, [])
        self.assertEquals(result.active_players_list, [])
        self.assertEquals(result.current_active_player_index, 0)
        self.assertEquals(result.state, GameDAO.GAME_STATE_IN_PROGRESS)
        self.assertEquals(result.winner, None)
        self.assertEquals(result.moves, [])

    def test_get_game_by_id_game_not_found(self):
        # GIVEN a valid game exists
        with self.app.app_context():
            db.session.add(get_test_game_model())
            db.session.commit()
        # WHEN get game by id is called with a non-existent gameId
        result = self.data_provider.get_game_by_id('foo')
        # THEN the result is NONE
        self.assertIsNone(result)

    def test_get_game_by_id_player(self):
        # GIVEN a valid game exists
        with self.app.app_context():
            db.session.add(get_test_game_model())
            db.session.commit()
        # WHEN get game by id is called with player
        result = self.data_provider.get_game_by_id(EXPECTED_GAME_ID, player_id=EXPECTED_PLAYER_1)
        # THEN the result contains the valid data
        self.assertEquals(result.columns, EXPECTED_COLUMNS)
        self.assertEquals(result.rows, EXPECTED_ROWS)
        self.assertEquals(result.initial_players_list, EXPECTED_PLAYERS)
        self.assertEquals(result.active_players_list, EXPECTED_PLAYERS)
        self.assertEquals(result.current_active_player_index, 0)
        self.assertEquals(result.state, GameDAO.GAME_STATE_IN_PROGRESS)
        self.assertEquals(result.winner, None)
        self.assertEquals(result.moves, [])

    def test_get_game_by_id_serialize_players(self):
        # GIVEN a valid game exists
        with self.app.app_context():
            db.session.add(get_test_game_model())
            db.session.commit()
        # WHEN get game by id is called with serialize_players is TRUE
        result = self.data_provider.get_game_by_id(EXPECTED_GAME_ID, serialize_players=True)
        # THEN the result contains the valid data
        self.assertEquals(result.columns, EXPECTED_COLUMNS)
        self.assertEquals(result.rows, EXPECTED_ROWS)
        self.assertEquals(result.initial_players_list, EXPECTED_PLAYERS)
        self.assertEquals(result.active_players_list, EXPECTED_PLAYERS)
        self.assertEquals(result.current_active_player_index, 0)
        self.assertEquals(result.state, GameDAO.GAME_STATE_IN_PROGRESS)
        self.assertEquals(result.winner, None)
        self.assertEquals(result.moves, [])

    def test_get_game_by_id_player_not_found(self):
        # GIVEN a valid game exists
        with self.app.app_context():
            db.session.add(get_test_game_model())
            db.session.commit()
        # WHEN get game by id is called with a non-existent playerId
        result = self.data_provider.get_game_by_id(EXPECTED_GAME_ID, player_id='foo')
        # THEN the result is NONE
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()

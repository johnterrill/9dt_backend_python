import unittest

from app import flask_app, data_provider
from data_provider import GameDAO
from json import dumps, loads
from mock import MagicMock
from sys import getdefaultencoding

EXPECTED_GAME_ID = 'EXPECTED_GAME_MODEL_ID'
EXPECTED_PLAYER_1, EXPECTED_PLAYER_2 = 'EXPECTED_PLAYER_1', 'EXPECTED_PLAYER_2'
EXPECTED_PLAYERS = [EXPECTED_PLAYER_1, EXPECTED_PLAYER_2]
EXPECTED_COLUMNS, EXPECTED_ROWS = 4, 4


def parse_json_response(response):
    return loads(response.decode(getdefaultencoding()))


class BaseTest(unittest.TestCase):
    def setUp(self):
        flask_app.config['TESTING'] = True
        self.app = flask_app.test_client()


class GameStateTest(BaseTest):
    def test_get_all_games_initial(self):
        # GIVEN the initial empty state (no games created)
        data_provider.get_all_game_ids = MagicMock(return_value=[])
        # WHEN GET all games is called.
        response = self.app.get('/drop_token')
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output is an empty list
        self.assertEquals(parse_json_response(response.get_data()), {'games': []})

    def test_get_all_games(self):
        # GIVEN there is an in-progress game
        data_provider.get_all_game_ids = MagicMock(return_value=[EXPECTED_GAME_ID])
        # WHEN GET all games is called
        response = self.app.get('/drop_token')
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output contains the in-progress game
        self.assertEquals(parse_json_response(response.get_data()), {'games': [EXPECTED_GAME_ID]})

    def test_create_game(self):
        # GIVEN valid input
        expected_players_list = ['player1', 'player2']
        expected_columns, expected_rows = 4, 4
        request_data = dumps({'players': expected_players_list, 'columns': expected_columns, 'rows': expected_rows})
        data_provider.create_game = MagicMock()
        # WHEN POST new game is called
        response = self.app.post('/drop_token', data=request_data, content_type='application/json')
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output contains a gameId
        output = parse_json_response(response.get_data())
        self.assertTrue(output['gameId'] is not None)
        # THEN the game is created
        data_provider.create_game.assert_called_once()

    def test_create_game_missing_players(self):
        # GIVEN input missing players
        expected_columns, expected_rows = 4, 4
        request_data = dumps({'columns': expected_columns, 'rows': expected_rows})
        data_provider.create_game = MagicMock()
        # WHEN POST new game is called
        response = self.app.post('/drop_token', data=request_data, content_type='application/json')
        # THEN the response code is 400
        self.assertEquals(response.status_code, 400)
        # THEN the game is NOT created
        data_provider.create_game.assert_not_called()

    def test_create_game_missing_columns(self):
        # GIVEN input missing columns
        expected_players_list = ['player1', 'player2']
        expected_rows = 4
        request_data = dumps({'players': expected_players_list, 'rows': expected_rows})
        data_provider.create_game = MagicMock()
        # WHEN POST new game is called
        response = self.app.post('/drop_token', data=request_data, content_type='application/json')
        # THEN the response code is 400
        self.assertEquals(response.status_code, 400)
        # THEN the game is NOT created
        data_provider.create_game.assert_not_called()

    def test_create_game_missing_rows(self):
        # GIVEN input missing rows
        expected_players_list = ['player1', 'player2']
        expected_columns = 4
        request_data = dumps({'players': expected_players_list, 'columns': expected_columns})
        data_provider.create_game = MagicMock()
        # WHEN POST new game is called
        response = self.app.post('/drop_token', data=request_data, content_type='application/json')
        # THEN the response code is 400
        self.assertEquals(response.status_code, 400)
        # THEN the game is NOT created
        data_provider.create_game.assert_not_called()


class GameStateByIdTest(BaseTest):
    def test_get_game_state_in_progress(self):
        # GIVEN a valid in-progress game exists
        data_provider.get_game_by_id = MagicMock(return_value=GameDAO(EXPECTED_GAME_ID, EXPECTED_COLUMNS, EXPECTED_ROWS,
                                                                      state=GameDAO.GAME_STATE_IN_PROGRESS,
                                                                      active_players_list=EXPECTED_PLAYERS,
                                                                      initial_players_list=EXPECTED_PLAYERS))
        # WHEN GET game state is called
        response = self.app.get('/drop_token/{}'.format(EXPECTED_GAME_ID))
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output contains the state of the game
        self.assertEquals(parse_json_response(response.get_data()), {'players': EXPECTED_PLAYERS,
                                                                     'state': 'IN_PROGRESS'})

    def test_get_game_state_done_winner(self):
        # GIVEN a valid done game exists
        data_provider.get_game_by_id = MagicMock(return_value=GameDAO(EXPECTED_GAME_ID, EXPECTED_COLUMNS, EXPECTED_ROWS,
                                                                      state=GameDAO.GAME_STATE_DONE,
                                                                      active_players_list=EXPECTED_PLAYERS,
                                                                      initial_players_list=EXPECTED_PLAYERS,
                                                                      winner=EXPECTED_PLAYER_1))
        # WHEN GET game state is called
        response = self.app.get('/drop_token/{}'.format(EXPECTED_GAME_ID))
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output contains the state of the game
        self.assertEquals(parse_json_response(response.get_data()), {'players': EXPECTED_PLAYERS,
                                                                     'state': 'DONE',
                                                                     'winner': EXPECTED_PLAYER_1})

    def test_get_game_state_done_draw(self):
        # GIVEN a valid done game exists
        data_provider.get_game_by_id = MagicMock(return_value=GameDAO(EXPECTED_GAME_ID, EXPECTED_COLUMNS, EXPECTED_ROWS,
                                                                      state=GameDAO.GAME_STATE_DONE,
                                                                      active_players_list=EXPECTED_PLAYERS,
                                                                      initial_players_list=EXPECTED_PLAYERS,
                                                                      winner=None))
        # WHEN GET game state is called
        response = self.app.get('/drop_token/{}'.format(EXPECTED_GAME_ID))
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output contains the state of the game
        self.assertEquals(parse_json_response(response.get_data()), {'players': EXPECTED_PLAYERS,
                                                                     'state': 'DONE',
                                                                     'winner': None})

    def test_get_game_state_not_found(self):
        # GIVEN a valid game exists
        data_provider.get_game_by_id = MagicMock(return_value=None)
        # WHEN GET game state is called with a non-existent gameId
        response = self.app.get('/drop_token/{}'.format('foo'))
        # THEN the response code is 404
        self.assertEquals(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()

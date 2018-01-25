import unittest

from app import flask_app, data_provider
from data_provider import GameDAO, MoveDAO
from json import dumps, loads
from mock import MagicMock
from sys import getdefaultencoding

EXPECTED_COLUMNS, EXPECTED_ROWS = 4, 4
EXPECTED_GAME_ID = 'EXPECTED_GAME_MODEL_ID'
EXPECTED_PLAYER_1, EXPECTED_PLAYER_2 = 'EXPECTED_PLAYER_1', 'EXPECTED_PLAYER_2'
EXPECTED_MOVE_VALUES_ACTIVE_GAME = [('player1', MoveDAO.TYPE_MOVE, 0), ('player2', MoveDAO.TYPE_MOVE, 0),
                                    ('player1', MoveDAO.TYPE_QUIT, None)]

EMPTY_BOARD = [['', '', '', ''], ['', '', '', ''], ['', '', '', ''], ['', '', '', '']]


def parse_json_response(response):
    return loads(response.decode(getdefaultencoding()))


class BaseTest(unittest.TestCase):
    def setUp(self):
        flask_app.config['TESTING'] = True
        self.app = flask_app.test_client()
        self.expected_players = [EXPECTED_PLAYER_1, EXPECTED_PLAYER_2]


class GameStateTest(BaseTest):
    def test_get_all_games_initial(self):
        # GIVEN the initial empty state (no games created)
        data_provider.get_all_active_game_ids = MagicMock(return_value=[])
        # WHEN GET all games is called.
        response = self.app.get('/drop_token')
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output is an empty list
        self.assertEquals(parse_json_response(response.get_data()), {'games': []})

    def test_get_all_games(self):
        # GIVEN there is an in-progress game
        data_provider.get_all_active_game_ids = MagicMock(return_value=[EXPECTED_GAME_ID])
        # WHEN GET all games is called
        response = self.app.get('/drop_token')
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output contains the in-progress game
        self.assertEquals(parse_json_response(response.get_data()), {'games': [EXPECTED_GAME_ID]})

    def test_create_game(self):
        # GIVEN valid input
        self.expected_players_list = ['player1', 'player2']
        expected_columns, expected_rows = 4, 4
        request_data = dumps({'players': self.expected_players_list, 'columns': expected_columns, 'rows': expected_rows})
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
        self.expected_players_list = ['player1', 'player2']
        expected_rows = 4
        request_data = dumps({'players': self.expected_players_list, 'rows': expected_rows})
        data_provider.create_game = MagicMock()
        # WHEN POST new game is called
        response = self.app.post('/drop_token', data=request_data, content_type='application/json')
        # THEN the response code is 400
        self.assertEquals(response.status_code, 400)
        # THEN the game is NOT created
        data_provider.create_game.assert_not_called()

    def test_create_game_missing_rows(self):
        # GIVEN input missing rows
        self.expected_players_list = ['player1', 'player2']
        expected_columns = 4
        request_data = dumps({'players': self.expected_players_list, 'columns': expected_columns})
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
                                                                      active_players_list=self.expected_players,
                                                                      initial_players_list=self.expected_players))
        # WHEN GET game state is called
        response = self.app.get('/drop_token/{}'.format(EXPECTED_GAME_ID))
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output contains the state of the game
        self.assertEquals(parse_json_response(response.get_data()), {'players': self.expected_players,
                                                                     'state': 'IN_PROGRESS'})

    def test_get_game_state_done_winner(self):
        # GIVEN a valid done game exists
        data_provider.get_game_by_id = MagicMock(return_value=GameDAO(EXPECTED_GAME_ID, EXPECTED_COLUMNS, EXPECTED_ROWS,
                                                                      state=GameDAO.GAME_STATE_DONE,
                                                                      active_players_list=self.expected_players,
                                                                      initial_players_list=self.expected_players,
                                                                      winner=EXPECTED_PLAYER_1))
        # WHEN GET game state is called
        response = self.app.get('/drop_token/{}'.format(EXPECTED_GAME_ID))
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output contains the state of the game
        self.assertEquals(parse_json_response(response.get_data()), {'players': self.expected_players,
                                                                     'state': 'DONE',
                                                                     'winner': EXPECTED_PLAYER_1})

    def test_get_game_state_done_draw(self):
        # GIVEN a valid done game exists
        data_provider.get_game_by_id = MagicMock(return_value=GameDAO(EXPECTED_GAME_ID, EXPECTED_COLUMNS, EXPECTED_ROWS,
                                                                      state=GameDAO.GAME_STATE_DONE,
                                                                      active_players_list=self.expected_players,
                                                                      initial_players_list=self.expected_players,
                                                                      winner=None))
        # WHEN GET game state is called
        response = self.app.get('/drop_token/{}'.format(EXPECTED_GAME_ID))
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output contains the state of the game
        self.assertEquals(parse_json_response(response.get_data()), {'players': self.expected_players,
                                                                     'state': 'DONE',
                                                                     'winner': None})

    def test_get_game_state_not_found(self):
        # GIVEN a valid game exists
        data_provider.get_game_by_id = MagicMock(return_value=None)
        # WHEN GET game state is called with a non-existent gameId
        response = self.app.get('/drop_token/{}'.format('foo'))
        # THEN the response code is 404
        self.assertEquals(response.status_code, 404)


class MoveListTest(BaseTest):
    def test_get_list_of_moves(self):
        # GIVEN a list of moves
        moves = [MoveDAO(move[0], move_type=move[1], column=move[2]) for move in EXPECTED_MOVE_VALUES_ACTIVE_GAME]
        # GIVEN a game with the moves
        data_provider.get_game_by_id = MagicMock(return_value=GameDAO(EXPECTED_GAME_ID, EXPECTED_COLUMNS, EXPECTED_ROWS,
                                                                      active_players_list=self.expected_players,
                                                                      initial_players_list=self.expected_players,
                                                                      moves=moves))
        # WHEN GET list of moves played is called
        response = self.app.get('/drop_token/{}/moves'.format(EXPECTED_GAME_ID))
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output contains all the moves
        output_moves = parse_json_response(response.get_data())['moves']
        self.assertEquals(len(output_moves), len(EXPECTED_MOVE_VALUES_ACTIVE_GAME))
        # THEN the response output values contain the expected values
        for index, move in enumerate(EXPECTED_MOVE_VALUES_ACTIVE_GAME):
            if move[2] is not None:
                self.assertEquals(output_moves[index]['column'], move[2])
            self.assertEquals(output_moves[index]['player'], move[0])
            self.assertEquals(output_moves[index]['type'], move[1])

    def test_get_list_of_moves_game_not_found(self):
        # GIVEN a game is not found
        data_provider.get_game_by_id = MagicMock(return_value=None)
        # WHEN GET list of moves is called with a non-existent gameId
        response = self.app.get('/drop_token/{}/moves'.format('foo'))
        # THEN the response code is 404
        self.assertEquals(response.status_code, 404)


class PlayerMoveTest(BaseTest):
    def test_post_move(self):
        # GIVEN a valid game exists
        data_provider.get_game_for_player_with_board = MagicMock(return_value=GameDAO(EXPECTED_GAME_ID,
                                                                                      EXPECTED_COLUMNS, EXPECTED_ROWS,
                                                                                      state=GameDAO.GAME_STATE_IN_PROGRESS,
                                                                                      active_players_list=self.expected_players,
                                                                                      initial_players_list=self.expected_players,
                                                                                      board=EMPTY_BOARD))
        # GIVEN a valid input
        request_data = dumps({'column': 0})
        data_provider.persist_new_move_and_game_state = MagicMock(return_value=None)
        # WHEN POST a move is called
        response = self.app.post('/drop_token/{}/{}'.format(EXPECTED_GAME_ID, EXPECTED_PLAYER_1),
                                 data=request_data, content_type='application/json')
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the new move is persisted
        data_provider.persist_new_move_and_game_state.assert_called_once()
        # THEN the response output is correct
        self.assertEquals(parse_json_response(response.get_data()), {'move': '{}/moves/0'.format(EXPECTED_GAME_ID)})

    def test_delete_move_quit(self):
        # GIVEN a valid game exists
        data_provider.get_game_by_id = MagicMock(return_value=GameDAO(EXPECTED_GAME_ID, EXPECTED_COLUMNS, EXPECTED_ROWS,
                                                                      state=GameDAO.GAME_STATE_IN_PROGRESS,
                                                                      active_players_list=self.expected_players,
                                                                      initial_players_list=self.expected_players))
        data_provider.persist_new_move_and_game_state = MagicMock(return_value=None)
        # WHEN DELETE player is called
        response = self.app.delete('/drop_token/{}/{}'.format(EXPECTED_GAME_ID, EXPECTED_PLAYER_1))
        # THEN the new move is persisted
        data_provider.persist_new_move_and_game_state.assert_called_once()
        # THEN the response code is 202
        self.assertEquals(response.status_code, 202)

if __name__ == '__main__':
    unittest.main()

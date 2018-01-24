import pickle
import unittest

from app import app, db, Game, Move
from json import dumps, loads
from sys import getdefaultencoding

EXPECTED_GAME_ID = 'EXPECTED_GAME_MODEL_ID'
EXPECTED_PLAYER_1, EXPECTED_PLAYER_2 = 'EXPECTED_PLAYER_1', 'EXPECTED_PLAYER_2'
EXPECTED_PLAYERS = [EXPECTED_PLAYER_1, EXPECTED_PLAYER_2]
EXPECTED_COLUMNS, EXPECTED_ROWS = 4, 4

EXPECTED_MOVE_VALUES_ACTIVE_GAME = [('player1', 'MOVE', 0), ('player2', 'MOVE', 0), ('player1', 'QUIT', None)]


def get_test_game_model(game_id=EXPECTED_GAME_ID, columns=4, rows=4, state=0, winner=None,
                        initial_players=EXPECTED_PLAYERS, active_players=EXPECTED_PLAYERS):
    return Game(id=game_id, columns=columns, rows=rows, state=state, winner=winner,
                initial_players=pickle.dumps(initial_players), active_players=pickle.dumps(active_players))


def get_test_moves_list(move_values_list, game_id):
    result = []
    for move in move_values_list:
        result.append(Move(player_id=move[0], game_id=game_id, move_type=move[1], column=move[2]))
    return result


def parse_json_response(response):
    return loads(response.decode(getdefaultencoding()))


class BaseTest(unittest.TestCase):
    SQLALCHEMY_DATABASE_URI = "postgresql://localhost/9dt_test"
    TESTING = True

    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/9dt_test'
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        self.app = app.test_client()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()


class GameStateTest(BaseTest):
    def test_get_all_games_initial(self):
        # GIVEN the initial empty state (no games created)
        # WHEN GET all games is called.
        response = self.app.get('/drop_token')
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output is an empty list
        self.assertEquals(parse_json_response(response.get_data()), {'games': []})

    def test_get_all_games(self):
        # GIVEN there is an in-progress game
        db.session.add(get_test_game_model())
        db.session.commit()
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
        # WHEN POST new game is called
        response = self.app.post('/drop_token', data=request_data, content_type='application/json')
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output contains a gameId
        output = parse_json_response(response.get_data())
        self.assertTrue(output['gameId'] is not None)

    def test_create_game_missing_players(self):
        # GIVEN input missing players
        expected_columns, expected_rows = 4, 4
        request_data = dumps({'columns': expected_columns, 'rows': expected_rows})
        # WHEN POST new game is called
        response = self.app.post('/drop_token', data=request_data, content_type='application/json')
        # THEN the response code is 400
        self.assertEquals(response.status_code, 400)

    def test_create_game_missing_columns(self):
        # GIVEN input missing columns
        expected_players_list = ['player1', 'player2']
        expected_rows = 4
        request_data = dumps({'players': expected_players_list, 'rows': expected_rows})
        # WHEN POST new game is called
        response = self.app.post('/drop_token', data=request_data, content_type='application/json')
        # THEN the response code is 400
        self.assertEquals(response.status_code, 400)

    def test_create_game_missing_rows(self):
        # GIVEN input missing rows
        expected_players_list = ['player1', 'player2']
        expected_columns = 4
        request_data = dumps({'players': expected_players_list, 'columns': expected_columns})
        # WHEN POST new game is called
        response = self.app.post('/drop_token', data=request_data, content_type='application/json')
        # THEN the response code is 400
        self.assertEquals(response.status_code, 400)


class GameStateByIdTest(BaseTest):
    def test_get_game_state_in_progress(self):
        # GIVEN a valid in-progress game exists
        db.session.add(get_test_game_model())
        db.session.commit()
        # WHEN GET game state is called
        response = self.app.get('/drop_token/{}'.format(EXPECTED_GAME_ID))
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output contains the state of the game
        self.assertEquals(parse_json_response(response.get_data()), {'players': EXPECTED_PLAYERS,
                                                                     'state': 'IN_PROGRESS'})

    def test_get_game_state_done_winner(self):
        # GIVEN a valid done game exists
        db.session.add(get_test_game_model(state=1, winner=EXPECTED_PLAYER_1))
        db.session.commit()
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
        db.session.add(get_test_game_model(state=1, winner=None))
        db.session.commit()
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
        db.session.add(get_test_game_model())
        db.session.commit()
        # WHEN GET game state is called with a non-existent gameId
        response = self.app.get('/drop_token/{}'.format('foo'))
        # THEN the response code is 404
        self.assertEquals(response.status_code, 404)


class MoveListTest(BaseTest):
    def test_get_list_of_moves(self):
        # GIVEN a valid game exists
        game = get_test_game_model(game_id=EXPECTED_GAME_ID)
        db.session.add(game)
        # GIVEN the game has existing moves
        game.moves = get_test_moves_list(EXPECTED_MOVE_VALUES_ACTIVE_GAME, EXPECTED_GAME_ID)
        db.session.commit()
        # WHEN GET list of moves is called
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
        # GIVEN a valid game exists
        db.session.add(get_test_game_model())
        db.session.commit()
        # WHEN GET list of moves is called with a non-existent gameId
        response = self.app.get('/drop_token/{}/moves'.format('foo'))
        # THEN the response code is 404
        self.assertEquals(response.status_code, 404)


class PlayerMoveTest(BaseTest):
    def test_post_move(self):
        # GIVEN a valid game exists
        game = get_test_game_model()
        db.session.add(game)
        db.session.commit()
        # GIVEN a valid input
        request_data = dumps({'column': 0})
        # WHEN POST a move is called
        response = self.app.post('/drop_token/{}/{}'.format(EXPECTED_GAME_ID, EXPECTED_PLAYER_1),
                                 data=request_data, content_type='application/json')
        # THEN the response code is 200
        self.assertEquals(response.status_code, 200)
        # THEN the response output is correct
        self.assertEquals(parse_json_response(response.get_data()), {'move': '{}/moves/0'.format(EXPECTED_GAME_ID)})

    def test_delete_move_quit(self):
        # GIVEN a valid game exists
        game = get_test_game_model()
        db.session.add(game)
        db.session.commit()
        # WHEN DELETE player is called
        response = self.app.delete('/drop_token/{}/{}'.format(EXPECTED_GAME_ID, EXPECTED_PLAYER_1))
        # THEN the response code is 202
        self.assertEquals(response.status_code, 202)

if __name__ == '__main__':
    unittest.main()

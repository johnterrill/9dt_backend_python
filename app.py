#!flask/bin/python
from data_provider import MoveDAO, GameDAO
from flask import Blueprint, Flask, jsonify, request
from flask_restful import abort, Api, Resource
from sql_data_provider import SQLAlchemyDataProvider
from uuid import uuid4

flask_app = Flask(__name__)
flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/9dt'
flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
data_provider = SQLAlchemyDataProvider(flask_app)
api_blueprint = Blueprint('drop_token_api', __name__)
api = Api(api_blueprint)

MOVE_DIRECTIONS = (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1), (-1, 1), (1, -1), (-1, -1)


###
# API resource methods
###
class GameStateAPI(Resource):
    """ Handles creating a new game and providing all the Game IDs of active games. """
    def get(self):
        """ Return all in-progress games. """
        return jsonify({'games': data_provider.get_all_active_game_ids()})

    def post(self):
        """ Create a new game. """
        players = request.json.get('players')
        if not players or len(players) < 2:
            abort(400, message='players argument missing or invalid.')
        columns = request.json.get('columns')
        if type(columns) is not int or columns <= 0:
            abort(400, message='columns argument missing or invalid.')
        rows = request.json.get('rows')
        if type(rows) is not int or rows <= 0:
            abort(400, message='columns argument missing or invalid.')
        game_id = str(uuid4())
        data_provider.create_game(game_id, columns, rows, players)
        return jsonify({'gameId': game_id})


class GameStateByIdAPI(Resource):
    """ Handles providing the state of a single game. """
    def get(self, game_id):
        """ Get the state of the game. """
        game = get_game_by_id(game_id, active_only=False, serialize_players=True)
        if not game:
            abort(404, message='Game not found')
        output = {'players': game.initial_players_list}
        if game.state is GameDAO.GAME_STATE_IN_PROGRESS:
            output['state'] = 'IN_PROGRESS'
        else:
            output['state'] = 'DONE'
            output['winner'] = game.winner
        return jsonify(output)


class MoveAPI(Resource):
    """ Handles providing the details of a given move. """
    def get(self, game_id, move_number_unicode):
        """ Return a move. """
        move_number = parse_argument_as_number(move_number_unicode)
        game = get_game_by_id(game_id, active_only=False)
        if move_number < 0 or move_number >= len(game.moves):
            abort(404, message='Move not found.')
        return jsonify(get_move_output(game.moves[move_number]))


class MoveListAPI(Resource):
    """ Handles providing a list of moves for a given game. """
    def get(self, game_id):
        """ Get (sub) list of moves played. """
        game = get_game_by_id(game_id, active_only=False)
        move_len = len(game.moves)
        if move_len == 0:
            return jsonify({'moves': []})
        # Set start index
        start_arg = request.args.get('start')
        start_index = parse_argument_as_number(start_arg) if start_arg else 0
        if start_index < 0 or start_index >= move_len:
            abort(400, message='Malformed request.')
        # Set end index
        until_arg = request.args.get('until')
        end_index = parse_argument_as_number(until_arg) if until_arg else move_len
        if end_index > move_len:
            end_index = move_len
        if start_index > end_index:
            abort(400, message='Malformed request.')
        # Create moves list output
        moves_list = []
        for move in game.moves[start_index:end_index]:
            moves_list.append(get_move_output(move))
        return jsonify({'moves': moves_list})


class PlayerMoveAPI(Resource):
    """ Handles the moves made by a player; such as making a move or quiting the game. """
    def post(self, game_id, player_id):
        """ Post a move. """
        move_column = request.json.get('column')
        if type(move_column) is not int:
            abort(400, message='Malformed move input.')
        game = get_game_for_player_with_board(game_id, player_id)
        if game.state is GameDAO.GAME_STATE_DONE:
            abort(409, message='Not the provided players turn.')
        if move_column < 0 or move_column > game.columns:
            abort(400, message='Illegal move.')
        if game.board[move_column][0] != '':
            abort(400, message='Illegal move.')
        move_number = len(game.moves)
        game.current_active_player_index = (game.current_active_player_index + 1) % len(game.active_players_list)
        move_row = game.rows - 1
        while move_row >= 0:
            if game.board[move_column][move_row] == '':
                game.board[move_column][move_row] = player_id
                break
            move_row -= 1
        if is_winning_move(game, player_id, move_column, move_row):
            game.winner = player_id
            game.state = 1
        elif is_game_draw(game):
            game.state = 1
        data_provider.persist_new_move_and_game_state(game, player_id, move_type=MoveDAO.TYPE_MOVE, column=move_column)
        return jsonify({'move': '{}/moves/{}'.format(game_id, move_number)})

    def delete(self, game_id, player_id):
        """ Player quits a game. """
        game = get_game_by_id(game_id, player_id=player_id)
        quitting_player_index = game.active_players_list.index(player_id)
        if quitting_player_index < game.current_active_player_index:
            game.current_active_player_index -= 1
        elif quitting_player_index is len(game.active_players_list) - 1:
            game.current_active_player_index = 0
        game.active_players_list.remove(player_id)
        if len(game.active_players_list) is 1:
            game.state = 1
            game.winner = game.active_players_list[0]
        data_provider.persist_new_move_and_game_state(game, player_id, MoveDAO.TYPE_QUIT)
        return {}, 202


###
# Util methods
###
def get_move_output(move):
    """ Provides the parsing the given move into the desired output. """
    result = {'type': move.move_type,
              'player': move.player_id}
    if move.column is not None:
        result['column'] = move.column
    return result


def get_game_by_id(game_id, player_id=None, active_only=True, serialize_players=False):
    """ Retrieves the game from the data_provider, and validates whether the provided parameter criteria is met. """
    game = data_provider.get_game_by_id(game_id, player_id=player_id, serialize_players=serialize_players)
    if not game:
        abort(404, message='Game not found')
    if game.state is GameDAO.GAME_STATE_DONE and active_only:
        abort(410, message='Game is already in DONE state.')
    return game


def get_game_for_player_with_board(game_id, player_id):
    """ Retrieves the game from the data_provider, and validates whether the provided parameter criteria is met. """
    game = data_provider.get_game_for_player_with_board(game_id, player_id=player_id)
    if game.state is GameDAO.GAME_STATE_DONE:
        abort(409, message='Not the provided players turn.')
    if game.active_players_list[game.current_active_player_index] != player_id:
        abort(409, message='Not the provided players turn.')
    return game


def is_game_draw(game):
    """ Determines whether the game, in its current state, is a draw. """
    total_moves = game.columns * game.rows
    return sum(1 for move in game.moves if move.move_type == 'MOVE') is total_moves


def is_winning_move(game, player_id, move_column, move_row):
    """ Determines if the provided move wins the game. """
    for direction in MOVE_DIRECTIONS:
        visited = 1
        while visited <= 4:
            try:
                player_node = game.board[move_column + (direction[0] * visited)][move_row + (direction[1] * visited)]
                if player_node != player_id:
                    break
            except IndexError:
                break
            visited += 1
        if visited > 4:
            return True
    return False


def parse_argument_as_number(argument):
    """ Parses and validates the provided string argument as an integer. """
    try:
        return int(argument)
    except ValueError:
        abort(400, message='Malformed request')

##
# Setup the Api resource routing
##
api.add_resource(GameStateAPI, '/drop_token')
api.add_resource(GameStateByIdAPI, '/drop_token/<game_id>')
api.add_resource(PlayerMoveAPI, '/drop_token/<game_id>/<player_id>')
api.add_resource(MoveAPI, '/drop_token/<game_id>/moves/<move_number_unicode>')
api.add_resource(MoveListAPI, '/drop_token/<game_id>/moves')
flask_app.register_blueprint(api_blueprint)

if __name__ == '__main__':
    flask_app.run()

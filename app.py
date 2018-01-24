#!flask/bin/python
from datetime import datetime
from flask import Blueprint, Flask, jsonify, request
from flask_restful import abort, Api, Resource
from flask_sqlalchemy import SQLAlchemy
from pickle import dumps, loads
from uuid import uuid4

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/9dt'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
api_blueprint = Blueprint('drop_token_api', __name__)
api = Api(api_blueprint)


###
# DB Models
###
class Game(db.Model):
    id = db.Column(db.String, nullable=False, primary_key=True, unique=True)
    columns = db.Column(db.Integer, nullable=False)
    rows = db.Column(db.Integer, nullable=False)
    initial_players = db.Column(db.String, nullable=False)
    active_players = db.Column(db.String, nullable=False)
    current_active_player_index = db.Column(db.Integer, nullable=False, default=0)
    state = db.Column(db.Integer, nullable=False, default=0)
    winner = db.Column(db.String, nullable=True)
    moves = db.relationship('Move', backref=db.backref('games', lazy=True))


class Move(db.Model):
    id = db.Column(db.Integer, nullable=False, primary_key=True)
    player_id = db.Column(db.String, nullable=False)
    pub_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    game_id = db.Column(db.String, db.ForeignKey('game.id'), nullable=False)
    move_type = db.Column(db.String, nullable=False)
    column = db.Column(db.Integer, nullable=True)


###
# API resource methods
###
class GameStateAPI(Resource):
    def get(self):
        games = Game.query.all()
        return jsonify({'games': [game.id for game in games if game.state is 0]})

    def post(self):
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
        db.session.add(Game(id=game_id, columns=columns, rows=rows,
                            initial_players=dumps(players), active_players=dumps(players)))
        db.session.commit()
        return jsonify({'gameId': game_id})


class GameStateByIdAPI(Resource):
    def get(self, game_id):
        game = get_game_by_id(game_id, active_only=False, serialize_players=True)
        output = {'players': game.initial_players_list}
        if game.state is 0:
            output['state'] = 'IN_PROGRESS'
        else:
            output['state'] = 'DONE'
            output['winner'] = game.winner
        return jsonify(output)


class MoveAPI(Resource):
    def get(self, game_id, move_number_unicode):
        move_number = parse_argument_as_number(move_number_unicode)
        game = get_game_by_id(game_id, active_only=False)
        if move_number < 0 or move_number >= len(game.moves):
            abort(404, message='Move not found.')
        return jsonify(get_move_output(game.moves[move_number]))


class MoveListAPI(Resource):
    def get(self, game_id):
        game = get_game_by_id(game_id, active_only=False)
        move_len = len(game.moves)
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
    REQUEST_DATA_KEY_MOVE_COLUMN = 'column'

    def post(self, game_id, player_id):
        move_column = request.json.get(self.REQUEST_DATA_KEY_MOVE_COLUMN)
        if type(move_column) is not int:
            abort(400, message='Malformed move input.')
        game = get_game_for_player_with_board(game_id, player_id)
        if game.state is 1:
            abort(409, message='Not the provided players turn.')
        if move_column < 0 or move_column > game.columns:
            abort(400, message='Illegal move.')
        if game.board[move_column][0] != '':
            abort(400, message='Illegal move.')
        if game.active_players_list[game.current_active_player_index] != player_id:
            abort(409, message='Not the provided players turn.')
        move_number = len(game.moves)
        game.moves.append(Move(player_id=player_id, move_type='MOVE', column=move_column))
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
        db.session.commit()
        return jsonify({'move': '{}/moves/{}'.format(game_id, move_number)})

    def delete(self, game_id, player_id):
        game = get_game_by_id(game_id, player_id=player_id)
        quitting_player_index = game.active_players_list.index(player_id)
        if quitting_player_index < game.current_active_player_index:
            game.current_active_player_index -= 1
        elif quitting_player_index is len(game.active_players_list) - 1:
            game.current_active_player_index = 0
        game.active_players_list.remove(player_id)
        game.active_players = dumps(game.active_players_list)
        if len(game.active_players_list) is 1:
            game.state = 1
            game.winner = game.active_players_list[0]
        game.moves.append(Move(player_id=player_id, move_type='QUIT'))
        db.session.commit()
        return {}, 202


###
# Util methods
###
def get_move_output(move):
    result = {'type': move.move_type,
              'player': move.player_id}
    if move.column is not None:
        result['column'] = move.column
    return result


def get_game_by_id(game_id, player_id=None, active_only=True, serialize_players=False):
    game = Game.query.filter_by(id=game_id).first()
    if not game:
        abort(404, message='Game not found')
    if game.state is 1 and active_only:
        abort(410, message='Game is already in DONE state.')
    if player_id:
        game.active_players_list = loads(game.active_players)
        game.initial_players_list = loads(game.initial_players)
        if not any(player_id in player for player in game.active_players_list):
            abort(404, message='Player not apart of the provided game.')
    elif serialize_players:
        game.active_players_list = loads(game.active_players)
        game.initial_players_list = loads(game.initial_players)

    return game


def get_game_for_player_with_board(game_id, player_id):
    game = get_game_by_id(game_id, player_id=player_id)
    game.board = [['' for x in range(game.rows)] for y in range(game.columns)]
    move_type_gen = (move for move in game.moves if move.move_type == 'MOVE')
    for move in move_type_gen:
        row_index = game.rows - 1
        while row_index >= 0:
            if game.board[move.column][row_index] is '':
                game.board[move.column][row_index] = move.player_id
                break
            row_index -= 1
    return game


def is_game_draw(game):
    total_moves = game.columns * game.rows
    return sum(1 for move in game.moves if move.move_type == 'MOVE') is total_moves


def is_winning_move(game, player_id, move_column, move_row):
    move_directions = (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1), (-1, 1), (1, -1), (-1, -1)
    for direction in move_directions:
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
app.register_blueprint(api_blueprint)

if __name__ == '__main__':
    app.run()

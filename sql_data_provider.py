from data_provider import DataProviderInterface, GameDAO, MoveDAO
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from interface import implements
from pickle import dumps, loads

db = SQLAlchemy()


###
# DB Models
###
class Game(db.Model):
    """ A SQLAlchemy DB definition of the Game object. """
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
    """ A SQLAlchemy DB definition of the Move object. """
    id = db.Column(db.Integer, nullable=False, primary_key=True)
    player_id = db.Column(db.String, nullable=False)
    pub_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    game_id = db.Column(db.String, db.ForeignKey('game.id'), nullable=False)
    move_type = db.Column(db.String, nullable=False)
    column = db.Column(db.Integer, nullable=True)


class SQLAlchemyDataProvider(implements(DataProviderInterface)):
    """ A SQLAlchemy implementation of the DataProviderInterface. """
    def __init__(self, app):
        self.app = app
        db.init_app(app)

    def get_all_game_ids(self):
        with self.app.app_context():
            games = Game.query.all()
            return [game.id for game in games if game.state is GameDAO.GAME_STATE_IN_PROGRESS]

    def create_game(self, game_id, columns, rows, players):
        with self.app.app_context():
            db.session.add(Game(id=game_id, columns=columns, rows=rows,
                                initial_players=dumps(players), active_players=dumps(players)))
            db.session.commit()

    def get_game_by_id(self, game_id, player_id=None, serialize_players=False):
        with self.app.app_context():
            game = Game.query.filter_by(id=game_id).first()
            if not game:
                return None
            else:
                game_dao = GameDAO(game.id, game.columns, game.rows, state=game.state,
                                   winner=game.winner, moves=game.moves)
            if player_id or serialize_players:
                game_dao.active_players_list = loads(game.active_players)
                game_dao.initial_players_list = loads(game.initial_players)
                if player_id and not any(player_id in player for player in game_dao.active_players_list):
                    return None
            return game_dao

    def get_game_for_player_with_board(self, game_id, player_id):
        with self.app.app_context():
            game = self.get_game_by_id(game_id, player_id=player_id)
            game.board = [['' for x in range(game.rows)] for y in range(game.columns)]
            move_type_gen = (move for move in game.moves if move.move_type == MoveDAO.TYPE_MOVE)
            for move in move_type_gen:
                row_index = game.rows - 1
                while row_index >= 0:
                    if game.board[move.column][row_index] is '':
                        game.board[move.column][row_index] = move.player_id
                        break
                    row_index -= 1
            return game

    def persist_new_move_and_game_state(self, game_dao, player_id, move_type, column=None):
        with self.app.app_context():
            game = Game.query.filter_by(id=game_dao.id).first()
            game.active_players = dumps(game_dao.active_players_list)
            game.current_active_player_index = game_dao.current_active_player_index
            game.winner = game_dao.winner
            game.state = game_dao.state
            game.moves.append(Move(player_id=player_id, move_type=move_type, column=column))
            db.session.commit()

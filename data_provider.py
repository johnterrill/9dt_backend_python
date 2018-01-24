from interface import Interface


class MoveDAO(object):
    TYPE_MOVE = 'MOVE'
    TYPE_QUIT = 'QUIT'

    def __init__(self, player_id, move_type=TYPE_MOVE, column=None):
        self.player_id = player_id
        self.move_type = move_type
        self.column = column


class GameDAO(object):
    GAME_STATE_IN_PROGRESS = 0
    GAME_STATE_DONE = 1

    def __init__(self, id, columns, rows, current_active_player_index=0, active_players_list=[],
                 initial_players_list=[], state=GAME_STATE_IN_PROGRESS, winner=None, moves=[], board=None):
        self.id = id
        self.columns = columns
        self.rows = rows
        self.active_players_list = active_players_list
        self.initial_players_list = initial_players_list
        self.current_active_player_index = current_active_player_index
        self.state = state
        self.winner = winner
        self.moves = [MoveDAO(move.player_id, move.move_type, move.column) for move in moves]
        self.board = None


class DataProviderInterface(Interface):
    def get_all_game_ids(self, active_only=True):
        pass

    def create_game(self, game_id, columns, rows, players):
        pass

    def get_game_by_id(self, game_id, player_id=None, serialize_players=False):
        pass

    def persist_new_move_and_game_state(self, game_dao, player_id, move_type, column=None):
        pass

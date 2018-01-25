from interface import Interface


class MoveDAO(object):
    """ Application level representation of a move performed in a game. """
    TYPE_MOVE = 'MOVE'
    TYPE_QUIT = 'QUIT'

    def __init__(self, player_id, move_type=TYPE_MOVE, column=None):
        self.player_id = player_id
        self.move_type = move_type
        self.column = column


class GameDAO(object):
    """ Application level representation of the game. """
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
    """ Defines the interface for accessing application data. All implementations must return DAO objects. """
    def get_all_active_game_ids(self):
        """
        Provides a list of all in-progress game IDs.

        Returns
        -------
        list
            The IDs of all the games.

        """
        pass

    def create_game(self, game_id, columns, rows, players):
        """
        Persists a new game with the provide parameters.

        Parameters
        ----------
        game_id : str
            The game identifier.
        columns : int
            The number of columns in game's board.
        rows : int
            The number of rows in game's board.
        players : list
            A list of the initial player IDs.
        """
        pass

    def get_game_by_id(self, game_id, player_id=None, serialize_players=False):
        """
        Provides the GameDAO object for the given ID.

        Parameters
        ----------
        game_id : str
            The ID of the game to find.
        player_id : str
            Optional parameter, indicating whether the game's active players should include the provided player ID.
        serialize_players : bool
            Whether or not the game's active and initial list of players should be included in the result.

        Returns
        -------
        GameDAO
            The GameDAO if found with the optional player_id, otherwise None.

        """
        pass

    def persist_new_move_and_game_state(self, game_dao, player_id, move_type, column=None):
        """
        Persists a new move to the provided game, additionally the game metadata will be save as well.

        Parameters
        ----------
        game_dao : GameDAO
            The game, with updated game state, to add the new move to.
        player_id : str
            The ID of the player that performed the new move.
        move_type : str
            The type of move being made, should be either MoveDAO.TYPE_MOVE or MoveDAO.TYPE_QUIT.
        column : int
            Optional parameter for a MoveDAO.TYPE_MOVE move that indicates which column the move was played in.

        """
        pass

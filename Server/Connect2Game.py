import go
import numpy as np
#connectar melhor as regras
class Connect2Game:
    def __init__(self,n):
        self.row_count = n
        self.column_count = n
        self.action_size = n*n+1
        
    def __repr__(self):
        return "Go"
        
    def get_initial_state(self):
        return np.zeros((self.row_count, self.column_count))
    
    def get_next_state(self, state, action, player):
        b = go.GameState(state, play_idx=1)
        b.turn=player
        row = action// self.column_count
        col = action % self.column_count

        if action == self.column_count**2:
            boa= b.pass_turn()
        else:
            boa = b.move(row,col)
        return boa.board
    
    def get_valid_moves(self, state,previous):
        valid_moves = [0] * self.action_size
        valid_moves[-1]=1
        b = go.GameState(state, play_idx=1)
        if previous is not None:
            b.previous_boards[1]=previous
            
        possi=go.check_possible_moves(b)
        for i in possi:
            action = i[0] * self.column_count + i[1]
            valid_moves[action]=1
        return valid_moves
    
    def get_value_and_terminated(self, state, pas):
        b = go.GameState(state, play_idx=1)
        if pas:
            b.pass_count = 2
            self.game_over = True
        _ , terminated =b.get_value_and_terminated(b)
        value = self.winner(state)
        return value, terminated
    
    def winner(self, state):
        scores = self.scores(state)
        value = value_scores(scores)
        return value
    
    def get_opponent(self, player):
        return -player
    
    def get_opponent_value(self, value):
        return -value
    
    def change_perspective(self, state, player):
        return state * player
    
    def get_encoded_state(self, state):
        encoded_state = np.stack(
            (state == -1, state == 0, state == 1)
        ).astype(np.float32)
        
        if len(state.shape) == 3:
            encoded_state = np.swapaxes(encoded_state, 0, 1)
        
        return encoded_state
    
    def scores(self, state):
        b = go.GameState(state, play_idx=1)
        return b.get_scores()
    


def value_scores(scores):
    if scores[1] > scores[-1]:
        return 1
    elif scores[1] < scores[-1]:
        return -1
    else:
        return 0

#criada 
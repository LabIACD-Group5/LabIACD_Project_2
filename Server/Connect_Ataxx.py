import atax
import numpy as np

class Atax():
    def __init__(self,n):
        self.row_count = n
        self.column_count = n
        self.action_size = n*n*24
        self.num_to_pos= { 0 :(-2,-2),1 :(-2,-1),2 :(-2,0),3:(-2,1),4:(-2,2),
                            5:(-1,-2),6:(-1,-1),7:(-1,0),8:(-1,1),9:(-1,2),
                            10:(0,-2),11:(0,-1),12:(0,1),13:(0,2),
                            14:(1,-2),15:(1,-1),16:(1,0),17:(1,1),18:(1,2),
                            19:(2,-2),20:(2,-1),21:(2,0),22:(2,1),23:(2,2)}
        self.pos_to_num= {v: k for k, v in self.num_to_pos.items()}
    def __repr__(self):
        return "Atax"
        
    def get_initial_state(self):
        b=np.zeros((self.row_count, self.column_count))
        b[0][0]=1
        b[0][self.column_count-1]=-1
        b[self.row_count-1][self.column_count-1]=1
        b[self.row_count-1][0]=-1
        return b
    
    def get_next_state(self, state, action, player):
        #para o caso de passar
        if action ==-1:
            return state
        b = atax.State(state,player)
        val = action//24
        xi= val//self.column_count
        yi=val%self.column_count
        pos= self.num_to_pos[action%24]
        #por a ir ao dicionario
        xf = xi+pos[0]
        yf = yi+pos[1]
        ty=1
        if abs(pos[0])==2 or abs(pos[1])==2:
            ty=2
        move= atax.Move(xi,yi,xf,yf,player,ty)
        boa=b.execute_move(move)
        return boa
    
    def get_valid_moves(self, state,player):
        valid_moves = [0] * self.action_size
        b = atax.State(state,player)
        possi=b.available_moves(1)
        for i in possi:
            dicti=(i.xf - i.xi,i.yf-i.yi)
            action = self.pos_to_num[dicti] + (i.xi*self.column_count + i.yi)*24
            #por a ir ao dicionario
            valid_moves[action]=1
        return valid_moves
    
    def get_value_and_terminated(self, state):
        value,terminated = self.winner(state)
        return value, terminated
    
    def winner(self, state):
        b=atax.State(state,1)
        pecas= self.count(state)
        b1=b.available_moves(1).size
        b_1=b.available_moves(-1).size
        if pecas[0] == 0:
            if pecas[1] == pecas[2]:
                return 0,True
            elif pecas[1] < pecas[-1]:
                return -1,True
            else: return 1,True
        elif pecas[1] == 0:
            return -1,True
        elif pecas[-1] == 0:
            return 1,True
        
        b1=b.available_moves(1).size
        b_1=b.available_moves(-1).size
            
        if b1==0:
            if pecas[1] < pecas[-1] + pecas[0]:
                return -1,True
            else: return 1,True
        if b_1==0:
            if pecas[-1] < pecas[1] + pecas[0]:
                return 1,True
            else: return -1,True
        return 0,False
    
    def count(self,state):
        """counts pieces"""
        pecas=[0,0,0]
        for i in range(0, self.row_count):
            for j in range(0, self.column_count):
                if state[i][j] == 0:
                    pecas[0]+=1
                elif state[i][j] == 1:
                    pecas[1] +=1
                else:
                    pecas[-1] +=1
        return pecas
    
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
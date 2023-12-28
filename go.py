import pygame
import numpy as np
import copy as cp
from copy import deepcopy
import time
import sys

KOMI = 5.5   # predefined value to be added to white's score


class GameState:
    def __init__(self,board,turn=1,play_idx=0,pass_count=0,previous_boards={1:None, -1:None},empty_positions=None,parent=None):
        self.n = len(board)             # number of rows and columns
        self.board = board
        self.turn = turn                # who's playing next
        self.play_idx = play_idx        # how many overall plays occurred before this state
        self.pass_count = pass_count    # counts the current streak of 'pass' plays
        self.previous_boards = previous_boards     # saves both boards originated by each player's last move
        self.parent=parent
        if empty_positions is None:
            self.empty_positions = set([(x,y) for x in range(self.n) for y in range(self.n)])
        else:
            self.empty_positions = empty_positions   # set that stores every empty position in the current board; it is used to facilitate the determination of possible moves in each game state
        self.end = 0             # indicates if the game has ended ({0,1})
        
    def move(self,i,j):         # placing a piece on the board
        next_board = deepcopy(self.board)
        next_board[i][j] = self.turn
        next_board, next_empty_positions = check_for_captures(next_board, self.turn, self.empty_positions)
        next_previous_boards = deepcopy(self.previous_boards)
        next_previous_boards[self.turn] = deepcopy(next_board)
        next_empty_positions.remove((i,j))
        next_state = GameState(next_board,-self.turn,self.play_idx+1,0,next_previous_boards,next_empty_positions,parent=self)
        return next_state
        
    def pass_turn(self):        # a player chooses to "pass"
        next_previous_boards = deepcopy(self.previous_boards)
        next_previous_boards[self.turn] = deepcopy(self.board)
        next_state = GameState(self.board,-self.turn,self.play_idx+1,self.pass_count+1,next_previous_boards,self.empty_positions,parent=self)
        return next_state
            
    def get_winner(self):       # returns the player with the highest score and the scores
        scores = self.get_scores()
        if scores[1] == scores[-1]:
            return 0, scores    # draw
        elif scores[1] > scores[-1]:
            return 1, scores    # player 1 (black, 1) wins
        else:
            return 2, scores    # player 2 (white, -1) wins
    
    def get_scores(self):      # scoring: captured territories + player's stones + komi
        scores = {1:0, -1:0}
        if self.play_idx == 0:
            captured_territories = {1:0, -1:0}
        else:
            captured_territories = self.captured_territories_count()
        n_stones = self.get_number_of_stones()
        scores[1] += captured_territories[1] + n_stones[1]
        scores[-1] += captured_territories[-1] + n_stones[-1] + KOMI
        return scores
     
    def get_number_of_stones(self):     # calculates the number of stones each player has on the board
        n_stones = {1:0, -1:0}
        for i in range(self.n):
            for j in range(self.n):
                stone = self.board[i][j]
                if stone == 0:          # if position is empty, the method skips to the next iteration
                    continue
                n_stones[stone] += 1    # increments by one the number of stones for the player who holds this position
        return n_stones
    
    def captured_territories_count(self):   # returns how many captured territories each player has
        ct_count = {1:0, -1:0}
        visited = set()     # saves territories that were counted before being visited by the following loops
        for i in range(self.n):
            for j in range(self.n):
                if (i,j) in visited:
                    continue
                piece = self.board[i][j]
                if piece != 0:      # if it's not an empty territory, the method skips to the next iteration
                    continue
                ct_group, captor = get_captured_territories(i,j,self.board)     # gets the group of captured territories this position belongs to and its captor, if there is one
                if ct_group is None:    # if this position isn't part of a group of captured territories, the method skips to the next iteration
                    continue
                for (x,y) in ct_group:
                    visited.add((x,y))      # adding all of the group's position to visited
                    ct_count[captor] += 1   # incrementing the captor's count by one for each captured territory
        return ct_count
    
    def end_game(self):     # retrieving the winner and the scores and ending the game
        self.end = 1
        self.winner,self.scores = self.get_winner()

    # methods used to run the Monte Carlo Tree Search algorithm
    def create_children(self):   # creating all the possible new states originated from the current game state
        children = []
        for move in check_possible_moves(self):
            i,j=move
            new_state = deepcopy(self)
            new_state.move(i,j)
            children.append(new_state)
        return children
            
    def get_next_state(self,i,j):   # given an action, this method returns the resulting game state
        next_state = deepcopy(self)
        next_state.move(i,j)
        return next_state
            
    def get_value_and_terminated(self,state,i,j):   ################### (not sure if this is correct)
        new_state = self.move(i,j)
        if is_game_finished(new_state):
            return 1, True
        if np.sum(check_possible_moves(new_state))==0:
            return 0, True
        return 0, False
            
# auxiliar methods to implement Go's game logic
def check_for_captures(board, turn, empty_positions:set = set()):   # method that checks for captures, given a board and a turn, and returns the new board
    player_checked = -turn   # the player_checked will have its pieces scanned and evaluated if they're captured or not
    empty_positions = deepcopy(empty_positions)
    n = len(board)
    for i in range(n):
        for j in range(n):
            if board[i][j] != player_checked:
                continue    # only checks for captured pieces of the player who didn't make the last move
            captured_group = flood_fill(i,j,board)
            if captured_group is not None:
                for (x,y) in captured_group:
                    board[x][y] = 0    # updating the board after a capture
                    empty_positions.add((x,y))   # adding the territory of the captured piece as an empty position
    return board, empty_positions   # returning the new board and the new empty positions list

def is_move_valid(state: GameState, i, j):
    return (i, j) in check_possible_moves(state)

    
def check_possible_moves(state: GameState):
    possible_moves = set(state.empty_positions)

    invalid_moves = set()
    for move in possible_moves:
        i, j = move

        if no_suicide(state.board, state.turn, i, j) or superko(state.board, state.turn, state.previous_boards[state.turn], i, j):
            invalid_moves.add(move)

    possible_moves -= invalid_moves
    return possible_moves


def no_suicide(board, turn, i, j):
    new_board = deepcopy(board)
    new_board[i][j] = turn
    # Provide empty_positions to check_for_captures
    new_board, _ = check_for_captures(new_board, turn, empty_positions=set())

    captured_group = flood_fill(i, j, new_board)
    return captured_group is not None


            
def superko(board, turn, previous_board, i, j):
    new_board = deepcopy(board)
    new_board[i][j] = turn
    new_board, _ = check_for_captures(new_board, turn)
    if np.array_equal(new_board, previous_board):
        return True   # if this move would result in the same board configuration as this player's previous move, then it would violate the ko rule and, consequently, the positional superko rule
    return False 



def is_game_finished(state: GameState):
    if state.pass_count == 2:    # game ends if both players consecutively pass
        print("Reason for game ending: 2 passes in a row")
        return True
    if state.play_idx >= (state.n**2)*2:    # game ends if n*n*2 plays have occurred
        print(f"Reason for game ending: the limit of {state.n**2} plays was exceeded")
        return True
    return False


def invalid_position(i,j,n):    # helper method that returns True if (i,j) is an invalid position
    return i < 0 or i >= n or j < 0 or j >= n


def check_for_captures(board, turn, empty_positions:set = set()):   
    player_checked = -turn   
    empty_positions = deepcopy(empty_positions)
    n = len(board)
    for i in range(n):
        for j in range(n):
            if board[i][j] != player_checked:
                continue    # only checks for captured pieces of the player who didn't make the last move
            captured_group = flood_fill(i,j,board)
            if captured_group is not None:
                for (x,y) in captured_group:
                    board[x][y] = 0    # updating the board after a capture
                    empty_positions.add((x,y))   # adding the territory of the captured piece as an empty position
    return board, empty_positions



def flood_fill(i,j,board):     # returns the captured group or None if there isn't one
    has_liberties, group_positions = _flood_fill(i,j,board[i][j],board,group_positions=set(),_visited=set())
    if has_liberties:
        return None
    else:
        return group_positions

# helper method that returns True if this position or an adjacent position to this one has at least one adjacent empty position (liberty),
# otherwise it returns False and also returns all the positions of the captured group to which the position (i,j) belongs
def _flood_fill(i,j,original_piece,board,group_positions,_visited):
    if (i,j) in _visited or invalid_position(i,j,len(board)):
        return False, group_positions    # returns False if this position is out of bounds or was already visited
    _visited.add((i, j))
    position = board[i][j]

    if position == 0:
        return True, group_positions            # this position is a liberty of the initially given position
    elif position == -original_piece:
        return False, group_positions           # this position has an opposing piece to the original position being checked

    neighbors = [(i-1, j), (i+1, j), (i, j-1), (i, j+1)]    # if (i,j) has the same piece as the original position, its neighbors will be checked
    for x,y in neighbors:
        result, group_positions = _flood_fill(x,y,original_piece,board,group_positions,_visited)
        if result:
            return True, group_positions
    group_positions.add((i,j))      # this position has a same color piece as the original position being checked and it has no liberties
    return False, group_positions


# returns the positions of the captured group (i,j) belongs to and which player is the captor. if (i,j) isn't captured, return None
def get_captured_territories(i,j,board):
    ct_group, captor = _get_captured_territories(i,j,board,ct_group=set(),captor=0,visited=set())
    return ct_group, captor

# Let A be a point connected to (through a path of adjacent positions) a black stone. 
# Therefore, A does not belong to White's territory. 
# Furthermore A is connected to B, which is adjacent to a white stone. 
# Therefore, A does not belong to Black's territory either. 
# In conclusion, A is neutral territory.

# An empty point only belongs to somebody's territory, 
#   if all the empty intersections that form a connected group with it are adjacent to stones of that player's territory.

# recursive helper method that implements an algorithm that searches for a captured group of territories
def _get_captured_territories(i,j,board,ct_group,captor,visited):
    if (i,j) in visited or invalid_position(i,j,len(board)):
        return ct_group, captor
    visited.add((i,j))
    if board[i][j] != 0:    # if this position isn't empty, it checks whose player it belongs to
        if captor == 0:
            captor = board[i][j]     # getting the captor of this group, if there isn't one yet
            if captor == 1:
                return ct_group, captor
            elif captor == -1:
                return ct_group, captor
        elif board[i][j]!=captor:   # If there's two different captors to the group's positions, then
            return None,0           # it returns None, because the group has links to both players' pieces, hence there's no group captured by one captor
        if captor == 1:
            return ct_group, captor     # this piece is captured by the same captor as every piece in this group checked so far
        elif captor == -1:
            return ct_group, captor
    ct_group.add((i,j))  # if this position is empty, then it is added to the territory group
    neighbors = [(i-1, j), (i+1, j), (i, j-1), (i, j+1)]   # if (i,j) has the same piece as the original position, its neighbors will be checked
    for x,y in neighbors:
        ct_group,captor = _get_captured_territories(x,y,board,ct_group,captor,visited)
        if ct_group is None:    # if (i,j) has links to pieces of different players
            return None,0       #   then, there's no captured group of territories
    return ct_group, captor     # if there is a captured group, it is returned alongside its captor
    
    

def setScreen():
    width = 800
    height = 800
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Go")
    return screen

def drawBoard(game: GameState, screen):
    screen.fill((173, 216, 230)) 

    # Draw the name "Go" above the board
    font = pygame.font.SysFont(None, 50)
    text = font.render("Go " + str(game.n)+ "x"+ str(game.n), True, (0, 0, 0))
    text_rect = text.get_rect(center=(400, 25))
    screen.blit(text, text_rect)

    pygame.draw.line(screen, (0, 0, 0), (0, 0), (800, 0), 5)
    pygame.draw.line(screen, (0, 0, 0), (0, 0), (0, 800), 5)
    pygame.draw.line(screen, (0, 0, 0), (0, 798), (800, 798), 5)
    pygame.draw.line(screen, (0, 0, 0), (798, 0), (798, 800), 5)

    # Draw lines on the board
    for i in range(0, game.n):
        # Vertical lines
        pygame.draw.line(screen, (0, 0, 0), (800 * i / game.n + (800 / game.n) / 2, (800 / game.n) / 2), (800 * i / game.n + (800 / game.n) / 2, 800 - (800 / game.n) / 2), 5)
        # Horizontal lines
        pygame.draw.line(screen, (0, 0, 0), ((800 / game.n) / 2, 800 * i / game.n + (800 / game.n) / 2), (800 - (800 / game.n) / 2, 800 * i / game.n + (800 / game.n) / 2), 5)


def drawPieces(game: GameState, screen):
    n = game.n
    for i in range(n):
        for j in range(n):
            # draws black pieces
            if game.board[j][i] == 1:
                pygame.draw.circle(screen, (0,0,0), ((800*i/n)+800/(2*n), (800*j/n)+800/(2*n)), 800/(3*n))
            # draws white pieces
            elif game.board[j][i]==-1:
                pygame.draw.circle(screen, (255,255,255), ((800*i/n)+800/(2*n), (800*j/n)+800/(2*n)), 800/(3*n))


def drawResult(game: GameState, screen):
    if game.end == 0:
        return None

    # Cores
    bg_color = (20, 20, 20)
    message_color = (255, 255, 255)
    font_color = (0, 0, 0)

    # Dimensões e bordas arredondadas
    rect_dimensions = (250, 300, 300, 200)
    border_radius = 15

    # Desenhar retângulos
    pygame.draw.rect(screen, bg_color, rect_dimensions, border_radius=border_radius)
    pygame.draw.rect(screen, message_color, (rect_dimensions[0] + 10, rect_dimensions[1] + 10, rect_dimensions[2] - 20, rect_dimensions[3] - 20), border_radius=border_radius)

    # Fontes
    font_title = pygame.font.SysFont(None, 40)
    font_body = pygame.font.SysFont(None, 30)

    color = {1: "Black", 2: "White"}

    # Título
    if game.winner == 0:
        title_text = font_title.render("Draw!", True, font_color)
    else:
        title_text = font_title.render(f"{color[game.winner].capitalize()} Wins!", True, font_color)

    title_rect = title_text.get_rect(center=(400, 400))
    screen.blit(title_text, title_rect)

    # Texto do placar
    score_text = font_body.render(f"Score: Black {game.scores[1]} | White {game.scores[-1]}", True, font_color)
    score_rect = score_text.get_rect(center=(400, 460))
    screen.blit(score_text, score_rect)

    pygame.display.flip()


        
def mousePos(game:GameState):
    click = pygame.mouse.get_pos()   
    i = int(click[0]*game.n/800)
    j = int(click[1]*game.n/800)
    coord=(i,j)
    return coord


def switchPlayer(turn):
    return -turn

"""  
def go_game(game: GameState, screen):  
    turn = 1
    step = 0
    while game.end == 0:
        drawBoard(game, screen)
        drawPieces(game, screen)
        pygame.display.flip()  

        event = pygame.event.poll()
        if event.type == pygame.QUIT:
            game.end == game.get_winner()

        if event.type == pygame.KEYDOWN:  # tecla P = dar pass
            if event.key == pygame.K_p:
                game = game.pass_turn()
            if is_game_finished(game):
                game.end_game()

        if event.type == pygame.MOUSEBUTTONDOWN:
            targetCell = mousePos(game)
            prevBoard = cp.deepcopy(game.board)
            i, j = targetCell[1], targetCell[0]
            if not is_move_valid(game, i, j):  # checks if move is valid
                continue  # if not, it expects another event from the same player
            game = game.move(i, j)
            if not (np.array_equal(prevBoard, game.board)):
                turn = switchPlayer(turn)
            time.sleep(0.1)

            if is_game_finished(game):
                game.end_game()

            step += 1
        # to display the winner
        if game.end != 0:
            drawResult(game, screen)
            pygame.display.flip()  # Add this line to update the screen
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
            time.sleep(4)

        pygame.display.flip()  # Adiciona esta linha para garantir que a tela seja atualizada após cada jogada

        
        
def main(board_size):
    n = board_size
    initial_board = np.zeros((n, n), dtype=int)  # initializing an empty board of size (n x n)
    initial_state = GameState(initial_board)
    pygame.init()
    screen = setScreen()
    drawBoard(initial_state, screen)
    go_game(initial_state, screen)

"""

def go_game(game: GameState):
    turn = 1
    step = 0
    while game.end == 0:
        print_board(game)

        if is_game_finished(game):
            game.end_game()

        if game.end != 0:
            draw_result(game)
            time.sleep(4)
            break

        i, j = get_player_move(game)
        prev_board = cp.deepcopy(game.board)

        if not is_move_valid(game, i, j):  # checks if move is valid
            continue  # if not, it expects another move from the same player

        game = game.move(i, j)

        if not np.array_equal(prev_board, game.board):
            turn = switch_player(turn)
        time.sleep(0.1)

        if is_game_finished(game):
            game.end_game()

        step += 1


def print_board(game: GameState):
    n = game.n
    current_player = "1" if game.turn == 1 else "2"
    print(f"Turn: {game.play_idx} | Player: {current_player}")
    # Print column numbers
    col_numbers = "    " + " ".join(str(i) for i in range(n))
    print(col_numbers)

    # Print a line of separation
    print("   " + "--" * n)

    for i, row in enumerate(game.board):
        # Print row number, row content, and current player
        row_str = f"{i} | {' '.join(map(str, row))}"
        print(row_str)

    print()




def get_player_move(game: GameState):
    while True:
        try:
            move_input = input(f"Move: ")
            i, j = map(int, move_input.split())
            if 0 <= i < game.n and 0 <= j < game.n:
                return i, j
            else:
                print("Invalid move. Please enter valid indices.")
        except ValueError:
            print("Invalid input. Please enter valid integers.")
        except IndexError:
            print("Invalid input format. Please enter row and column indices in the format 'row col: 0 0'.")



def switch_player(turn):
    return -turn


def draw_result(game: GameState):
    if game.winner == 0:
        print("Draw!")
    else:
        print(f"Player {game.winner} wins!")

    print(f"Score: Black {game.scores[1]} | White {game.scores[-1]}")


def main(board_size):
    n = board_size
    initial_board = np.zeros((n, n), dtype=int)  # initializing an empty board of size (n x n)
    initial_state = GameState(initial_board)
    go_game(initial_state)
    

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python go.py <board_size>")
        sys.exit(1)

    try:
        board_size = int(sys.argv[1])
        if board_size not in [7, 9]:
            raise ValueError("Invalid board size. Please choose 7 or 9.")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    main(board_size)

## Para rodar é python go.py 7
############################ 9
## Pressionar P para passar
## Acaba quando os 2 passam 
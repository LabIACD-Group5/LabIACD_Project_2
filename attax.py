import os
import threading
import time
from tkinter import *
from tkinter import messagebox
import numpy as np
import copy as cp

# 0 - empty, 1 - player_1, 2 - player_2 e 8 - black_square

BOARDS = []
for file in os.listdir("."):
    if file.endswith(".txt") and file.startswith("board"):
        BOARDS.append(file)
for board in BOARDS:
    print(str(BOARDS.index(board) + 1) + "-" + board.removesuffix(".txt"))

i = 0
while i < 1 or i > len(BOARDS):
    i = int(input("Escolha um tabuleiro: "))

file = open(BOARDS[i - 1], 'r')
NB = len(file.readlines())  # Board number of rows/columns
size_of_board = 800
size_of_square = size_of_board / NB
symbol_size = (size_of_square * 0.7 - 10) / 2
symbol_thickness = 10
symbol_X_color = '#FF0000'
symbol_O_color = '#0000FF'
Green_color = '#7BC043'
DEPTH = 4
TIME = 0.3


def other_player(player):
    """receives a player and returns the other one"""
    if player == 1:
        return 2
    elif player == 2:
        return 1


def convert_logical_to_grid_position(logical_pos):
    logical_pos = np.array(logical_pos, dtype=int)
    return (size_of_board / NB) * logical_pos + size_of_board / NB / 2


def convert_grid_to_logical_position(grid_pos):
    grid_pos = np.array(grid_pos)
    return np.array(grid_pos // (size_of_board / NB), dtype=int)


def inside(x, y):
    """checks if the given coordinates are inside the board"""
    return 0 <= x <= NB - 1 and 0 <= y <= NB - 1


def game_type():
    """asks the user for the game type"""
    ch = '0'
    while ch < '1' or ch > '4':
        ch = input("Jogo de Attax\nEscolha o modo de jogo: \n1-Hum/Hum 2-Hum/PC 3-PC/Hum 4-PC/PC\n")
    return int(ch)


class Move:
    def __init__(self, xi, yi, xf, yf, player, ty):
        """class that defines the movement with initial and final positions, player and type of movement"""
        self.xi = xi
        self.yi = yi
        self.xf = xf
        self.yf = yf
        self.player = player
        self.ty = ty

    def __eq__(self, move2):
        """checks if two moves are similar"""
        if isinstance(move2, Move):
            return self.player == move2.player and self.xf == move2.xf and self.yf == move2.yf \
                   and self.ty == move2.ty == 1
        return False

    def isIn(self, moves):
        """checks if there are similar moves is in a given moves list"""
        for move in moves:
            if self.__eq__(move):
                return True
        return False

    def movement_type(self):
        """returns the movement type"""
        if self.distance_mov(2):
            return 2
        elif self.distance_mov(1):
            return 1
        else:
            return 0

    def distance_mov(self, dist):
        """returns the absolute distance between the initial position and the final one"""
        return abs(self.xi - self.xf) == dist and abs(self.yi - self.yf) <= dist \
               or abs(self.yi - self.yf) == dist and abs(self.xi - self.xf) <= dist


class State:
    def __init__(self, matrix, player):
        """class that defines the state of the board"""
        self.matrix = np.copy(matrix)
        self.player = player
        self.winner = -1

    def valid_move(self, move):
        """checks if a move is valid"""
        if not (inside(move.xi, move.yi) and inside(move.xf, move.yf)):
            return False
        if self.matrix[move.xi][move.yi] != move.player:
            return False
        if self.matrix[move.xf][move.yf] != 0:
            return False
        if move.ty == 0:
            return False
        return True

    def available_moves(self, player):
        """returns a list of all the possible moves of a certain player"""
        moves = np.array([])
        for i in range(NB):
            for j in range(NB):
                if self.matrix[i][j] == player:
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            if NB > i + dx >= 0 and NB > j + dy >= 0:
                                if self.matrix[i + dx][j + dy] == 0:
                                    move = Move(i, j, i + dx, j + dy, player, 0)
                                    move.ty = move.movement_type()
                                    if not move.isIn(moves):
                                        moves = np.append(moves, move)
        return moves

    def experimental_move(self, move):
        """moves a piece according to the movement type"""
        if move.ty == 1:
            self.matrix[move.xf][move.yf] = move.player
        if move.ty == 2:
            self.matrix[move.xf][move.yf] = move.player
            self.matrix[move.xi][move.yi] = 0

    def multiply(self, move):
        """makes all the surrounding pieces equal to the played one"""
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if inside(move.xf + dx, move.yf + dy):
                    if self.matrix[move.xf + dx][move.yf + dy] == other_player(move.player):
                        self.matrix[move.xf + dx][move.yf + dy] = move.player

    def isEndState(self):
        """checks if a state is an end state"""
        return self.available_moves(1).size == 0 or self.available_moves(2).size == 0

    def ler_fich(self, f):
        """loads a file"""
        self.matrix = np.loadtxt(f, dtype='i', delimiter=' ')

    def evaluation_function(self):
        """returns the difference of pieces of both players"""
        return self.count_pieces(self.player) - self.count_pieces(other_player(self.player))

    def other_eval_funct(self):
        """returns the number of pieces of a given player"""
        return self.count_pieces(self.player)

    def count_pieces(self, player):
        """counts pieces"""
        cp = 0
        for i in range(0, NB):
            for j in range(0, NB):
                if self.matrix[i, j] == player:
                    cp = cp + 1
        return cp

    def execute_move(self, move):
        """makes a move and changes the turn"""
        self.experimental_move(move)
        self.multiply(move)
        self.player = 3 - self.player


class Attax:
    def __init__(self):
        """class that defines the playing board and its pieces"""
        self.window = Tk()
        self.window.title('Attax')
        self.board = State(np.zeros((NB, NB), dtype=int), 1)
        self.board.ler_fich(file.name)
        self.canvas = Canvas(self.window, width=size_of_board, height=size_of_board)
        self.canvas.pack()
        self.init_draw_board()
        self.window.bind('<Button-1>', self.click)  # Input from user in form of clicks
        self.draw_pieces()
        self.game_type = 0
        self.game_ended = False
        self.CL = 2
        self.Move = Move(-1, -1, -1, -1, 1, -1)

    def mainloop(self):
        self.window.mainloop()

    def difficulty(self):
        """asks the user to select a difficulty"""
        if self.game_type == 2 or self.game_type == 3:
            ch = '0'
            while ch < '1' or ch > '2':
                ch = input("Escolha a dificuldade: \n1-Fácil 2-Difícil\n")
                self.cpu(int(ch))
        elif self.game_type == 4:
            ch1 = '0'
            ch2 = '0'
            while ch1 < '1' or ch1 > '2' and ch2 < '1' or ch2 > '2':
                ch1 = input("Escolha a dificuldade do pc 1: \n1-Fácil 2-Difícil\n")
                ch2 = input("Escolha a dificuldade do pc 2: \n1-Fácil 2-Difícil\n")
            self.cpuVScpu(int(ch1), int(ch2))

    # ------------------------------------------------------------------
    # Logical Functions:
    # ------------------------------------------------------------------

    def show_valid(self, logical_pos):
        """shows the valid moves for a select piece"""
        logical_pos = np.array(logical_pos)
        px, py = logical_pos
        for i in range(-2, 3):
            for j in range(-2, 3):
                if NB > px + i >= 0 and NB > py + j >= 0:
                    if self.board.matrix[px + i, py + j] == 0:
                        logical_pos = np.array([px + i, py + j])
                        self.draw_square(logical_pos, Green_color)

    def valid_plays(self, player):
        """returns the number of plays remaining of a given player"""
        nmovs = 0
        for i in range(NB):
            for j in range(NB):
                if self.board.matrix[i, j] == player:
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            if NB > i + dx >= 0 and NB > j + dy >= 0:
                                if self.board.matrix[i + dx, j + dy] == 0:
                                    nmovs += 1
        return nmovs

    def is_winner(self):
        """returns the winner"""
        if self.valid_plays(self.board.player) > 0:
            return -1
        elif self.board.count_pieces(1) > self.board.count_pieces(2):
            return 1
        elif self.board.count_pieces(1) < self.board.count_pieces(2):
            return 2

    def is_tie(self):
        """checks if there is a tie"""
        return self.board.count_pieces(1) == self.board.count_pieces(2) and self.valid_plays(
            other_player(self.board.player)) == 0 and self.valid_plays(self.board.player) == 0

    def is_game_over(self):
        """shows which player won"""
        if self.game_ended:
            return

        elif self.is_tie():
            messagebox.showinfo("O jogo acabou!", "Empate!")
            self.game_ended = True

        elif self.is_winner() != -1:
            player = self.is_winner()
            messagebox.showinfo("O jogo acabou!",
                                "Jogador " + str(player) + " venceu!")
            self.game_ended = True

    def simple_comp_play(self, player):
        """makes a simple play that tries to get as many pieces as it can"""
        best_score = -800
        self.Move = Move(-1, -1, -1, -1, player, -1)
        best_move = self.Move
        for xi in range(0, NB):
            for yi in range(0, NB):
                if self.board.matrix[xi, yi] == player:
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            self.Move.xi = xi
                            self.Move.yi = yi
                            self.Move.xf = xi + dx
                            self.Move.yf = yi + dy
                            self.Move.ty = self.Move.movement_type()
                            if self.board.valid_move(self.Move):
                                copy = np.copy(self.board.matrix)
                                self.board.experimental_move(self.Move)
                                self.board.multiply(self.Move)
                                score = self.board.other_eval_funct()
                                if score >= best_score:
                                    best_score = score
                                    best_move = cp.copy(self.Move)
                                self.board.matrix = np.copy(copy)
        self.Move = cp.copy(best_move)
        self.board.execute_move(self.Move)
        self.draw_pieces()

    def execute_minimax_move(self, depth):
        """makes a play using the minimax algorithm"""
        if self.game_ended: return
        best_move = None
        best_eval = float('-inf')
        for move in self.board.available_moves(self.board.player):
            new_state = cp.deepcopy(self.board)
            new_state.execute_move(move)
            new_state_eval = self.minimax(new_state, depth - 1, float('-inf'), float('+inf'), False)
            if new_state_eval is not None and new_state_eval > best_eval:
                best_move = new_state
                best_eval = new_state_eval
        if best_move is not None:
            self.board = cp.deepcopy(best_move)
            self.is_game_over()
            self.draw_pieces()

    def minimax(self, state, depth, alpha, beta, maximizing):
        """defines the minimax algorithm with alpha-beta pruning"""
        if depth == 0 or state.winner != -1:
            return state.evaluation_function() if state is not None else 0

        if maximizing:
            max_eval = float('-inf')
            for move in state.available_moves(state.player):
                new_state = cp.deepcopy(state)
                new_state.execute_move(move)
                eval = self.minimax(new_state, depth - 1, alpha, beta, False)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for move in state.available_moves(state.player):
                new_state = cp.deepcopy(state)
                new_state.execute_move(move)
                eval = self.minimax(new_state, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            return min_eval

    # ------------------------------------------------------------------
    # Drawing Functions:
    # The modules required to draw required game based object on canvas
    # logical_position = grid value on the board
    # grid_position = actual pixel values of the center of the grid
    # ------------------------------------------------------------------

    def draw_square(self, logical_pos, color):
        """ Draws a square on the canvas at the given logical position """
        logical_pos = np.array(logical_pos)
        grid_pos = convert_logical_to_grid_position(logical_pos)
        self.canvas.create_rectangle(grid_pos[0] - size_of_square / 2, grid_pos[1] - size_of_square / 2,
                                     grid_pos[0] + size_of_square / 2, grid_pos[1] + size_of_square / 2,
                                     fill=color)

    def init_draw_board(self):
        """ Draws the board on the canvas """
        self.canvas.delete("all")
        for i in range(NB - 1):
            self.canvas.create_line((i + 1) * size_of_square, 0, (i + 1) * size_of_square, size_of_board)
        for i in range(NB - 1):
            self.canvas.create_line(0, (i + 1) * size_of_square, size_of_board, (i + 1) * size_of_square)

    def draw_pieces(self):
        """ Draws the pieces on the canvas """
        self.init_draw_board()
        for i in range(NB):
            for j in range(NB):
                if self.board.matrix[i, j] == 1:
                    color = symbol_X_color
                elif self.board.matrix[i, j] == 2:
                    color = symbol_O_color
                elif self.board.matrix[i, j] == 8:
                    color = '#000000'
                    self.draw_square([i, j], color)
                if self.board.matrix[i, j] == 1 or self.board.matrix[i, j] == 2:
                    logical_pos = np.array([i, j])
                    grid_pos = convert_logical_to_grid_position(logical_pos)
                    self.canvas.create_oval(grid_pos[0] - symbol_size, grid_pos[1] - symbol_size,
                                            grid_pos[0] + symbol_size, grid_pos[1] + symbol_size,
                                            fill=color)

    def draw_O(self, logical_pos):
        """ Draws an O (a piece from the player) on the canvas at the given logical position """
        if self.board.player == 1:
            color = symbol_X_color
        else:
            color = symbol_O_color
        logical_pos = np.array(logical_pos)
        grid_pos = convert_logical_to_grid_position(logical_pos)
        self.canvas.create_oval(grid_pos[0] - symbol_size, grid_pos[1] - symbol_size,
                                grid_pos[0] + symbol_size, grid_pos[1] + symbol_size,
                                fill=color)

    # ------------------------------------------------------------------
    # Play Manager Functions:
    # Functions that manage how each move is executed and who does it
    # ------------------------------------------------------------------

    def click(self, event):
        """ Handles the click event on the canvas """
        if self.game_ended: return
        if self.game_type == 4:
            return
        elif self.board.player == 1 and self.game_type == 3:
            return
        elif self.board.player == 2 and self.game_type == 2:
            return
        grid_pos = [event.x, event.y]
        logical_pos = convert_grid_to_logical_position(grid_pos)
        px, py = logical_pos
        if self.CL == 2 and self.board.matrix[px, py] == self.board.player:
            self.CL = 1
            self.Move.player = self.board.player
            self.Move.xi = px
            self.Move.yi = py
            self.show_valid(logical_pos)
        elif self.CL == 1:
            self.Move.xf = px
            self.Move.yf = py
            self.Move.ty = self.Move.movement_type()
            if self.board.valid_move(self.Move):
                self.board.execute_move(self.Move)
                self.draw_pieces()
            else:
                self.draw_pieces()
            self.CL = 2
        self.is_game_over()

    def cpu(self, difficulty):
        """ Handles the CPU's turn """
        while not self.game_ended:
            if difficulty == 1:
                if self.game_type == 2 and self.board.player == 2:
                    self.simple_comp_play(2)
                if self.game_type == 3 and self.board.player == 1:
                    self.simple_comp_play(1)
                if self.game_type == 4:
                    if self.board.player == 1:
                        self.simple_comp_play(1)
                    else:
                        self.simple_comp_play(2)
            else:
                if self.game_type == 2 and self.board.player == 2:
                    self.execute_minimax_move(DEPTH)
                if self.game_type == 3 and self.board.player == 1:
                    self.execute_minimax_move(DEPTH)
                if self.game_type == 4:
                    self.execute_minimax_move(DEPTH)
            time.sleep(TIME)
            self.is_game_over()

    def cpuVScpu(self, cpu1, cpu2):
        """ Handles the CPU vs CPU game """
        while not self.game_ended:
            if cpu1 == 1:
                self.simple_comp_play(1)
            else:
                self.execute_minimax_move(2)
            self.is_game_over()
            if self.game_ended: break
            time.sleep(TIME)
            if cpu2 == 1:
                self.simple_comp_play(2)
            else:
                self.execute_minimax_move(4)
            self.is_game_over()
            time.sleep(TIME)


if __name__ == '__main__':
    game = Attax()
    game.game_type = game_type()
    file.close()
    if not game.game_type == 1:
        x = threading.Thread(target=game.difficulty)
        x.start()
    game.mainloop()
    if not game.game_type == 1:
        x.join()

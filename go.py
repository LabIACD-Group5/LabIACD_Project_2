import pygame
import numpy as np
import copy as cp
from copy import deepcopy
import time
import sys

# Código inspirado em https://github.com/kelbyh2o/GO_Game_Python/tree/master

# Constante para adicionar ao score do 2 jogador
KOMI = 5.5   

# Classe que representa o estado do jogo
class GameState:
    def __init__(self,board,turn=1,play_idx=0,pass_count=0,previous_boards={1:None, -1:None},empty_positions=None,parent=None):
        self.n = len(board) # tamanho do board
        self.board = board # board
        self.turn = turn # vez do jogador
        self.play_idx = play_idx # número de jogadas feitas
        self.pass_count = pass_count # número de pass feitos
        self.previous_boards = previous_boards # dicionário que armazena o board anterior de cada jogador
        self.parent=parent # estado anterior
        if empty_positions is None:
            # armazena as posições vazias do board para ajudar a determinar os movimentos possíveis
            self.empty_positions = set([(x,y) for x in range(self.n) for y in range(self.n) if self.board[x][y]==0])
        else:
            self.empty_positions = empty_positions  
        self.end = 0 # flag que indica se o jogo acabou
        
    # faz uma jogada na posição (i,j)
    def move(self,i,j):
        next_board = deepcopy(self.board)
        next_board[i][j] = self.turn
        next_board, next_empty_positions = check_for_captures(next_board, self.turn, self.empty_positions) # processa as capturas
        next_previous_boards = deepcopy(self.previous_boards) 
        next_previous_boards[self.turn] = deepcopy(next_board)
        next_empty_positions.remove((i,j)) # remove a posição (i,j) da lista de posições vazias
        next_state = GameState(next_board,-self.turn,self.play_idx+1,0,next_previous_boards,next_empty_positions,parent=self) # cria o próximo estado
        return next_state
    
    # função para passar a vez
    def pass_turn(self):
        next_previous_boards = deepcopy(self.previous_boards)
        next_previous_boards[self.turn] = deepcopy(self.board)
        next_state = GameState(self.board,-self.turn,self.play_idx+1,self.pass_count+1,next_previous_boards,self.empty_positions,parent=self)
        return next_state
            
    # retorna o vencedor e os scores
    def get_winner(self):
        scores = self.get_scores()
        if scores[1] == scores[-1]:
            return 0, scores # empate
        elif scores[1] > scores[-1]:
            return 1, scores # peças pretas ganham 
        else:
            return 2, scores # peças brancas ganham 
        
    # função auxiliar para o modelo para retornar o vencedor    
    def get_winner_model(self): 
        scores = self.get_scores()
        if scores[1] == scores[-1]:
            return 0, scores # empate
        elif scores[1] > scores[-1]:
            return 1, scores # peças pretas ganham
        else:
            return -1, scores # peças brancas ganham
    
    # retorna o score de cada jogador
    def get_scores(self):
        scores = {1:0, -1:0}
        if self.play_idx == 0:
            captured_territories = {1:0, -1:0} # se não houve jogadas, não há territórios capturados
        else:
            captured_territories = self.captured_territories_count() # conta os territórios capturados
        n_stones = self.get_number_of_stones() # conta o número de peças de cada jogador
        scores[1] += captured_territories[1] + n_stones[1] # calcula o score do jogador 1
        scores[-1] += captured_territories[-1] + n_stones[-1] + KOMI # calcula o score do jogador -1 adicionando o KOMI
        return scores
    
    # retorna o número de peças de cada jogador no tabuleiro
    def get_number_of_stones(self):
        n_stones = {1:0, -1:0}
        for i in range(self.n):
            for j in range(self.n):
                stone = self.board[i][j]
                if stone == 0: # se a posição estiver vazia, continua
                    continue
                n_stones[stone] += 1 # incrementa o número de peças do jogador
        return n_stones
    
    # retorna o número de territórios capturados por cada jogador
    def captured_territories_count(self):
        # dicionário que armazena o número de territórios capturados por cada jogador
        ct_count = {1: 0, -1: 0}
        # set que armazena as posições já visitadas
        visited = set()

        for i in range(self.n):
            for j in range(self.n):
                if (i, j) in visited:
                    continue
                piece = self.board[i][j]

                if piece != 0:
                    continue
                
                # ct_group armazena as posições do grupo de territórios capturados
                ct_group, captor = get_captured_territories(i, j, self.board)

                if ct_group is None:
                    continue
                
                # adiciona as posições do grupo de territórios capturados ao set de posições visitadas
                for (x, y) in ct_group:
                    visited.add((x, y))
                    if captor in ct_count:
                        ct_count[captor] += 1

        return ct_count


    # retorna o vencedor e os scores e termina o jogo
    def end_game(self):  
        self.end = 1
        self.winner,self.scores = self.get_winner()
        return self.winner,self.scores

            
"""
    Funções auxiliares para o jogo
    
"""          

# verifica se há capturas
def check_for_captures(board, turn, empty_positions:set = set()):
    player_checked = -turn 
    empty_positions = deepcopy(empty_positions)
    n = len(board)
    for i in range(n):
        for j in range(n):
            # apenas verifica as peças do jogador que não fez a última jogada
            if board[i][j] != player_checked:
                continue
            # roda a função de flood fill para verificar se há capturas
            captured_group = flood_fill(i,j,board)
            if captured_group is not None:
                # atualiza o tabuleiro após as capturas
                for (x,y) in captured_group:
                    board[x][y] = 0
                    # adiciona as posições das peças capturadas ao set de posições vazias
                    empty_positions.add((x,y))
    # retorna o tabuleiro e o set de posições vazias
    return board, empty_positions


# verifica se a jogada é válida utilizando a função check_possible_moves
def is_move_valid(state: GameState, i, j):
    return (i, j) in check_possible_moves(state)

# verifica se a jogada é válida tendo em conta as regras do jogo (suicídio e superko)
def check_possible_moves(state: GameState):
    possible_moves = set(state.empty_positions)

    invalid_moves = set()
    for move in possible_moves:
        i, j = move
        # verifica se a jogada é suicida ou se viola a regra do superko
        if no_suicide(state.board, state.turn, i, j) or superko(state.board, state.turn, state.previous_boards[state.turn], i, j):
            invalid_moves.add(move)
            
    # retira os moves inválidos ao possible_moves e retorna os novos possible_moves
    possible_moves -= invalid_moves
    return possible_moves


# regra do suicidio (nao deixa uma peça se suícidar)
def no_suicide(board, turn, i, j):
    new_board = deepcopy(board)
    new_board[i][j] = turn
    # verifica se houve captura
    new_board, _ = check_for_captures(new_board, turn, empty_positions=set())
    # identifica um grupo de peças capturadas em torno da posição
    captured_group = flood_fill(i, j, new_board)
    # true se houver um grupo capturado (suicídio), se nao é false
    return captured_group is not None


# regra ko/superko (nao deixa fazer um move que resulte na mesma configuração do tabuleiro que o movimento anterior do jogador)
def superko(board, turn, previous_board, i, j):
    new_board = deepcopy(board)
    new_board[i][j] = turn
    new_board, _ = check_for_captures(new_board, turn)
    # compara o novo board com o board antigo
    if np.array_equal(new_board, previous_board):
        return True   
    return False 


# verificar se o jogo acabou
def is_game_finished(state: GameState):
    # se os 2 players passarem consecutivamente
    if state.pass_count == 2:
        return True
    # se o número de jogadas for maior extremamente grande
    if state.play_idx >= (state.n**2)*2: 
        return True
    return False


# verifica se a posição (i,j) é válida (dentro do tabuleiro)
def invalid_position(i,j,n):
    return i < 0 or i >= n or j < 0 or j >= n

# funçao que retorna o grupo de peças capturadas
def flood_fill(i,j,board): 
    # utiliza a função auxiliar _flood_fill para retornar o grupo de peças capturadas
    has_liberties, group_positions = _flood_fill(i,j,board[i][j],board,group_positions=set(),_visited=set())
    if has_liberties:
        return None
    else:
        return group_positions


# funçao auxiliar que retorna True se a posição (i,j) ou uma posição adjacente a esta tiver pelo menos uma posição vazia adjacente (liberdade),
# caso contrário, retorna False e também retorna todas as posições do grupo capturado ao qual a posição (i,j) pertence
def _flood_fill(i,j,original_piece,board,group_positions,_visited):
    # verifica se a posição (i,j) já foi visitada ou se é inválida
    if (i,j) in _visited or invalid_position(i,j,len(board)):
        return False, group_positions  
    # adiciona a posição (i,j) ao set de posições visitadas
    _visited.add((i, j))
    position = board[i][j]

    # se a posição (i,j) for vazia, então tem liberdade
    if position == 0:
        return True, group_positions 
    # se a posição (i,j) tiver uma peça de cor diferente da peça original, então não tem liberdade
    elif position == -original_piece:
        return False, group_positions

    # se a posição (i,j) tiver uma peça da mesma cor da peça original, então verifica as posições adjacentes
    neighbors = [(i-1, j), (i+1, j), (i, j-1), (i, j+1)]  
    # para cada posição adjacente, executa a função _flood_fill recursivamente
    for x,y in neighbors:
        result, group_positions = _flood_fill(x,y,original_piece,board,group_positions,_visited)
        if result:
            return True, group_positions
    # esta posição tem a mesma cor da peça original e não tem liberdade
    group_positions.add((i,j))
    return False, group_positions


# função que retorna o grupo de territórios capturados e o jogador que capturou
def get_captured_territories(i,j,board):
    ct_group, captor = _get_captured_territories(i,j,board,ct_group=set(),captor=0,visited=set())
    return ct_group, captor


# função auxiliar que retorna o grupo de territórios capturados e o jogador que capturou
def _get_captured_territories(i,j,board,ct_group,captor,visited):
    # Verifica se a posição (i,j) já foi visitada ou se é inválida
    if (i,j) in visited or invalid_position(i,j,len(board)):
        return ct_group, captor
    # adiciona a posição (i,j) ao set de posições visitadas
    visited.add((i,j)) 
    # se a posição (i,j) não estiver vazia, então verifica a cor da peça
    if board[i][j] != 0:
        if captor == 0:
            # se captor for 0, então captor recebe a cor da peça
            captor = board[i][j] 
            if captor == 1:
                return ct_group, captor
            elif captor == -1:
                return ct_group, captor
        # se a cor da peça for diferente da cor do captor, então não há territórios capturados
        elif board[i][j]!=captor:   
            return None,0  
        # a peça é capturada pelo mesmo jogador que capturou as peças anteriores
        if captor == 1:
            return ct_group, captor 
        # a peça é capturada pelo mesmo jogador que capturou as peças anteriores
        elif captor == -1:
            return ct_group, captor
    # se a posição (i,j) estiver vazia, então é adicionada ao grupo de territórios
    ct_group.add((i,j))
    # se a posição (i,j) estiver vazia, então verifica as posições adjacentes
    neighbors = [(i-1, j), (i+1, j), (i, j-1), (i, j+1)]  
    for x,y in neighbors:
        ct_group,captor = _get_captured_territories(x,y,board,ct_group,captor,visited)
        # se (i,j) tiver links para peças de jogadores diferentes, então não há territórios capturados
        if ct_group is None:
            return None,0   
    # retorna o grupo de territórios capturados e o jogador que capturou    
    return ct_group, captor
    
    

def setScreen():
    """
        Cria a tela do jogo
        
    """
    width = 800
    height = 800
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Go")
    return screen

def drawBoard(game: GameState, screen):
    """
        Desenha o tabuleiro
        
    """
    screen.fill((173, 216, 230)) 


    font = pygame.font.SysFont(None, 50)
    text = font.render("Go " + str(game.n)+ "x"+ str(game.n), True, (0, 0, 0))
    text_rect = text.get_rect(center=(400, 25))
    screen.blit(text, text_rect)

    pygame.draw.line(screen, (0, 0, 0), (0, 0), (800, 0), 5)
    pygame.draw.line(screen, (0, 0, 0), (0, 0), (0, 800), 5)
    pygame.draw.line(screen, (0, 0, 0), (0, 798), (800, 798), 5)
    pygame.draw.line(screen, (0, 0, 0), (798, 0), (798, 800), 5)

    # Desenha as linhas do tabuleiro
    for i in range(0, game.n):
        # Verticais
        pygame.draw.line(screen, (0, 0, 0), (800 * i / game.n + (800 / game.n) / 2, (800 / game.n) / 2), (800 * i / game.n + (800 / game.n) / 2, 800 - (800 / game.n) / 2), 5)
        # Horizontais
        pygame.draw.line(screen, (0, 0, 0), ((800 / game.n) / 2, 800 * i / game.n + (800 / game.n) / 2), (800 - (800 / game.n) / 2, 800 * i / game.n + (800 / game.n) / 2), 5)


def drawPieces(game: GameState, screen):
    """
        Desenha as peças no tabuleiro
        
    """
    n = game.n
    for i in range(n):
        for j in range(n):
            # desenha as peças pretas
            if game.board[j][i] == 1:
                pygame.draw.circle(screen, (0,0,0), ((800*i/n)+800/(2*n), (800*j/n)+800/(2*n)), 800/(3*n))
            # deseja as peças brancas
            elif game.board[j][i]==-1:
                pygame.draw.circle(screen, (255,255,255), ((800*i/n)+800/(2*n), (800*j/n)+800/(2*n)), 800/(3*n))


def drawResult(game: GameState, screen):
    """
        Desenha o resultado do jogo, no final do jogo
        
    """
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
    """
        Retorna a posição do rato no tabuleiro
    
    """
    click = pygame.mouse.get_pos()   
    i = int(click[0]*game.n/800)
    j = int(click[1]*game.n/800)
    coord=(i,j)
    return coord

# função auxiliar para alternar entre os jogadores
def switchPlayer(turn):
    return -turn

# função que inicia o jogo
def go_game(game: GameState, screen):  
    turn = 1
    step = 0
    while game.end == 0:
        # desenha o tabuleiro e as peças
        drawBoard(game, screen)
        drawPieces(game, screen)
        pygame.display.flip()  

        event = pygame.event.poll()
        # se o jogador fechar a janela, o jogo acaba
        if event.type == pygame.QUIT:
            game.end == game.get_winner()
        # se o jogador pressionar a tecla P, então passa a vez
        if event.type == pygame.KEYDOWN: 
            if event.key == pygame.K_p:
                game = game.pass_turn()
            if is_game_finished(game):
                game.end_game()

        # se o jogador clicar no tabuleiro, então faz a jogada
        if event.type == pygame.MOUSEBUTTONDOWN:
            targetCell = mousePos(game)
            prevBoard = cp.deepcopy(game.board)
            i, j = targetCell[1], targetCell[0]
            # verifica se a jogada é válida
            if not is_move_valid(game, i, j): 
                continue  
            game = game.move(i, j)
            if not (np.array_equal(prevBoard, game.board)):
                turn = switchPlayer(turn)
            time.sleep(0.1)

            if is_game_finished(game):
                game.end_game()

            step += 1
        # se o jogo acabar, então desenha o resultado
        if game.end != 0:
            drawResult(game, screen)
            pygame.display.flip()
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
            time.sleep(4)

        pygame.display.flip() 

        
# função principal
def main(board_size):
    n = board_size
    initial_board = np.zeros((n, n), dtype=int)  
    initial_state = GameState(initial_board)
    pygame.init()
    screen = setScreen()
    drawBoard(initial_state, screen)
    go_game(initial_state, screen)


if __name__ == "__main__":
    if len(sys.argv) != 2:
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
## Acaba quando os
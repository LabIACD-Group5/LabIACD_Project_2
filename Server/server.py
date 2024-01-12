import socket
import time
from go import *
import numpy as np 
from Connect_Ataxx import Atax as Atax
import pygame
from atax import *


# Escolha do board para o jogo
Games = ["G7x7", "G9x9", "A4x4", "A5x5", "A6x6"]
number = int(input("Escolha o jogo: \n Go: 1- G7x7  2- G9x9 \n Ataxx: 3- A4x4  4- A5x5  5- A6x6 \n"))
Game = Games[number-1]

# Função para obter o tamanho do board
def n_board(Game):
    n = int(Game[1])
    return n

# Configuração do server
def server_for_go(host='localhost', port=12345):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(2)
    print("------------------------------------")
    print("Waiting for two agents to connect...")
    agent1, addr1 = server_socket.accept()  # Aceita a ligação do agente 1
    print("Agent 1 connected from", addr1)
    bs=b'AG1 '+Game.encode()
    agent1.sendall(bs)  # Envia o jogo para o agente 1

    agent2, addr2 = server_socket.accept()  # Aceita a ligação do agente 2
    print("Agent 2 connected from", addr2)
    bs=b'AG2 '+Game.encode()
    agent2.sendall(bs)  # Envia o jogo para o agente 2
    print("------------------------------------")
    n = n_board(Game)
    initial_board = np.zeros((n, n),dtype=int)  # Tabuleiro inicial
    Go = GameState(initial_board)   # Jogo iniciado

    # Interface gráfica
    pygame.init()
    screen = setScreen()   
    drawBoard(Go, screen)
    pygame.display.update()

    # Lista de agentes
    agents = [agent1, agent2]
    current_agent = 0


    invalid_count = 0   # Contar os moves inválidos para o caso de um agente fazer jogadas erradas umas x vezes
    time.sleep(3)
    while True:
        print("Agent ", current_agent+1, " turn")
        try:
            # Receber a jogada do agente
            yet_invalid = False
            data = None
            data = agents[current_agent].recv(1024).decode() # Recebe a jogada do agente
            
            if not data:
                break

            if data == "PASS":
                
                agents[current_agent].sendall(b'VALID') # Envia a mensagem de validação
                agents[1-current_agent].sendall(data.encode()) # Envia a jogada para o outro agente
                Go = Go.pass_turn() # Executa o pass_turn
                
                if current_agent == 0:
                    print("Agent 1 -> ",data)
                else:
                    print("Agent 2 -> ",data)
            else:
                # Processing the move (example: "MOVE X,Y")
                i = int(data[5])
                j = int(data[7])
                
                if current_agent == 0:
                    print("Agent 1 -> ",data)
                else:
                    print("Agent 2 -> ",data)
                
                # Verificar se a jogada é válida
                if is_move_valid(Go, i,j):
                    agents[current_agent].sendall(b'VALID') # Envia a mensagem de validação
                    agents[1-current_agent].sendall(data.encode()) # Envia a jogada para o outro agente
                    Go = Go.move(i,j) # Executa o move
                    time.sleep(0.1)
                    drawBoard(Go, screen) # Desenha o tabuleiro
                    drawPieces(Go, screen) # Desenha as peças
                    
                else:
                    # Se a jogada for inválida, envia a mensagem de invalida
                    agents[current_agent].sendall(b'INVALID')
                    invalid_count += 1
                    yet_invalid = True
                    if invalid_count >= 3:   # Se o agente fizer 3 jogadas inválidas seguidas, passa
                        agents[current_agent].sendall(b'TURN LOSS')
                        agents[1-current_agent].sendall(b'PASS')
                        Go = Go.pass_turn()
                        invalid_count = 0
                        yet_invalid = False
            pygame.display.update()
                
            # print do tabuleiro no terminal
            print(Go.board)
            
            # Verificar se o jogo acabou
            if is_game_finished(Go):
                # Obter o vencedor e os scores
                winner, scores = Go.end_game()
                if winner == -1:
                    winner = 2
                p1_score = scores[1]
                p2_score = scores[-1]
                
                data = "END " + str(winner) + " " + str(p1_score) + " " + str(p2_score)
                agents[current_agent].sendall(data.encode()) # Envia a mensagem de fim de jogo
                agents[1-current_agent].sendall(data.encode()) # Envia a mensagem de fim de jogo
                
                # Dá print ao resultado
                drawResult(Go, screen) 
                pygame.display.update() 
                time.sleep(4)
                pygame.quit()
                break
            

            # Muda a vez do agente
            if not yet_invalid:
                current_agent = 1-current_agent

        except Exception as e:
            print("Error:", e)
            break
    
    print("\n-----------------\nGAME END\n-----------------\n")
    print(f"Results: Ganhou o {winner}! {p1_score} x {p2_score}\n")
    time.sleep(1)
    
    # Fechar as ligações e o server
    agent1.close()
    agent2.close()
    server_socket.close()

# Configuração do server    
def server_for_atax(host='localhost', port=12345):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(2)
    print("------------------------------------")
    print("Waiting for two agents to connect...")
    agent1, addr1 = server_socket.accept() # Aceita a ligação do agente 1
    print("Agent 1 connected from", addr1)
    bs=b'AG1 '+Game.encode()
    agent1.sendall(bs) # Envia o jogo para o agente 1

    agent2, addr2 = server_socket.accept() # Aceita a ligação do agente 2
    print("Agent 2 connected from", addr2)
    bs=b'AG2 '+Game.encode()
    agent2.sendall(bs) # Envia o jogo para o agente 2
    print("------------------------------------")


    atax = Atax(n_board(Game))    # Jogo iniciado do connect
    initial_board = atax.get_initial_state()
    ata= State(initial_board,1)

    # Lista de agentes
    agents = [agent1, agent2]
    current_agent = 0
    player= 1


    invalid_count = 0   # Contar os moves inválidos para o caso de um agente fazer jogadas erradas umas x vezes
    time.sleep(3)
    while True:
        print("Agent ", current_agent+1, " turn")
        try:
            # Receber a jogada do agente
            yet_invalid = False
            data = None
            data = agents[current_agent].recv(1024).decode() # Recebe a jogada do agente
            
            if not data:
                break
            else:
                # Processing the move (example: "MOVE X,Y")
                i = int(data[5])
                j = int(data[7])
                k= int(data[9])
                l=int(data[11])
                
                if current_agent == 0:
                    print("Agent 1 -> ",data)
                else:
                    print("Agent 2 -> ",data)
                
                # Verificar se a jogada é válida
                move =Move(i,j,k,l,player, 0)
                move.ty= move.movement_type()
                
                if ata.valid_move(move):
                    agents[current_agent].sendall(b'VALID') # Envia a mensagem de validação
                    agents[1-current_agent].sendall(data.encode()) # Envia a jogada para o outro agente
                    ata.matrix =ata.execute_move(move) # Executa o move
                    player=-player
                    time.sleep(0.1)

                else:
                    # Se a jogada for inválida, envia a mensagem de invalida
                    agents[current_agent].sendall(b'INVALID')
                    invalid_count += 1
                    yet_invalid = True
                    if invalid_count >= 3:   # Se o agente fizer 3 jogadas inválidas seguidas, passa
                        agents[current_agent].sendall(b'TURN LOSS')
                        agents[1-current_agent].sendall(b'PASS')
                        invalid_count = 0
                        yet_invalid = False
                
            # Print do tabuleiro no terminal
            print(ata.matrix)
            
            # Verificar se o jogo acabou
            winner, terminated = atax.get_value_and_terminated(ata.matrix)
            if terminated:
                # Obter o vencedor e os scores
                if winner == -1:
                    winner = 2
                if winner == 0:
                    data = "END! DRAW"
                else:
                    data = "END! Player " + str(winner) + " won!"
                agents[current_agent].sendall(data.encode()) # Envia a mensagem de fim de jogo
                agents[1-current_agent].sendall(data.encode()) # Envia a mensagem de fim de jogo

                break
            
            # Muda a vez do agente
            if not yet_invalid:
                current_agent = 1-current_agent

        except Exception as e:
            print("Error:", e)
            break
    
    print("\n-----------------\nGAME END\n-----------------\n")
    print(f"Results: Ganhou o {winner}!")
    time.sleep(1)
    
    # Fechar as ligações e o server
    agent1.close()
    agent2.close()
    server_socket.close()

if __name__ == "__main__":
    if number < 3:
        server_for_go()
    else:
        server_for_atax()
import socket
import time
from go import *   

# Escolha do board para o jogo
Games = ["G7x7", "G9x9"]
number = int(input("Escolha o jogo: 1-7x7 2-9x9: "))
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
    agent1, addr1 = server_socket.accept() # aceita a ligação do agente 1
    print("Agent 1 connected from", addr1)
    bs=b'AG1 '+Game.encode()
    agent1.sendall(bs) # envia o jogo para o agente 1

    agent2, addr2 = server_socket.accept() # aceita a ligação do agente 2
    print("Agent 2 connected from", addr2)
    bs=b'AG2 '+Game.encode()
    agent2.sendall(bs) # envia o jogo para o agente 2
    print("------------------------------------")
    n = n_board(Game)
    initial_board = np.zeros((n, n),dtype=int)# tabuleiro inicial
    Go = GameState(initial_board)    # jogo iniciado
    
    #interface gráfica
    pygame.init()
    screen = setScreen()   
    drawBoard(Go, screen)
    pygame.display.update()

    # lista de agentes
    agents = [agent1, agent2]
    current_agent = 0


    invalid_count = 0   # contar os moves inválidos para o caso de um agente fazer jogadas erradas umas x vezes
    time.sleep(3)
    while True:
        print("Agent ", current_agent+1, " turn")
        try:
            # receber a jogada do agente
            yet_invalid = False
            data = None
            data = agents[current_agent].recv(1024).decode() # recebe a jogada do agente
            
            if not data:
                break

            if data == "PASS":
                
                agents[current_agent].sendall(b'VALID') # envia a mensagem de validação
                agents[1-current_agent].sendall(data.encode()) # envia a jogada para o outro agente
                Go = Go.pass_turn() # executa o pass_turn
                
                if current_agent == 0:
                    print("Agent 1 -> ",data)
                else:
                    print("Agent 2 -> ",data)
            else:
                # processing the move (example: "MOVE X,Y")
                i = int(data[5])
                j = int(data[7])
                
                if current_agent == 0:
                    print("Agent 1 -> ",data)
                else:
                    print("Agent 2 -> ",data)
                
                # verificar se a jogada é válida
                if is_move_valid(Go, i,j):
                    agents[current_agent].sendall(b'VALID') # envia a mensagem de validação
                    agents[1-current_agent].sendall(data.encode()) # envia a jogada para o outro agente
                    Go = Go.move(i,j) # executa o move
                    time.sleep(0.1)
                    drawBoard(Go, screen) # desenha o tabuleiro
                    drawPieces(Go, screen) # desenha as peças
                    
                else:
                    # se a jogada for inválida, envia a mensagem de invalida
                    agents[current_agent].sendall(b'INVALID')
                    invalid_count += 1
                    yet_invalid = True
                    if invalid_count >= 3:   # se o agente fizer 3 jogadas inválidas seguidas, passa
                        agents[current_agent].sendall(b'TURN LOSS')
                        agents[1-current_agent].sendall(b'PASS')
                        Go = Go.pass_turn()
                        invalid_count = 0
                        yet_invalid = False
            pygame.display.update()
                
            # print do tabuleiro no terminal
            print(Go.board)
            
            # verificar se o jogo acabou
            if is_game_finished(Go):
                # obter o vencedor e os scores
                winner, scores = Go.end_game()
                if winner == -1:
                    winner = 2
                p1_score = scores[1]
                p2_score = scores[-1]
                
                data = "END " + str(winner) + " " + str(p1_score) + " " + str(p2_score)
                agents[current_agent].sendall(data.encode()) # envia a mensagem de fim de jogo
                agents[1-current_agent].sendall(data.encode()) # envia a mensagem de fim de jogo
                
                # dá print ao resultado
                drawResult(Go, screen) 
                pygame.display.update() 
                time.sleep(4)
                pygame.quit()
                break
            

            # muda a vez do agente
            if not yet_invalid:
                current_agent = 1-current_agent

        except Exception as e:
            print("Error:", e)
            break
    
    print("\n-----------------\nGAME END\n-----------------\n")
    print(f"Results: Ganhou o {winner}! {p1_score} x {p2_score}\n")
    time.sleep(1)
    
    # fechar as ligações e o server
    agent1.close()
    agent2.close()
    server_socket.close()
    
    
if __name__ == "__main__":
    server_for_go()

    




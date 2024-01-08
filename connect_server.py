import socket
import time
from go import *   

#Game="A4x4"
#Game="A5x5"
#Game="A6x6"
Game="G7x7"
#Game="G9x9"

def n_board(Game):
    n = int(Game[1])
    return n



def server_for_go(host='localhost', port=12345):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(2)

    print("Waiting for two agents to connect...")
    agent1, addr1 = server_socket.accept()
    print("Agent 1 connected from", addr1)
    bs=b'AG1 '+Game.encode()
    agent1.sendall(bs)

    agent2, addr2 = server_socket.accept()
    print("Agent 2 connected from", addr2)
    bs=b'AG2 '+Game.encode()
    agent2.sendall(bs)
    
    n = n_board(Game)
    initial_board = np.zeros((n, n),dtype=int)# tabuleiro inicial
    Go = GameState(initial_board)    # jogo iniciado
    
    #interface gráfica
    pygame.init()
    screen = setScreen()   
    drawBoard(Go, screen)
    pygame.display.update()

    agents = [agent1, agent2]
    current_agent = 0

    jog=0
    invalid_count = 0   # contar os moves inválidos para o caso de um agente fazer jogadas erradas umas x vezes
    time.sleep(3)
    while True:
        try:
            yet_invalid = False
            data = None
            data = agents[current_agent].recv(1024).decode()
            if not data:
                break

            if data == "PASS":
                agents[current_agent].sendall(b'VALID')
                agents[1-current_agent].sendall(data.encode())
                Go.pass_turn()
                print("pass = ", str(Go.pass_count))
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
                jog = jog+1
                
                # fazer moves
                if is_move_valid(Go, i,j):
                    agents[current_agent].sendall(b'VALID')
                    agents[1-current_agent].sendall(data.encode())
                    Go = Go.move(i,j)
                    time.sleep(0.1)
                    drawBoard(Go, screen)
                    drawPieces(Go, screen)
                    event = pygame.event.poll()
                else:
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
                
            # verficar o estado do jogo
            print(Go.board)
            print(f"pass_count: {Go.pass_count}")
            print(f"end: {Go.end}")
            if is_game_finished(Go):
                Go.end_game()
                winner = Go.winner
                if winner == -1:
                    winner = 2
                p1_score = Go.scores[1]
                p2_score = Go.scores[-1]
                data = "END " + str(winner) + " " + str(p1_score) + " " + str(p2_score)
                agents[current_agent].sendall(data.encode())
                agents[1-current_agent].sendall(data.encode())
                drawResult(Go, screen)
                pygame.display.update()
                time.sleep(4)
                pygame.quit()
                break
            

            # mudar de agente
            if not yet_invalid:
                current_agent = 1-current_agent

        except Exception as e:
            print("Error:", e)
            break

    print("\n-----------------\nGAME END\n-----------------\n")
    time.sleep(1)
    agent1.close()
    agent2.close()
    server_socket.close()
    
    
if __name__ == "__main__":
    server_for_go()

    




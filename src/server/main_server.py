import threading
import time
from random import randint
from timeit import default_timer as timer
import socket
from _thread import *
import _pickle as pickle
from src.config.Config import Config
from src.gameSetting.game import Game
from src.gameSetting.gameInit import GameInit
from src.player.player import Player
from src.server.clientInfo import ClientInfo
from src.database.firebasedb import firebase
import pygame

db = firebase.database()

class main_server:
    def __init__(self):
        self.start = timer()
        self.game = Game()
        self.chat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.chat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.game_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.HOST_NAME = socket.gethostname()
        self.SERVER_IP = socket.gethostbyname(self.HOST_NAME)
        self.init = GameInit()
        self.config = Config()
        self.time = 0
        self.win = False
        self.winner = None
        self.playersId = [1, 2, 3, 4]
        self.clients = {}
        self.fun()

    # try to connect to server
    def fun(self):
        try:
            self.game_socket.bind((self.SERVER_IP, 420))
            self.chat_socket.bind((self.SERVER_IP, 450))
        except socket.error as e:
            print(str(e))
            print("[SERVER] Server could not start")
            quit()

        self.game_socket.listen()  # listen for game connections
        print(f"[SERVER] Server Started with local ip {self.SERVER_IP}")
        self.chat_socket.listen() # listen for chat connections
        print("waiting for connection")

        while True:
            chat_host, chat_addr = self.chat_socket.accept()
            print("[CONNECTION] chat - Connected to:", chat_addr)
            start_new_thread(self.handle_client, (chat_host,))

            waiting_for_game = True

            while waiting_for_game:
                print("waiting for game to connect")
                game_host, game_addr = self.game_socket.accept()
                print("[CONNECTION] game - Connected to:", game_addr)
                self.init.connections += 1
                if self.init.connections <= self.config.playersNumer:
                    print("thread")
                    t = threading.Thread(target=self.threaded_client, args=(game_host, self.playersId.pop(0),))
                    #start_new_thread(self.threaded_client, (game_host, self.playersId.pop(0)))
                    t.start()
                    waiting_for_game = False
                    print("done")

    def handle_client(self, client):  # Takes client socket as argument.
        """Handles a single client connection."""
        name = ""
        prefix = ""

        while True:
            msg = client.recv(2048)

            if not msg is None:
                msg = msg.decode("utf-8")

            if msg == "":
                msg = "{QUIT}"

            # Avoid messages before registering
            if msg.startswith("{ALL}") and name:
                new_msg = msg.replace("{ALL}", "{MSG}" + prefix)
                self.send_message(new_msg, broadcast=True)
                continue

            if msg.startswith("{REGISTER}"):
                name = msg.split("}")[1]
                welcome = '{MSG}Welcome %s!' % name
                self.send_message(welcome, destination=client)
                msg = "{MSG}%s has joined the chat!" % name
                self.send_message(msg, broadcast=True)
                self.clients[client] = name
                prefix = name + ": "
                self.send_clients()
                continue

            if msg == "{QUIT}":
                client.close()
                try:
                    del self.clients[client]
                except KeyError:
                    pass
                if name:
                    self.send_message("{MSG}%s has left the chat." % name, broadcast=True)
                    self.send_clients()
                break

            # Avoid messages before registering
            if not name:
                continue
            # We got until this point, it is either an unknown message or for an
            # specific client...
            try:
                msg_params = msg.split("}")
                dest_name = msg_params[0][1:]  # Remove the {
                dest_sock = self.find_client_socket(dest_name)
                if dest_sock:
                    self.send_message(msg_params[1], prefix=prefix, destination=dest_sock)
                else:
                    print("Invalid Destination. %s" % dest_name)
            except:
                print("Error parsing the message: %s" % msg)

    def send_clients(self):
        self.send_message("{CLIENTS}" + self.get_clients_names(), broadcast=True)

    def get_clients_names(self,separator="|"):
        names = []
        for _, name in self.clients.items():
            names.append(name)
        return separator.join(names)

    def find_client_socket(self,name):
        for cli_sock, cli_name in self.clients.items():
            if cli_name == name:
                return cli_sock
        return None

    def send_message(self,msg, prefix="", destination=None, broadcast=False):
        send_msg = bytes(prefix + msg, "utf-8")
        if broadcast:
            """Broadcasts a message to all the clients."""
            for sock in self.clients:
                sock.send(send_msg)
        else:
            if destination is not None:
                destination.send(send_msg)

    def threaded_client(self, conn, _id):
        data = conn.recv(16)
        name = data.decode("utf-8")
        print("[LOG]", name, "connected to the server.")
        keys=db.child("players").shallow().get().val()
        flag=True
        if(keys):
            for i in keys:
                if (name == i):
                    flag = False
                    player_data = db.child("players").child(name).get().val()
                    player = Player(self.game, self, self.init, self.config, _id, player_data["position"],
                                    player_data["max_speed"],
                                    player_data["turn"])
                    self.game.players.append(player)
                    clientsList = ClientInfo(self.config, _id, player_data["position"],
                                             player_data["angle"], player_data["speed"],
                                             player_data["max_speed"], player_data["acceleration"],
                                             player_data["breaks"], player_data["turn"], player_data["lab"],
                                             player.rect, 0,
                                             self.game.showTimer, self.game.positionTimer, player_data["win"],
                                             self.winner,
                                             self.init.connections)
                    self.init.addPlayer(clientsList)


        if (flag):
            player = Player(self.game, self, self.init, self.config, _id, None, self.config.player['speed'],
                            self.config.player['turn'])

            self.game.players.append(player)
            clientsList = ClientInfo(self.config, player.id, player.position, player.angle, player.speed,
                                     player.max_speed,
                                     player.acceleration, player.breaks, player.turn, player.lab, player.rect, 0,
                                     self.game.showTimer, self.game.positionTimer, self.win, self.winner,
                                     self.init.connections)

            data = {
                "id": player.id,
                "position": player.position,
                "angle": player.angle,
                "speed": player.speed,
                "max_speed": player.max_speed,
                "acceleration": player.acceleration,
                "breaks": player.breaks,
                "turn": player.turn,
                "lab": player.lab,
                # "rect": player.rect,
                "time": 0,
                "showTimer": self.game.showTimer,
                "posTimer": self.game.positionTimer,
                "win": self.win,
                "name": self.winner,
                "connection": self.init.connections
            }
            db.child("players").child(name).set(data)
            self.init.addPlayer(clientsList)
        start_time = time.time()
        conn.send(str.encode(str(_id)))
        restart = False
        run = True
        while run:
            data = conn.recv(1024)
            if not data:
                break
            self.time = (pygame.time.get_ticks() - start_time)
            data = data.decode("utf-8")
            # look for specific commands from received data
            if data.split(" ")[0] == "move":
                m, s = divmod(int(self.time / 1000), 60)
                if int(s) == self.game.countTimer and not self.game.showTimer:
                    self.game.showTimer = True
                    self.game.positionTimer = self.config.timer['positon'][randint(0, 2)]
                    # self.game.positionTimer = self.config.timer['positon'][0]

                split_data = data.split(" ")
                key = []
                for i in range(1, len(split_data)):
                    key.append(split_data[i])

                if key[4] == 'False':
                    run = False

                if self.init.connections == self.config.playersNumer:

                    player.onServer(key)
                    # run = player.onServer(key)

                    if player.lab == self.config.labs:
                        self.win = True
                        self.winner = name
                        self.init.connections = 0

                    if restart:
                        self.win = False
                        self.winner = None
                        restart = False
                    clientsList.updateValues(player.id, player.position, player.angle, player.speed, player.max_speed,
                                             player.acceleration, player.breaks, player.turn, player.lab,
                                             player.rect, self.time - player.bonusTime, self.game.showTimer,
                                             self.game.positionTimer, self.win, self.winner, self.init.connections)
                    updated_data = {
                        "id": player.id,
                        "position": player.position,
                        "angle": player.angle,
                        "speed": player.speed,
                        "max_speed": player.max_speed,
                        "acceleration": player.acceleration,
                        "breaks": player.breaks,
                        "turn": player.turn,
                        "lab": player.lab,
                        # "rect": player.rect,
                        "time": 0,
                        "showTimer": self.game.showTimer,
                        "posTimer": self.game.positionTimer,
                        "win": self.win,
                        "winner": self.winner,
                        "connection": self.init.connections
                    }
                    db.child("players").child(name).update(updated_data)
                else:
                    clientsList.updateValues(player.id, player.position, player.angle, player.speed, player.max_speed,
                                             player.acceleration, player.breaks, player.turn, player.lab,
                                             player.rect, 0, False,
                                             None, self.win, self.winner, self.init.connections)
                    updated_data = {
                        "id": player.id,
                        "position": player.position,
                        "angle": player.angle,
                        "speed": player.speed,
                        "max_speed": player.max_speed,
                        "acceleration": player.acceleration,
                        "breaks": player.breaks,
                        "turn": player.turn,
                        "lab": player.lab,
                        # "rect": player.rect,
                        "time": 0,
                        "showTimer": self.game.showTimer,
                        "posTimer": self.game.positionTimer,
                        "win": self.win,
                        "winner": self.winner,
                        "connection": self.init.connections
                    }
                    db.child("players").child(name).update(updated_data)

            elif data.split(" ")[0] == "time":
                start_time = pygame.time.get_ticks()
                self.time = (pygame.time.get_ticks() - start_time)
                clientsList.updateValues(player.id, player.position, player.angle, player.speed, player.max_speed,
                                         player.acceleration, player.breaks, player.turn, player.lab, player.rect,
                                         self.time - player.bonusTime, self.game.showTimer, self.game.positionTimer,
                                         self.win, self.winner, self.init.connections)
                updated_data = {
                    "id": player.id,
                    "position": player.position,
                    "angle": player.angle,
                    "speed": player.speed,
                    "max_speed": player.max_speed,
                    "acceleration": player.acceleration,
                    "breaks": player.breaks,
                    "turn": player.turn,
                    "lab": player.lab,
                    # "rect": player.rect,
                    "time": 0,
                    "showTimer": self.game.showTimer,
                    "posTimer": self.game.positionTimer,
                    "win": self.win,
                    "winner": self.winner,
                    "connection": self.init.connections
                }
                db.child("players").child(name).update(updated_data)

            elif data.split(" ")[0] == "restart":
                restart = True
                player.restart()
                start_time = pygame.time.get_ticks()
                self.game.countTimer = self.config.timer['countTimer']
                self.game.showTimer = False
                self.game.positionTimer = None
                self.time = 0
                self.init.connections += 1
                clientsList.updateValues(player.id, player.position, player.angle, player.speed, player.max_speed,
                                         player.acceleration, player.breaks, player.turn, player.lab, player.rect,
                                         self.time - player.bonusTime, self.game.showTimer, self.game.positionTimer,
                                         self.win, self.winner, self.init.connections)
                updated_data = {
                    "id": player.id,
                    "position": player.position,
                    "angle": player.angle,
                    "speed": player.speed,
                    "max_speed": player.max_speed,
                    "acceleration": player.acceleration,
                    "breaks": player.breaks,
                    "turn": player.turn,
                    "lab": player.lab,
                    # "rect": player.rect,
                    "time": 0,
                    "showTimer": self.game.showTimer,
                    "posTimer": self.game.positionTimer,
                    "win": self.win,
                    "winner": self.winner,
                    "connection": self.init.connections
                }
                db.child("players").child(name).update(updated_data)

            else:
                clientsList.updateValues(player.id, player.position, player.angle, player.speed, player.max_speed,
                                         player.acceleration, player.breaks, player.turn, player.lab, player.rect,
                                         0, self.game.showTimer, self.game.positionTimer, self.win, self.winner,
                                         self.init.connections)
                updated_data = {
                    "id": player.id,
                    "position": player.position,
                    "angle": player.angle,
                    "speed": player.speed,
                    "max_speed": player.max_speed,
                    "acceleration": player.acceleration,
                    "breaks": player.breaks,
                    "turn": player.turn,
                    "lab": player.lab,
                    # "rect": player.rect,
                    "time": 0,
                    "showTimer": self.game.showTimer,
                    "posTimer": self.game.positionTimer,
                    "win": self.win,
                    "winner": self.winner,
                    "connection": self.init.connections
                }
                db.child("players").child(name).update(updated_data)

            conn.send(pickle.dumps(self.init.players))
            time.sleep(0.001)

        # When user disconnects
        print("[DISCONNECT] Name:", name, ", Client Id:", _id, "disconnected")
        self.playersId.append(_id)
        self.playersId.sort()
        self.init.connections -= 1

        if clientsList in self.init.players:
            self.init.removePlayer(clientsList)  # remove client information from players list
            self.game.players.remove(player)
        conn.close()  # close connection

main_server()


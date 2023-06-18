import pickle
import socket
import sys
import threading
import time
from _thread import *
import functools
from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QMessageBox, QTabWidget
from PyQt5.QtWidgets import QGridLayout, QScrollArea, QLabel, QListView
from PyQt5.QtWidgets import QLineEdit, QComboBox, QGroupBox, QAction
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont
from src.config.Config import Config
from src.gameSetting.game import Game
import pygame
import src.server.network as network


class MyTableWidget(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.conn = socket.socket()
        self.connected = False
        self.IP = "15.237.43.244"
        self.port = 450
        # tab UI
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.resize(300, 200)
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tabs.addTab(self.tab1, "Home")
        self.tabs.addTab(self.tab2, "Chat Room")
        self.tabs.setTabEnabled(1, False)
        # <Home>
        gridHome = QGridLayout()
        self.tab1.setLayout(gridHome)
        self.nameBox = QGroupBox("Name")
        self.nameLineEdit = QtWidgets.QLineEdit()
        nameBoxLayout = QVBoxLayout()
        nameBoxLayout.addWidget(self.nameLineEdit)
        self.nameBox.setLayout(nameBoxLayout)
        self.connStatus = QLabel("Status", self)
        font = QFont()
        font.setPointSize(16)
        self.connStatus.setFont(font)
        self.connBtn = QPushButton("Connect")
        self.connBtn.clicked.connect(self.connect_server)
        self.disconnBtn = QPushButton("Disconnect")
        self.disconnBtn.clicked.connect(self.disconnect_server)
        gridHome.addWidget(self.nameBox, 1, 0, 1, 1)
        gridHome.addWidget(self.connStatus, 1, 1, 1, 1)
        gridHome.addWidget(self.connBtn, 2, 0, 1, 1)
        gridHome.addWidget(self.disconnBtn, 2, 1, 1, 1)
        gridHome.setColumnStretch(0, 1)
        gridHome.setColumnStretch(1, 1)
        gridHome.setRowStretch(0, 0)
        gridHome.setRowStretch(1, 0)
        gridHome.setRowStretch(2, 9)
        # </Home>
        # <Chat Room>
        gridChatRoom = QGridLayout()
        self.tab2.setLayout(gridChatRoom)
        self.messageRecords = QLabel("<font color=\"#000000\">Welcome to chat room</font>", self)
        self.messageRecords.setStyleSheet("background-color: white;");
        self.messageRecords.setAlignment(QtCore.Qt.AlignTop)
        self.messageRecords.setAutoFillBackground(True);
        self.scrollRecords = QScrollArea()
        self.scrollRecords.setWidget(self.messageRecords)
        self.scrollRecords.setWidgetResizable(True)
        self.sendTo = "ALL"
        self.sendChoice = QLabel("Send to :ALL", self)
        self.sendComboBox = QComboBox(self)
        self.sendComboBox.addItem("ALL")
        self.sendComboBox.activated[str].connect(self.send_choice)
        self.lineEdit = QLineEdit()
        self.lineEnterBtn = QPushButton("Enter")
        self.lineEnterBtn.clicked.connect(self.enter_line)
        self.lineEdit.returnPressed.connect(self.enter_line)
        self.friendList = QListView()
        self.friendList.setWindowTitle('Room List')
        self.model = QStandardItemModel(self.friendList)
        self.friendList.setModel(self.model)
        gridChatRoom.addWidget(self.scrollRecords, 0, 0, 1, 3)
        gridChatRoom.addWidget(self.friendList, 0, 3, 1, 1)
        gridChatRoom.addWidget(self.sendComboBox, 1, 0, 1, 1)
        gridChatRoom.addWidget(self.sendChoice, 1, 2, 1, 1)
        gridChatRoom.addWidget(self.lineEdit, 2, 0, 1, 3)
        gridChatRoom.addWidget(self.lineEnterBtn, 2, 3, 1, 1)
        gridChatRoom.setColumnStretch(0, 9)
        gridChatRoom.setColumnStretch(1, 9)
        gridChatRoom.setColumnStretch(2, 9)
        gridChatRoom.setColumnStretch(3, 1)
        gridChatRoom.setRowStretch(0, 9)
        # </Chat Room>
        # Initialization
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)


    def enter_line(self):
        # assure the person still in rooom before send out
        if self.sendTo != self.sendComboBox.currentText():
            self.message_display_append("The person left. Private message not delivered")
            self.lineEdit.clear()
            return
        line = self.lineEdit.text()
        if line == "":  # prevent empty message
            return
        if self.sendTo != "ALL":  # private message, send to myself first
            # this is a trick leverage the server sending back a copy to myself
            send_msg = bytes("{" + self.userName + "}" + line, "utf-8")
            self.conn.send(send_msg)
            time.sleep(0.1)  # this is important for not overlapping two sending
        send_msg = bytes("{" + self.sendTo + "}" + line, "utf-8")
        self.conn.send(send_msg)
        self.lineEdit.clear()
        self.scrollRecords.verticalScrollBar().setValue(self.scrollRecords.verticalScrollBar().maximum())


    def message_display_append(self, newMessage, textColor="#000000"):
        oldText = self.messageRecords.text()
        appendText = oldText + "<br /><font color=\"" + textColor + "\">" + newMessage + "</font><font color=\"#000000\"></font>"
        self.messageRecords.setText(appendText)
        time.sleep(0.2)  # this helps the bar set to bottom, after all message already appended
        self.scrollRecords.verticalScrollBar().setValue(self.scrollRecords.verticalScrollBar().maximum())

    def updateRoom(self):
        while self.connected:
            data = self.conn.recv(1024)
            data = data.decode("utf-8")
            print(data)
            if data != "":
                if "{CLIENTS}" in data:
                    welcome = data.split("{CLIENTS}")
                    self.update_send_to_list(welcome[1])
                    self.update_room_list(welcome[1])
                    if not welcome[0][5:] == "":
                        self.message_display_append(welcome[0][5:])
                        self.scrollRecords.verticalScrollBar().setValue(
                            self.scrollRecords.verticalScrollBar().maximum())
                elif data[:5] == "{MSG}":  # {MSG} includes broadcast and server msg
                    self.message_display_append(data[5:], "#006600")
                    self.scrollRecords.verticalScrollBar().setValue(self.scrollRecords.verticalScrollBar().maximum())
                else:  # private messgage is NONE format
                    self.message_display_append("{private}" + data, "#cc33cc")
                    self.scrollRecords.verticalScrollBar().setValue(self.scrollRecords.verticalScrollBar().maximum())
            time.sleep(0.1)  # this is for saving thread cycle time

    def connect_server(self):
        if self.connected == True:
            self.g = start_game()
            self.sg = threading.Thread(target=self.g.connect_game, args=(self.name,))
            self.sg.start()
            return
        self.name = self.nameLineEdit.text()
        if self.name == "":
            self.connStatus.setText("Status :" + "Please enter your name")
            return
        self.userName = self.name
        try:
            self.conn.connect((self.IP, self.port))
        except:
            self.connStatus.setText("Status :" + " Can't enter room")
            self.conn = socket.socket()
            return
        send_msg = bytes("{REGISTER}" + self.name, "utf-8")
        self.conn.send(send_msg)
        self.connected = True
        self.connStatus.setText("Status :" + " Connected")
        self.nameLineEdit.setReadOnly(True)  # This setting is not functional well
        self.tabs.setTabEnabled(1, True)
        self.g = start_game()
        self.rT = threading.Thread(target=self.updateRoom)
        self.sg = threading.Thread(target=self.g.connect_game, args=(self.name,))
        self.rT.start()
        self.sg.start()

    def disconnect_server(self):
        if self.connected == False:
            return
        send_msg = bytes("{QUIT}", "utf-8")
        self.conn.send(send_msg)
        self.connStatus.setText("Status :" + " Disconnected")
        self.nameLineEdit.setReadOnly(False)
        self.nameLineEdit.clear()
        self.tabs.setTabEnabled(1, False)
        self.connected = False
        self.g.run = False
        self.sg.join()
        self.g.disconnect_game()
        self.rT.join()
        self.conn.close()
        self.conn = socket.socket()

    def update_room_list(self, strList):
        L = strList.split("|")
        self.model.clear()
        for person in L:
            item = QStandardItem(person)
            item.setCheckable(False)
            self.model.appendRow(item)

    def update_send_to_list(self, strList):
        L = strList.split("|")
        self.sendComboBox.clear()
        self.sendComboBox.addItem("ALL")
        for person in L:
            if person != self.userName:
                self.sendComboBox.addItem(person)
        previous = self.sendTo
        index = self.sendComboBox.findText(previous)
        print("previous choice:", index)
        if index != -1:
            self.sendComboBox.setCurrentIndex(index)  # updating, maintain receiver
        else:
            self.sendComboBox.setCurrentIndex(0)  # updating, the receiver left, deafault to "ALL"

    def send_choice(self, text):
        self.sendTo = text
        print(self.sendTo)
        self.sendChoice.setText("Send to: " + text)

class start_game():
    def __init__(self):
        self.server = network.Network()
        self.run = True

    def moves(self):
        keys = pygame.key.get_pressed()
        move = [False, False, False, False, True]

        if keys[pygame.K_w]:
            move[0] = True

        if keys[pygame.K_s]:
            move[1] = True

        if keys[pygame.K_a]:
            move[2] = True

        if keys[pygame.K_d]:
            move[3] = True

        if keys[pygame.K_ESCAPE]:
            move[4] = False

        return move


    def connect_game(self, name):
        print("thread")
        pygame.init()
        self.config = Config()

        self.current_id = self.server.connect(name)
        self.players = self.server.send("get")

        game = Game()
        game.screen = pygame.display.set_mode((game.assets.width, game.assets.height))
        pygame.display.set_caption("Car Racing")
        assets = [(game.assets.track, (0, 0)), (game.assets.start, (502, 160)), (game.assets.borders, (0, 0))]

        game.constDraw()
        start = True
        win = False
        sendEndInfo = True

        cur_players = next((x for x in self.players if x.id == self.current_id))

        while self.run:
            pygame.time.Clock().tick(self.config.FPS)

            if start and cur_players.connection == self.config.playersNumer:
                self.players = self.server.send("temp")
                cur_players = next((x for x in self.players if x.id == self.current_id))
                start_ticks = pygame.time.get_ticks()
                game.constDraw()
                while True:
                    seconds = (pygame.time.get_ticks() - start_ticks) / 1000
                    if seconds > 5:
                        break
                    game.draw(game.screen, assets, cur_players.lab, cur_players.speed,
                              cur_players.time)
                    for p in self.players:
                        game.drawCar(game.loadCar(p.id), p.angle, p.position)
                    game.draw_counter(int(seconds))
                    pygame.display.update()
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.disconnect_game()
                            run = False
                game.constDraw()

                data = "time"
                self.players = self.server.send(data)
                start = False

            keys = pygame.key.get_pressed()

            data = "move"
            for m in self.moves():
                data += " " + str(m)

            self.players = self.server.send(data)
            if not self.players:
                break
            cur_players = next((x for x in self.players if x.id == self.current_id))
            game.draw(game.screen, assets, cur_players.lab, cur_players.speed, cur_players.time)


            for p in self.players:
                game.drawCar(game.loadCar(p.id), p.angle, p.position)

            if cur_players.win and not start:
                game.drawWinner(cur_players.name)
                game.draw_end_game_info()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.run = False

            pygame.display.update()
            time.sleep(0.1)
        pygame.quit()
        quit()


    def disconnect_game(self):
        self.server.disconnect()
        pygame.quit()


class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()
        self.setGeometry(50, 50, 500, 300)
        self.setWindowTitle("Chat-Client")
        self.table_widget = MyTableWidget(self)
        self.setCentralWidget(self.table_widget)
        self.show()

    def closeEvent(self, event):
        close = QMessageBox()
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        close = close.exec()
        if close == QMessageBox.Yes:
            self.table_widget.disconnect_server() # disconnect to server before exit
            event.accept()
        else:
            event.ignore()


def run():
    app = QApplication(sys.argv)
    GUI = Window()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()


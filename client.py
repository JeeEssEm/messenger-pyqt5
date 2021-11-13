import sys
from PyQt5 import uic, QtCore, QtGui
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QHBoxLayout, \
    QLabel, QListWidgetItem, QVBoxLayout
from threading import Thread
from sockets import Socket
from encrypt_decrypt import *
import datetime as dt
import pickle

STYLES = {'sent': """
                    margin-bottom: 12px;
                    line-height: 24px;
                    position: relative;
                    padding: 10px 10px;
                    border-radius: 25px;
                    border: 0px solid #212121;
                    background-color: #7289da;
                    color: #fff;
                    font-size: 25px;
                    """,
          'received': """
                    margin-bottom: 12px;
                    line-height: 24px;
                    position: relative;
                    padding: 10px 10px;
                    border-radius: 25px;
                    border: 0px solid #212121;
                    background-color: #23272a;
                    color: #fff;
                    font-size: 25px;
                    """}


def set_time_item(lst, widget, time):
    for r in range(lst.count()):
        item = lst.item(r)
        wid = lst.itemWidget(item)
        if wid == widget:
            item.time = time
            break


class Client(Socket):
    def __init__(self):
        super(Client, self).__init__()
        self.main_form = MainForm(self)  # создание главного окна

    def install(self):
        connection = [i.strip().replace('\n', '') for i
                      in open('config.txt', encoding='utf-8').readlines()]
        self.connect((connection[0], int(connection[1])))
        listen_user = Thread(target=self.listen_user, args=(self,))
        listen_user.start()  # запуска потока получения потоков сервера

    def listen_user(self, user):  # получение всех пакетов от сервера
        while True:
            info = user.recv(8192)
            info = pickle.loads(info)
            if "clients" == info.type:
                self.main_form.receive_clients(info.kwargs['name'])
                self.main_form.msg_signal.emit()  # связь между потоками и запуск метода
                # получение всех пользователей
            elif 'auth' == info.type:
                self.main_form.connection_signal.emit(info.kwargs)
            elif 'create' == info.type:
                self.main_form.auth.creating.signal.emit(info.kwargs['status'])
            elif 'recover' == info.type:
                self.main_form.auth.recover.signal.emit(info.kwargs['status'])
            elif 'global_search' == info.type:
                self.main_form.gl_search_signal.emit(info.kwargs['result'])
            elif 'friend_request' == info.type:
                self.main_form.add_friend_request_signal.emit(info.kwargs['name'])
            elif 'friend_accept' == info.type:
                self.main_form.clients.append(info.kwargs['name'])
                self.main_form.create_profile_signal.emit(info.kwargs['name'])
            elif 'delete' == info.type:
                self.main_form.dialogs[info.kwargs['who']].delete_signal.emit()
            else:
                try:
                    self.main_form.receive_msg(info)
                    # print(self.main_form.dialogs, self.main_form.profiles_lst)
                    # добавление сообщений в чат
                except Exception as e:
                    # print(str(info))
                    print('error', e)
                    # print(self.main_form.profiles_lst, self.main_form.profiles)

    def send_info(self, info):  # отправка сообщения на сервер
        self.send(info)


class MainForm(QMainWindow):
    msg_signal = pyqtSignal()
    connection_signal = pyqtSignal(dict)
    gl_search_signal = pyqtSignal(list)
    add_friend_request_signal = pyqtSignal(str)
    create_profile_signal = pyqtSignal(str)

    def __init__(self, talker):
        super(MainForm, self).__init__()

        self.clients = []
        self.connect_buttons = []
        self.users_labels = []
        self.my_name = ""
        self.dialogs = {}
        self.now = None
        self.profiles_lst = []
        self.log = []
        self.auth = Auth(self)  # окно аутентификации
        self.auth.show()

        self.talker = talker

        self.initUI()

    def initUI(self):
        uic.loadUi("ui/choose_user_form.ui", self)
        self.search_btn.setIcon(QtGui.QIcon('images/lupa.png'))
        self.search_btn.clicked.connect(self.search)
        self.create_profile_signal.connect(self.create_profile)
        self.mms.setColumnMinimumWidth(100, 100)

        self.msg_signal.connect(self.render_messages)
        self.connection_signal.connect(self.connect_start)
        self.gl_search_signal.connect(self.global_search)
        self.add_friend_request_signal.connect(self.add_friend_profile)

    def add_friend_profile(self, name):
        item = QListWidgetItem(self.friend_requests)
        widget = MiniAddFriend(self, name)
        item.setSizeHint(widget.size())
        self.friend_requests.addItem(item)
        self.friend_requests.setItemWidget(item, widget)

    def search(self):
        name = self.search_form.text()
        self.search_results.clear()
        if self.local_s.isChecked():
            self.local_search()
        else:
            self.talker.send(pickle.dumps(SendMessage(type_oper='/global_search',
                                                      search=name, sender=self.my_name)))
        self.search_results.show()

    def local_search(self):
        name = self.search_form.text()
        for record in range(self.profiles.count()):
            item = self.profiles.item(record)
            widget = self.profiles.itemWidget(item)
            if name in widget.name:
                it = QListWidgetItem(self.search_results)
                wid = widget.copy()
                wid.starting.setText('Написать')
                # создание копии объекта, чтобы виджет не исчез из другого списка
                it.setSizeHint(widget.size())
                self.search_results.addItem(it)
                self.search_results.setItemWidget(it, wid)

    def global_search(self, lst):
        for name in lst:
            item = QListWidgetItem(self.search_results)
            wid = MiniFriend(self, name[0])
            wid.starting.setText('Отправить запрос на дружбу')
            item.setSizeHint(wid.size())
            self.search_results.addItem(item)
            self.search_results.setItemWidget(item, wid)

    def receive_msg(self, obj):
        self.dialogs[obj.sender].signal.emit(decode(obj.text, obj.key), obj.kwargs['time'])

    def connect_start(self, data):  # авторизация и полключение к серверу
        if data['status'] == 'ok':
            self.auth.hide()
            self.welcome.setText(data['name'])
            self.clients = data['friends']
            self.my_name = data['name']
            self.render_messages()
            if data['msgs'] != 'No data':
                for fr, txt, time, to in data['msgs']:
                    self.dialogs[fr if fr != self.my_name else to].dialogue_builder(
                        fr, txt, dt.datetime.fromisoformat(time))
            if data['nrms'] != 'No data':
                for fr, msg, time, to in data['nrms']:
                    self.dialogs[fr].signal.emit(msg, dt.datetime.fromisoformat(time))
                    self.dialogs[fr].bg.num_msg.show()
            if data['friend_requests'] != 'No data':
                for name in data['friend_requests']:
                    item = QListWidgetItem(self.friend_requests)
                    widget = MiniAddFriend(self, name)

                    item.setSizeHint(widget.size())
                    self.friend_requests.addItem(item)
                    self.friend_requests.setItemWidget(item, widget)
            self.show()
        else:
            self.auth.status.setText(data['status'])

    def dialogue_start(self, name):  # начало или продолжение диалога с пользователем
        if self.mms.count() and self.log:  # проверка уже отрендеренных диалогов в главном окне
            self.log[-1].hide()  # скрытие запущенного диалога
        if name in self.dialogs:  # открытие ранее начатого и скрытого диалога
            self.now = self.dialogs[name]
            self.now.show()
            self.log.append(self.now)
        else:  # создание диалога
            mini = MiniProfile(self, name)
            self.now = Dialogue(self, name, mini)
            self.dialogs[name] = self.now
            self.mms.addWidget(self.now)
            self.now.show()
            self.profiles_lst.append(mini)
            self.log.append(self.now)
        self.now.bg.num_msg.hide()

    def receive_clients(self, clients):
        self.clients = clients.split()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:  # закрытие приложения -> отключение
        self.talker.close()
        self.close()

    def render_messages(self):
        if self.my_name in self.clients:
            del self.clients[self.clients.index(self.my_name)]
        for user in self.clients:
            if user not in [i.name for i in self.profiles_lst]:
                self.create_profile(user)

        self.sort_messages()

    def create_profile(self, name):
        widget = MiniProfile(self, name)
        item = Item(widget.time)
        item.setSizeHint(widget.size())
        self.profiles.addItem(item)
        self.profiles.setItemWidget(item, widget)
        self.profiles_lst.append(widget)

        d = Dialogue(self, name, widget)
        self.dialogs[name] = d
        self.mms.addWidget(d)
        self.profiles.repaint()

    def sort_messages(self):
        self.profiles.sortItems(QtCore.Qt.DescendingOrder)


class Auth(QWidget):
    def __init__(self, main_form):
        super().__init__()
        self.main = main_form
        self.creating = None
        self.recover = None
        self.InitUI()

    def InitUI(self):
        self.setWindowTitle("Авторизация")
        uic.loadUi("ui/auth.ui", self)
        self.enter.clicked.connect(self.enter_acc)
        self.forget_pass.clicked.connect(self.rec_pass)
        self.create_acc.clicked.connect(self.account_cr)

    def enter_acc(self):
        login = self.login.text()
        password = self.password.text()
        attempt = SendMessage(login=login, pwd=password, type_oper='/auth')
        self.main.talker.send_info(pickle.dumps(attempt))

    def account_cr(self):
        self.creating = CreateAccount(self.main, self)
        self.creating.show()
        self.hide()

    def rec_pass(self):
        self.recover = RecoverAccount(self.main, self)
        self.recover.show()
        self.hide()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:  # закрытие приложения -> отключение
        self.main.talker.close()
        self.close()


class Dialogue(QWidget):
    signal = pyqtSignal(str, dt.datetime)
    delete_signal = pyqtSignal()

    def __init__(self, user, name, mini_bg):
        super().__init__()
        self.user = user
        self.name = name
        self.bg = mini_bg
        self.signal.connect(self.receive_msg)
        self.delete_signal.connect(self.delete_me)
        self.InitUI()
        self.hide()

    def InitUI(self):
        uic.loadUi("ui/test_dialogue.ui", self)
        self.button_sender.setIcon(QtGui.QIcon('images/send.png'))
        self.delete_friend.clicked.connect(self.delete)
        self.status.hide()
        self.talker_name.setText(self.name)
        self.button_sender.clicked.connect(self.buttons)

    def buttons(self):  # визуализация и отправка сообщений
        text = text_split(self.message_field.toPlainText())
        if len(text) > 4000:
            self.status.show()
            self.status.setText(f'Длина сообщения не должна превышать 4000, {len(text)}/4000')
        elif text == '':
            pass
        else:
            self.status.hide()
            item = QListWidgetItem(self.messages)
            widget = QWidget()
            text_w = QLabel(text)
            text_w.setStyleSheet(STYLES['sent'])

            lay = QHBoxLayout()
            lay.setAlignment(QtCore.Qt.AlignRight)
            lay.addWidget(text_w)
            widget.setLayout(lay)

            item.setSizeHint(widget.sizeHint())

            self.messages.addItem(item)
            self.messages.setItemWidget(item, widget)
            self.bg.last_msg.setText(text[:15] if len(text) > 15 else text)

            time = dt.datetime.now()
            msg = SendMessage("/send", sender=self.user.my_name, text=text, name=self.name,
                              time=time)
            info = pickle.dumps(msg)
            self.bg.time = time
            self.user.talker.send_info(info)
            self.message_field.clear()

            set_time_item(self.user.profiles, self.bg, time)
            self.user.sort_messages()

    def receive_msg(self, msg, time):  # получение и визуализация сообщений
        item = QListWidgetItem(self.messages)
        widget = QWidget()
        text_w = QLabel(msg)
        text_w.setStyleSheet(STYLES['received'])

        lay = QHBoxLayout()
        lay.setAlignment(QtCore.Qt.AlignLeft)
        lay.addWidget(text_w)
        widget.setLayout(lay)

        item.setSizeHint(widget.sizeHint())

        self.messages.addItem(item)
        self.messages.setItemWidget(item, widget)

        self.bg.time = time
        set_time_item(self.user.profiles, self.bg, time)
        self.bg.last_msg.setText(msg[:15] if len(msg) > 15 else msg)

        if self.isHidden():
            # print('должен быть show', self.bg)
            self.bg.num_msg.show()
        self.user.sort_messages()

    def dialogue_builder(self, fr, text, time):
        item = QListWidgetItem(self.messages)
        widget = QWidget()
        text_w = QLabel(text)
        lay = QHBoxLayout()
        if fr == self.user.my_name:
            text_w.setStyleSheet(STYLES['sent'])
            lay.setAlignment(QtCore.Qt.AlignRight)
        else:
            text_w.setStyleSheet(STYLES['received'])
            lay.setAlignment(QtCore.Qt.AlignLeft)
        lay.addWidget(text_w)
        widget.setLayout(lay)
        item.setSizeHint(widget.sizeHint())
        self.messages.addItem(item)
        self.messages.setItemWidget(item, widget)
        self.bg.last_msg.setText(text[:15] if len(text) > 15 else text)

        set_time_item(self.user.profiles, self.bg, time)
        self.user.sort_messages()

    def delete_me(self):
        del self.user.profiles_lst[self.user.profiles_lst.index(
            [i for i in self.user.profiles_lst if i.name == self.name][0])]
        del self.user.dialogs[self.name]
        for row in range(self.user.profiles.count()):
            item = self.user.profiles.item(row)
            widget = self.user.profiles.itemWidget(item)
            if widget is not None and widget.name == self.name:
                widget.close()
                self.user.profiles.takeItem(row)
        # self.user.listView.show()
        self.user.profiles.repaint()
        self.close()

    def delete(self):
        self.user.talker.send(pickle.dumps(
            SendMessage(type_oper='/delete', friend=self.name, my_name=self.user.my_name)))
        self.delete_me()


class MiniProfile(QWidget):
    def __init__(self, form, name, last_msg='', time=dt.datetime(year=2000, month=1, day=1)):
        super(MiniProfile, self).__init__()
        self.last = last_msg
        self.form = form
        self.name = str(name)
        self.time = time
        self.initUI()

    def initUI(self):
        uic.loadUi('ui/mini_bg.ui', self)
        self.last_msg.setText(self.last)
        self.label.setText(self.name)
        self.num_msg.hide()
        self.starting.clicked.connect(self.go)

    def go(self):
        self.form.listView.hide()
        self.form.dialogue_start(self.label.text())

    def copy(self):
        return MiniProfile(self.form, self.name, last_msg=self.last_msg.text())


class MiniFriend(MiniProfile):
    def go(self):
        self.form.talker.send(
            pickle.dumps(SendMessage(type_oper='/add_friend', my_name=self.form.my_name,
                                     friend=self.name)))


class MiniAddFriend(QWidget):
    def __init__(self, form, name):
        super(MiniAddFriend, self).__init__()
        self.form = form
        self.name = str(name)
        self.initUI()

    def initUI(self):
        uic.loadUi('ui/mini_add_friend.ui', self)
        self.fr_name.setText(self.name)
        self.accept.clicked.connect(self.accept_req)
        self.deny.clicked.connect(self.deny_req)

    def accept_req(self):
        self.form.talker.send(
            pickle.dumps(SendMessage(type_oper='/accept_friend', my_name=self.form.my_name,
                                     friend=self.name)))

        self.form.clients.append(self.name)
        self.form.create_profile(self.name)
        self.delete_me()

    def delete_me(self):
        for row in range(self.form.friend_requests.count()):
            if self.form.friend_requests.itemWidget(self.form.friend_requests.item(row)) == self:
                self.form.friend_requests.takeItem(row)
                break

    def deny_req(self):
        self.form.talker.send(
            pickle.dumps(SendMessage(type_oper='/deny_friend', my_name=self.form.my_name,
                                     friend=self.name)))
        self.delete_me()


class CreateAccount(QWidget):
    signal = pyqtSignal(str)

    def __init__(self, main_form, auth):
        super().__init__()
        self.main = main_form
        self.auth = auth
        self.signal.connect(self.status_reg)
        self.InitUI()

    def InitUI(self):
        uic.loadUi('ui/create_acc.ui', self)
        self.go_back()

        self.status.hide()
        self.confirm.clicked.connect(self.create_acc)
        self.back_auth.clicked.connect(self.back_to_auth)
        self.back.clicked.connect(self.go_back)
        self.continue_2.clicked.connect(self.next)

    def next(self):
        for row in range(self.verticalLayout_2.count()):
            item = self.verticalLayout_2.itemAt(row)
            el = item.widget()
            if type(item) == QHBoxLayout:
                for r in range(item.count()):
                    el = item.itemAt(r).widget()
                    el.show()
            elif el is not None:
                el.show()
        for row in range(self.verticalLayout.count()):
            el = self.verticalLayout.itemAt(row).widget()
            if el is not None:
                el.hide()

    def go_back(self):
        for row in range(self.verticalLayout_2.count()):
            item = self.verticalLayout_2.itemAt(row)
            el = item.widget()
            if type(item) == QHBoxLayout:
                for r in range(item.count()):
                    el = item.itemAt(r).widget()
                    el.hide()
            elif el is not None:
                el.hide()
        for row in range(self.verticalLayout.count()):
            el = self.verticalLayout.itemAt(row).widget()
            if el is not None:
                el.show()

    def back_to_auth(self):
        self.hide()
        self.auth.show()

    def create_acc(self):
        name = self.name.text()
        pwd = self.pwd.text()
        pwd2 = self.pwd_2.text()
        pet = self.pet_name.text()
        team = self.sport_team.text()
        if pwd == '':
            self.status.setText('Вы не ввели пароль')
            self.status.show()
        elif pwd != pwd2:
            self.status.setText('Пароли не совпадают')
            self.status.show()
        elif name == '':
            self.status.setText('Вы не ввели имя')
            self.status.show()
        elif ' ' in name or ' ' in pwd:
            self.status.setText('Имя или пароль не должны содержать пробельных символов')
            self.status.show()
        elif len(name) > 16:
            self.status.setText('Длина имени не должна превышать 16 символов')
            self.status.show()
        elif pet == '' and team == '':
            self.status.setText('Введите хотя бы один из ответов на контрольный вопрос,'
                                ' иначе вы не сможете восстановить аккаунт, с случае утери пароля')
            self.status.show()
        else:
            self.main.talker.send(pickle.dumps(SendMessage(
                login=name, pwd=pwd, pet=pet, team=team, type_oper='/create')))

    def status_reg(self, res):
        if res == 'ok':
            self.auth.show()
            self.hide()
        else:
            self.status.setText(res)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:  # закрытие приложения -> отключение
        self.main.talker.close()
        self.close()


class RecoverAccount(QWidget):
    signal = pyqtSignal(str)

    def __init__(self, main_form, auth):
        super().__init__()
        self.main = main_form
        self.auth = auth
        self.signal.connect(self.status_rec)
        self.InitUI()

    def InitUI(self):
        uic.loadUi('ui/recover_acc.ui', self)
        self.confirm.clicked.connect(self.recover)
        self.back.clicked.connect(self.go_back)

    def recover(self):
        login = self.login.text()
        pet = self.pet.text()
        team = self.team.text()
        new_pass = self.password.text()
        con_pass = self.rep_password.text()
        if new_pass != con_pass:
            self.status.setText('Пароли не совпадают')
        elif new_pass == '':
            self.status.setText('Вы не ввели пароль')
        elif pet == '' and team == '':
            self.status.setText('Введите хотя бы один из ответов на контрольный вопрос')
        elif login == '':
            self.status.setText('Вы не ввели логин')
        else:
            self.main.talker.send(pickle.dumps(SendMessage(
                login=login, pwd=new_pass, pet=pet, team=team, type_oper='/recover')))

    def status_rec(self, res):
        if res == 'ok':
            self.auth.show()
            self.hide()
        else:
            self.status.setText(res)

    def go_back(self):
        self.hide()
        self.auth.show()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.main.talker.close()
        self.close()


class Item(QListWidgetItem):
    def __init__(self, time):
        super().__init__()
        self.time = time

    def __lt__(self, other):
        return self.time < other.time

    def __gt__(self, other):
        return self.time > other.time

    def __ge__(self, other):
        return self.time >= other.time

    def __le__(self, other):
        return self.time <= other.time


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = Client()
    ex.install()
    sys.exit(app.exec())

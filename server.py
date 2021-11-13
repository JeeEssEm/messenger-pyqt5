from sockets import Socket
from threading import Thread
from encrypt_decrypt import *
import pickle
from dbFuncs import DataBase
import hashlib


class Server(Socket):
    def __init__(self):
        super(Server, self).__init__()

        self.clients = []
        self.dict_clients = {}

    def send_msg(self, usr, info):
        # print(usr, info.decode())
        if usr in self.dict_clients:
            DataBase().add_message(info.sender, info.kwargs['name'],
                                   decode(info.text, info.key), info.kwargs['time'])
            info = pickle.dumps(info)
            self.dict_clients[usr].send(info)
        else:
            DataBase().add_not_received_msg(info.sender, usr, decode(info.text, info.key),
                                            info.kwargs['time'])

    def listen_user(self, user):
        try:
            while True:
                info = user.recv(8192)
                info = pickle.loads(info)
                if "/name" == info.type:
                    # if clients[-1] in dict_clients.values():
                    #     del dict_clients[
                    #         list(dict_clients.keys())[list(dict_clients.values()).index(clients[-1])]]
                    self.dict_clients[info.name] = self.clients[self.clients.index(user)]

                    info_to_send = pickle.dumps(SendMessage(
                        "clients", name=" ".join(list(self.dict_clients.keys()))))
                    # user.send(info_to_send)
                    self.send_new_user(info_to_send)

                elif "/send" == info.type:
                    self.send_msg(info.kwargs['name'], info)

                elif "/auth" == info.type:
                    res = DataBase().auth_user(
                        info.kwargs['login'],
                        hashlib.sha256(info.kwargs['pwd'].encode('utf-8')).hexdigest())
                    msg = SendMessage(type_oper='auth', status=res, name=info.kwargs['login'])
                    if res == 'ok':
                        friends = DataBase().get_friends(info.kwargs['login'])
                        nrms = DataBase().get_not_received_msgs(info.kwargs['login'])
                        fr_reqs = DataBase().get_friend_requests(info.kwargs['login'])
                        all_msgs = DataBase().all_data(info.kwargs['login'])
                        msg = SendMessage(type_oper='auth', status=res, name=info.kwargs['login'],
                                          friends=friends, nrms=nrms, msgs=all_msgs,
                                          friend_requests=fr_reqs)
                        if nrms != 'No data':
                            for fr, txt, time, to in nrms:
                                DataBase().add_message(fr, to, txt, time)
                        self.dict_clients[info.kwargs['login']] = self.clients[
                            self.clients.index(user)]

                    user.send(pickle.dumps(msg))
                    # метод, проверяющий пользователя в базе и отправляющий список друзей
                elif "/create" == info.type:
                    attempt = DataBase().create_acc(
                        info.kwargs['login'],
                        hashlib.sha256(info.kwargs['pwd'].encode('utf-8')).hexdigest(),
                        info.kwargs['pet'], info.kwargs['team'])
                    msg = SendMessage(type_oper='create', status=attempt)
                    user.send(pickle.dumps(msg))
                    # заносит пользователя в базу
                elif '/recover' == info.type:
                    attempt = DataBase().rec_acc(
                        info.kwargs['login'], info.kwargs['pet'], info.kwargs['team'],
                        hashlib.sha256(info.kwargs['pwd'].encode('utf-8')).hexdigest())
                    msg = SendMessage(type_oper='recover', status=attempt)
                    user.send(pickle.dumps(msg))
                    # смена пароля
                elif '/global_search' == info.type:
                    user.send(pickle.dumps(SendMessage(type_oper='global_search',
                                                       result=DataBase().search(
                                                           info.kwargs['search'],
                                                           info.sender))))
                elif '/add_friend' == info.type:
                    if not DataBase().check_requests(info.kwargs['friend'], info.kwargs['my_name'])\
                            and info.kwargs['friend'] not in \
                            DataBase().get_friends(info.kwargs['my_name']):

                        if info.kwargs['friend'] in self.dict_clients.keys():
                            self.dict_clients[info.kwargs['friend']].send(pickle.dumps(
                                SendMessage(
                                    type_oper='friend_request', name=info.kwargs['my_name'])))

                        DataBase().add_friend_request(info.kwargs['friend'], info.kwargs['my_name'])

                elif '/accept_friend' == info.type:
                    DataBase().add_friend(info.kwargs['my_name'], info.kwargs['friend'])
                    DataBase().delete_friend_request(info.kwargs['my_name'], info.kwargs['friend'])
                    if info.kwargs['friend'] in self.dict_clients.keys():
                        self.dict_clients[info.kwargs['friend']].send(pickle.dumps(SendMessage(
                            type_oper='friend_accept', name=info.kwargs['my_name'])))

                elif '/deny_friend' == info.type:
                    DataBase().delete_friend_request(info.kwargs['my_name'], info.kwargs['friend'])

                elif '/delete' == info.type:
                    print(str(info))
                    DataBase().delete_friend(info.kwargs['friend'], info.kwargs['my_name'])
                    if info.kwargs['friend'] in self.dict_clients.keys():
                        self.dict_clients[info.kwargs['friend']].send(pickle.dumps(
                            SendMessage(type_oper='delete', who=info.kwargs['my_name'])))

                else:
                    print(f"{user} отправил: {info}")

        except Exception as e:
            print(e)
            del self.clients[self.clients.index(user)]
            if user in self.dict_clients.values():
                del self.dict_clients[list(self.dict_clients.keys())[(list(
                    self.dict_clients.values()).index(user))]]
            info_to_send = pickle.dumps(SendMessage(
                "clients", name=" ".join(list(self.dict_clients.keys()))))
            # user.send(info_to_send)
            self.send_new_user(info_to_send)

    def start(self):
        while True:
            user, address = self.accept()
            print(f'{address} подключен')
            self.clients.append(user)
            listen_this_user = Thread(target=self.listen_user, args=(user,))
            listen_this_user.start()

    def send_new_user(self, user):
        for client in self.dict_clients.values():
            client.send(user)

    def install(self):
        self.bind(("127.0.0.1", 3389))
        self.listen(5)
        self.start()


if __name__ == "__main__":
    serv = Server()
    serv.install()

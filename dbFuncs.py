import sqlite3


class DataBase:
    def __init__(self):
        self.con = sqlite3.connect('auth.db')
        self.cur = self.con.cursor()

    def auth_user(self, login, password):
        log = self.cur.execute(f"""SELECT Password FROM Passwords
WHERE Name = '{login}'""").fetchall()
        if not log:
            return 'Неправильный логин'
        return 'Неверный пароль' if log[0][0] != password else 'ok'

    def get_friends(self, name):
        friends = self.cur.execute(f"""
SELECT DISTINCT (SELECT Name FROM Passwords WHERE Friends.FriendID = Passwords.UserID) FROM
Passwords,
Friends
WHERE Friends.UserID = (SELECT UserID FROM Passwords WHERE Name = '{name}')""").fetchall()
        return [i[0] for i in friends]

    def create_acc(self, name, pwd, pet, team):
        quest = self.cur.execute(f"""SELECT Name FROM Passwords WHERE
Name = '{name}'""").fetchall()
        if not quest:
            self.cur.execute(f"""INSERT INTO Passwords(Name, Password) VALUES('{name}', '{pwd}')""")
            self.cur.execute(f"""INSERT INTO SecretQuestions(UserID, Pet, SportTeam)
VALUES((SELECT UserID FROM Passwords WHERE Name = '{name}'), '{pet}', '{team}')""")
            self.con.commit()
            return 'ok'
        return 'это имя уже занято'

    def rec_acc(self, name, pet, team, pwd):
        exist = self.cur.execute(f"""SELECT Name FROM Passwords
WHERE '{name}' = Name """).fetchall()
        if not exist:
            return 'Такого логина не существует'
        users = self.cur.execute(f"""SELECT Passwords.Name FROM Passwords, SecretQuestions
WHERE Passwords.UserID = SecretQuestions.UserID AND '{pet}' = SecretQuestions.Pet AND
'{team}' = SecretQuestions.SportTeam AND '{name}' = Passwords.Name""").fetchall()
        if users:
            self.cur.execute(f"""UPDATE Passwords SET Password = '{pwd}'
WHERE Name = '{name}'""")
            self.con.commit()
            return 'ok'

        return 'Вы неправильно ответили на контрольные вопросы'

    def add_not_received_msg(self, fr, to, text, time):
        self.cur.execute(f"""INSERT INTO NotReceivedMsgs(Sender, Receiver, Message, Time)
VALUES((SELECT UserID FROM Passwords WHERE Name = '{fr}'),
(SELECT UserID FROM Passwords WHERE Name = '{to}'), '{text}', '{time}')""")
        self.con.commit()

    def get_not_received_msgs(self, to):
        # data = self.cur.execute(f"""SELECT Passwords.Name, NotReceivedMsgs.Message FROM
        # Passwords, NotReceivedMsgs WHERE Passwords.UserID = NotReceivedMsgs.Sender AND
        # NotReceivedMsgs.Receiver IN (SELECT UserID FROM Passwords WHERE Name = '{
        # to}')""").fetchall()
        data = self.cur.execute(f"""
SELECT (SELECT Name FROM Passwords WHERE UserID = NotReceivedMsgs.Sender),
NotReceivedMsgs.Message, NotReceivedMsgs.Time, Passwords.Name
FROM
Passwords,
NotReceivedMsgs
WHERE NotReceivedMsgs.Receiver = (SELECT UserID FROM Passwords WHERE Name = '{to}')
AND Passwords.UserID = NotReceivedMsgs.Receiver""").fetchall()

        if data:
            self.cur.execute(f"""DELETE FROM NotReceivedMsgs
WHERE NotReceivedMsgs.Receiver IN (SELECT UserID FROM Passwords WHERE Name = '{to}')""")
            self.con.commit()
        return data if data else 'No data'

    def all_data(self, name):
        # received = self.cur.execute(f"""SELECT Passwords.Name, Messages.Message, Messages.Time
        # FROM Passwords, Messages WHERE Passwords.UserID = Messages.Sender AND Messages.Receiver
        # IN (SELECT UserID FROM Passwords WHERE Name = '{name}')""").fetchall() sent =
        # self.cur.execute(f"""SELECT Passwords.Name, Messages.Message, Messages.Time FROM
        # Passwords, Messages WHERE Messages.Sender = (SELECT UserID FROM Passwords WHERE Name =
        # '{name}') AND Passwords.UserID = Messages.Sender""").fetchall()
        sent = self.cur.execute(f"""
SELECT Passwords.Name, Messages.Message, Messages.Time,
(SELECT Name FROM Passwords WHERE UserID = Messages.Receiver) FROM
        Passwords,
        Messages
WHERE Messages.Sender = (SELECT UserID FROM Passwords WHERE Name = '{name}')
AND Passwords.UserID = Messages.Sender""").fetchall()
        received = self.cur.execute(f"""
SELECT (SELECT Name FROM Passwords WHERE UserID = Messages.Sender), Messages.Message, Messages.Time,
Passwords.Name
 FROM
        Passwords,
        Messages
WHERE Messages.Receiver = (SELECT UserID FROM Passwords WHERE Name = '{name}')
AND Passwords.UserID = Messages.Receiver""").fetchall()
        not_received_from_me = self.cur.execute(f"""
SELECT Passwords.Name, NotReceivedMsgs.Message, NotReceivedMsgs.Time,
(SELECT Name FROM Passwords WHERE UserID = NotReceivedMsgs.Receiver) FROM
        Passwords,
        NotReceivedMsgs
WHERE NotReceivedMsgs.Sender = (SELECT UserID FROM Passwords WHERE Name = '{name}')
AND Passwords.UserID = NotReceivedMsgs.Sender""").fetchall()
        data = sent + received + not_received_from_me
        data.sort(key=lambda record: record[2])
        return data if data else 'No data'

    def add_message(self, fr, to, text, time):
        self.cur.execute(f"""INSERT INTO Messages(Sender, Receiver, Message, Time)
        VALUES((SELECT UserID FROM Passwords WHERE Name = '{fr}'),
        (SELECT UserID FROM Passwords WHERE Name = '{to}'), '{text}', '{time}')""")
        self.con.commit()

    def search(self, name, sender):
        data = self.cur.execute(f"""
SELECT Name FROM Passwords
WHERE Name LIKE '%{name}%' AND UserID NOT IN
(SELECT FriendID FROM Friends
WHERE UserID = (SELECT UserID FROM Passwords WHERE Name = '{sender}')) AND Name != '{sender}'
""").fetchall()
        return data

    def delete_friend_request(self, friend, name):
        self.cur.execute(f"""DELETE FROM FriendRequests
WHERE ReceiverID = (SELECT UserID FROM Passwords WHERE Name = '{friend}') AND
SenderID = (SELECT UserID FROM Passwords WHERE Name = '{name}')""")
        self.cur.execute(f"""DELETE FROM FriendRequests
WHERE ReceiverID = (SELECT UserID FROM Passwords WHERE Name = '{name}') AND
SenderID = (SELECT UserID FROM Passwords WHERE Name = '{friend}')""")
        self.con.commit()

    def add_friend(self, name, friend):
        self.cur.execute(f"""
INSERT INTO Friends(UserID, FriendID) VALUES((SELECT UserID FROM Passwords
WHERE Name = '{name}'),
(SELECT UserID FROM Passwords WHERE Name = '{friend}'))""")
        self.cur.execute(f"""
INSERT INTO Friends(UserID, FriendID) VALUES((SELECT UserID FROM Passwords
WHERE Name = '{friend}'), 
(SELECT UserID FROM Passwords WHERE Name = '{name}'))""")
        self.con.commit()

    def get_friend_requests(self, name):
        data = self.cur.execute(f"""
SELECT (SELECT Name FROM Passwords WHERE UserID = FriendRequests.SenderID) FROM
Passwords,
FriendRequests
WHERE UserID = (SELECT ReceiverID FROM FriendRequests
WHERE (SELECT UserID FROM Passwords WHERE Name = '{name}'))""").fetchall()
        return [i[0] for i in data] if data else 'No data'

    def add_friend_request(self, friend, name):
        if not self.check_requests(friend, name):
            self.cur.execute(f"""
INSERT INTO FriendRequests(SenderID, ReceiverID)
VALUES((SELECT UserID FROM Passwords WHERE Name = '{name}'),
(SELECT UserID FROM Passwords WHERE Name = '{friend}'))""")
            self.con.commit()

    def check_requests(self, friend, name):
        return self.cur.execute(f"""SELECT FriendRequests.SenderID FROM
FriendRequests
WHERE FriendRequests.SenderID = (SELECT UserID FROM Passwords WHERE Name = '{name}')
AND FriendRequests.ReceiverID =
(SELECT UserID FROM Passwords WHERE Name = '{friend}')""").fetchall()

    def delete_friend(self, friend, name):
        self.cur.execute(f"""DELETE FROM Friends
WHERE UserID IN (SELECT UserID FROM Passwords WHERE Name IN ('{friend}', '{name}')) AND
FriendID IN (SELECT UserID FROM Passwords WHERE Name IN ('{friend}', '{name}'))""")
        msgs = self.cur.execute(f"""SELECT Message FROM Messages
WHERE Sender IN (SELECT UserID FROM Passwords WHERE Name IN ('{name}', '{friend}')) AND
Receiver IN (SELECT UserID FROM Passwords WHERE Name IN ('{name}', '{friend}'))""").fetchall()
        if msgs:
            self.cur.execute(f"""
DELETE FROM Messages
WHERE Sender IN (SELECT UserID FROM Passwords WHERE Name IN ('{friend}', '{name}')) AND
Receiver IN (SELECT UserID FROM Passwords WHERE Name IN ('{friend}', '{name}'))""")
        self.con.commit()


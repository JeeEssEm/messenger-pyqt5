import datetime as dt


def encode(text, key):
    encrypted = ""
    for i in text:
        letter = ord(i)
        letter += key
        encrypted += chr(letter)
    return encrypted


def decode(text, key):
    decoded = ""
    for i in text:
        letter = ord(i) - int(key)
        decoded += chr(letter)
    return decoded


class SendMessage:
    # def __init__(self, type_oper, text="", name=None, sender='', login=None, pwd=None, status=None,
    #              friends=None, pet=None, team=None):
    def __init__(self, type_oper, text="", sender='', **kwargs):
        self.key = int(dt.timedelta(hours=dt.datetime.now().hour,
                                    seconds=dt.datetime.now().second).total_seconds())
        self.text = encode(text, self.key)
        self.type = type_oper
        self.sender = sender
        self.kwargs = kwargs

    def __str__(self):
        return f'{self.text} {self.sender} {self.kwargs}'


def text_split(txt):
    res = ''
    if len(txt) > 42:
        for i in range(len(txt)):
            if i % 42 == 0:
                res += '\n' + txt[i:i+42]
    else:
        res = '\n' + txt
    return res[1:]



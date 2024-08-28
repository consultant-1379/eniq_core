import base64
from socket import socket, AF_INET, SOCK_STREAM, SHUT_WR
from subprocess import Popen, PIPE, STDOUT
from time import strftime, gmtime
import sys

ENC_KEY = 'tgh[wo94h[0ht0-we'

def exec_process(command):
    process = Popen(command, stdout=PIPE, stderr=STDOUT)
    stdout = process.communicate()[0]
    if process.returncode != 0:
        raise IOError(process.returncode, stdout)
    return stdout


def netcat(hostname, port, content='', timeout=60):
    s = socket(AF_INET, SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((hostname, port))
    s.sendall(content)
    s.shutdown(SHUT_WR)
    data = None
    try:
        while 1:
            data = s.recv(1024)
            if data == '':
                break
    finally:
        s.close()
    return data


def encode(key, string):
    encoded_chars = []
    for i in xrange(len(string)):
        key_c = key[i % len(key)]
        encoded_c = chr(ord(string[i]) + ord(key_c) % 256)
        encoded_chars.append(encoded_c)
    encoded_string = "".join(encoded_chars)
    return base64.urlsafe_b64encode(encoded_string)


def decode(key, string):
    decoded_chars = []
    string = base64.urlsafe_b64decode(string)
    for i in xrange(len(string)):
        key_c = key[i % len(key)]
        encoded_c = chr(abs(ord(string[i]) - ord(key_c) % 256))
        decoded_chars.append(encoded_c)
    decoded_string = "".join(decoded_chars)
    return decoded_string


class Formatter:
    def __init__(self):
        pass

    VALUE_INC = '\033[33m'
    VALUE_DEC = '\033[36m'
    VALUE_NOC = '\033[92m'
    VALUE_KEY = '\033[7m'

    PLAN_STATE_COLORMAP = {
        'Success': '\033[36m',
        'Running': '\033[7m',
        'Initial': '\033[33m',
        'default': '\033[37m'
    }

    ENDC = '\033[0m'

    @staticmethod
    def format_color(text, color):
        return '{0}{1}{2} '.format(color, text, '\033[0m')

    def _format_color(self, name, value, color):
        return '{0}{1}[{2}]{3} '.format(name, color, value, Formatter.ENDC)

    def format_line(self, current_count, last_count):
        message = ''
        for idx, val in enumerate(current_count):
            cc = current_count[val]
            color = Formatter.VALUE_NOC
            if cc > last_count[val]:
                color = Formatter.VALUE_DEC
            elif cc < last_count[val]:
                color = Formatter.VALUE_INC
            message += self._format_color(val, cc, color)
        return message.strip()

    def print_if_changed(self, base_path, current_status, last_status):
        diff = False
        for key, count in current_status.items():
            if last_status[key] != count:
                diff = True
                break
        if diff:
            this_message = self.format_line(current_status, last_status)
            now = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            base_path = '[{0}]{1}{2}{3}'.format(now, self.VALUE_KEY, base_path,
                                                Formatter.ENDC)
            sys.stdout.write('{0} -> {1}\n'.format(base_path, this_message))
            sys.stdout.flush()

if __name__ == '__main__':
    print(encode(ENC_KEY, '4lackwar31'))
    print(encode(ENC_KEY, 'shroot12'))
import socket
import select
import struct

import config
from common import parse_request_addr, encrypt, decrypt, BUF_SIZE

print 'remote server at', config.server

STATE_WAIT_GREETING = 0
STATE_WAIT_COMMAND = 1
STATE_CONNECTING = 2
STATE_RELAYING = 3

listen_addr = ('localhost', 6560)

lsock = socket.socket()
lsock.bind(listen_addr)
lsock.listen(1024)
print 'listening at', listen_addr

sock2handler = {}

def destroy_socket(sock):
    if not sock:
        return
    sock.close()
    rs.discard(sock)
    ws.discard(sock)
    xs.discard(sock)
    sock2handler.pop(sock, None)

class Relay(object):

    def __init__(self, local_sock):
        local_sock.setblocking(0)
        rs.add(local_sock)

        self.state = STATE_WAIT_GREETING
        self.data_to_local = []
        self.data_to_remote = []
        self.local_sock = local_sock
        self.local_addr = local_sock.getpeername()
        self.remote_sock = None
        self.request_addr = None

    def on_read(self, sock):
        data = sock.recv(BUF_SIZE)
        if not data:
            self.destroy()
            return
        if sock == self.local_sock:
            if self.state == STATE_WAIT_GREETING:
                print 'got greeting from {}: {}'.format(
                    sock.getpeername(), repr(data))
                self.send('\x05\x00', self.local_sock)
                self.state = STATE_WAIT_COMMAND
            elif self.state == STATE_WAIT_COMMAND:
                self.on_command(data)
            elif self.state == STATE_CONNECTING:
                self.data_to_remote.append(data)
                print 'data from app while connecting:', repr(data)
            else:
                raise NotImplementedError('other state')
        elif sock == self.remote_sock:
            if self.state == STATE_CONNECTING:
                self.state = STATE_RELAYING
                if self.data_to_remote:
                    data = ''.join(self.data_to_remote)
                    self.data_to_remote = []
                    data = encrypt(data)
                    self.send(data, sock)
            elif self.state == STATE_RELAYING:
                data = decrypt(data)
                self.send(data, self.local_sock)
            else:
                raise NotImplementedError('oops')
        else:
            raise Exception('oops')

    def on_write(self, sock):
        if sock == self.local_sock:
            data = ''.join(self.data_to_local)
            self.data_to_local = []
            self.send(data, sock)
        elif sock == self.remote_sock:
            if self.state == STATE_CONNECTING:
                self.send(encrypt(self.cmd), sock)
                rs.add(sock)
            elif self.state == STATE_RELAYING:
                data = ''.join(self.data_to_remote)
                self.data_to_remote = []
                self.send(encrypt(data), sock)
            else:
                raise Exception('oops')

    def on_command(self, cmd):
        print 'command:', repr(cmd)
        try:
            parse_request_addr(cmd)
        except Exception as e:
            print e
            self.destroy()
        else:
            self.send('\x05\x00', self.local_sock)
            self.cmd = cmd
            sock = socket.socket()
            self.remote_sock = sock
            sock.setblocking(0)
            sock2handler[sock] = self
            ws.add(sock)
            self.state = STATE_CONNECTING
            sock.connect_ex(config.server)

    def send(self, data, sock):
        n_total = len(data)
        try:
            n_sent = sock.send(data)
        except socket.error as e:
            self.destroy()
            return
        print 'sent to {}: {}'.format(
            sock.getpeername(), repr(data[:n_sent][:70]))
        if n_sent < n_total:
            if sock == self.local_sock:
                self.data_to_local.append(data[n_sent:])
            elif sock == self.remote_sock:
                self.data_to_remote.append(data[n_sent:])
            else:
                raise Exception('oops')
            ws.add(sock)
        else:
            ws.discard(sock)

    def destroy(self):
        print 'closed', self.local_addr
        print
        destroy_socket(self.local_sock)
        destroy_socket(self.remote_sock)

rs, ws, xs = set([lsock]), set([]), set([])
while True:
    r, w, x = select.select(rs, ws, xs, 5)
    for sock in r:
        # listening sock
        if sock == lsock:
            sock, addr = lsock.accept()
            print 'accept', addr
            sock2handler[sock] = Relay(sock)
        # connection sock
        else:
            try:
                handler = sock2handler[sock]
            except KeyError:
                rs.discard(sock)
            handler.on_read(sock)
    for sock in w:
        try:
            handler = sock2handler[sock]
        except KeyError:
            print '!!!!!', sock, 'not found'
            exit()
            ws.discard(sock)
        handler.on_write(sock)

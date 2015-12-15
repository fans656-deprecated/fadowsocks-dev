import select
import socket
from common import encrypt, decrypt, parse_request_addr, BUF_SIZE
import config

STAGE_WAIT_COMMAND = 0
STAGE_CONNECTING = 1
STAGE_RELAYING = 2

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
        self.local_sock = local_sock
        self.local_addr = local_sock.getpeername()
        self.remote_sock = None
        self.stage = STAGE_WAIT_COMMAND
        self.data_to_local = []
        self.data_to_remote = []
        rs.add(local_sock)

    def on_read(self, sock):
        try:
            data = sock.recv(BUF_SIZE)
        except Exception as e:
            print e
            self.destroy()
            return
        if not data:
            self.destroy()
            return
        if self.stage == STAGE_RELAYING:
            if sock == self.local_sock:
                data = decrypt(data)
                print '->', len(data)
                self.send(data, self.remote_sock)
            elif sock == self.remote_sock:
                print '<-', len(data)
                data = encrypt(data)
                self.send(data, self.local_sock)
        elif self.stage == STAGE_WAIT_COMMAND:
            cmd = decrypt(data)
            try:
                request_addr = parse_request_addr(cmd)
                self.send(encrypt('\x05\x00'), self.local_sock)
                sock = socket.socket()
                self.remote_sock = sock
                sock.setblocking(0)
                ws.add(sock)
                sock2handler[sock] = self
                sock.connect_ex(request_addr)
                self.stage = STAGE_CONNECTING
                print 'connecting to remote', request_addr
            except Exception as e:
                print e
                self.destroy()
        elif self.stage == STAGE_CONNECTING:
            data = decrypt(data)
            self.data_to_remote.append(data)

    def on_write(self, sock):
        if sock == self.local_sock:
            data = ''.join(self.data_to_local)
            self.data_to_local = []
        elif sock == self.remote_sock:
            if self.stage == STAGE_CONNECTING:
                if self.data_to_remote:
                    data = ''.join(self.data_to_remote)
                    self.data_to_remote = []
                    print '->', len(data)
                    self.send(data, self.remote_sock)
                else:
                    ws.discard(sock)
                rs.add(sock)
                self.stage = STAGE_RELAYING
                print 'connected', sock.getpeername()
                return
            data = ''.join(self.data_to_remote)
            self.data_to_remote = []
        self.send(data, sock)

    def send(self, data, sock):
        n_total = len(data)
        try:
            n_sent = sock.send(data)
        except socket.error as e:
            print e
            self.destroy()
            return
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


sock2handler = {}

lsock = socket.socket()
lsock.bind(config.server)
lsock.listen(1024)
print 'listen at', lsock.getsockname()

rs, ws, xs = set([lsock]), set(), set()
while True:
    r, w, x = select.select(rs, ws, xs)
    for sock in r:
        if sock == lsock:
            sock, addr = sock.accept()
            print 'accept', addr
            sock2handler[sock] = Relay(sock)
        else:
            try:
                sock2handler[sock].on_read(sock)
            except KeyError:
                print 'sock not found'
                pass
    for sock in w:
        try:
            sock2handler[sock].on_write(sock)
        except KeyError:
            print 'sock not found'
            pass

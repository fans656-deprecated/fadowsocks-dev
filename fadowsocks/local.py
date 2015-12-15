import socket
import select
import struct
import logging
from collections import deque

import config_local as config

logging.basicConfig(level=logging.DEBUG)

SOCKS_VER_5 = '\x05'

BUF_SIZE = 32 * 1024

class Listener(object):

    def __init__(self, listen_sock):
        self.listen_sock = listen_sock

    def on_recv(self, _):
        sock, addr = self.listen_sock.accept()
        logging.debug('accept {}'.format(addr))
        sock2handler[sock] = Relay(sock)
        rs.add(sock)
        ws.add(sock)
        xs.add(sock)

STATE_INIT = 0
STATE_WAIT_FOR_CMD = 1
STATE_RELAYING = 2

class Relay(object):

    def __init__(self, local_sock):
        self.state = STATE_INIT
        self.local_sock = local_sock
        self.remote_sock = None
        self.data_to_remote = deque()
        self.data_to_local = deque()

    def on_recv(self, sock):
        if sock == self.local_sock:
            self.on_local_recv()
        elif sock == self.remote_sock:
            self.on_remote_recv()

    def on_send(self, sock):
        if sock == self.local_sock:
            data_to_send = self.data_to_local
            dst = 'local'
        elif sock == self.remote_sock:
            data_to_send = self.data_to_remote
            dst = 'remote'
        try:
            data = data_to_send[0]
            n_sent = self.local_sock.send(data)
            logging.debug('sent {} to {}'.format(repr(data[:n_sent]), dst))
            if n_sent == len(data):
                data_to_send.popleft()
            else:
                data_to_send[0] = data[n_sent:]
        except IndexError:
            #logging.debug('no data for {}'.format(dst))
            pass

    def on_local_recv(self):
        if self.state == STATE_INIT:
            greeting = self.local_sock.recv(BUF_SIZE)
            logging.debug('greeting: {}'.format(repr(greeting)))
            if not greeting:
                self.destroy('peer closed')
            if not greeting[0] == SOCKS_VER_5:
                self.destroy('not SOCKS5')
            self.data_to_local.append('\x05\x00')
            self.state = STATE_WAIT_FOR_CMD
        elif self.state == STATE_WAIT_FOR_CMD:
            cmd = self.local_sock.recv(BUF_SIZE)
            logging.debug('cmd: {}'.format(repr(cmd)))
            cmd_code = cmd[1]
            if cmd_code == '\x01': # establish TCP/IP stream connection
                pass
            elif cmd_code == '\x02': # establish TCP/IP port binding
                self.destroy('request for port binding not implemented')
                return
            elif cmd_code == '\x03': # associate UDP port
                self.destroy('request for UDP port assoc not implemented')
                return
            else:
                self.destroy('unknown command code {}'.format(cmd_code))
                return
            addr_type = cmd[3]
            if addr_type == '\x01': # IPv4 address
                port_index = 8
                host = '.'.join(str(int(struct.unpack('!B', byte)[0]))
                                for byte in cmd[4:port_index])
            elif addr_type == '\x03': # domain name
                name_len = int(struct.unpack('!B', cmd[4])[0])
                port_index = 5 + name_len
                host = cmd[5:port_index]
            else:
                self.destroy('unsupport address')
                return
            port = int(struct.unpack('!H', cmd[port_index:port_index+2])[0])
            logging.debug('request connect to {}:{}'.format(host, port))
            sock = socket.socket()
            sock2handler[sock] = self
            sock.setblocking(0)
            rs.add(sock)
            ws.add(sock)
            xs.add(sock)
            self.remote_sock = sock
            self.state = STATE_RELAYING
            sock.connect_ex(config.server_addr)
            logging.debug('connect to server at {}'.format(config.server_addr))
        elif self.state == STATE_RELAYING:
            print 'state == relaying'
            data = self.local_sock.recv(BUF_SIZE)
            print 'relay', repr(data)
            self.data_to_remote.append(data)

    def on_remote_recv(self):
        data = self.remote_sock.recv(BUF_SIZE)
        data = decrypt(data)
        self.data_to_local.append(data)

    def destroy(self, msg=''):
        logging.debug('destroy {}: {}'.format(self, msg))
        self.local_sock.close()
        rs.discard(self.local_sock)
        ws.discard(self.local_sock)
        xs.discard(self.local_sock)
        sock2handler.pop(self.local_sock, None)
        if self.remote_sock:
            self.remote_sock.close()
            rs.discard(self.remote_sock)
            ws.discard(self.remote_sock)
            xs.discard(self.remote_sock)
            sock2handler.pop(self.remote_sock, None)

listen_addr = config.ip, config.port
lsock = socket.socket()
lsock.bind(listen_addr)
lsock.listen(1024)
logging.info('Listening on {}:{}'.format(*listen_addr))

rs, ws, xs = set([lsock]), set(), set()
sock2handler = {}
sock2handler[lsock] = Listener(lsock)

while True:
    r, w, x = select.select(rs, ws, xs, 1)
    #logging.debug('select {}'.format(map(len, [r, w, x])))
    for sock in r:
        sock2handler[sock].on_recv(sock)
    for sock in w:
        sock2handler[sock].on_send(sock)
    for sock in x:
        sock2handler[sock].on_error(sock)

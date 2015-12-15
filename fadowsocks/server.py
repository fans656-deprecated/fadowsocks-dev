import socket

import config_server as config

BUF_SIZE = 32 * 1024

listen_addr = config.ip, config.port

lsock = socket.socket()
lsock.bind(listen_addr)
lsock.listen(1024)
print 'listening at', listen_addr
while True:
    sock, addr = lsock.accept()
    print 'accept', addr
    while True:
        try:
            data = sock.recv(BUF_SIZE)
            if not data:
                sock.close()
            print repr(data)
        except Exception:
            pass
        finally:
            sock.close()
            print 'close 1 connection'

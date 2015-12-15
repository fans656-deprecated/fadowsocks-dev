import socket
from f6.socket import Listener
from common import encrypt, decrypt, parse_request_addr, BUF_SIZE
import config

l = Listener(config.server)
while True:
    sock, addr = l.accept()
    print 'accept', addr
    try:
        cmd = sock.recv(1024)
        cmd = decrypt(cmd)
        request_addr = parse_request_addr(cmd)
        print repr(cmd), request_addr
        sock.send('\x05\x00')
        print 'granted'
        data = sock.recv(1024)
        if not data:
            print 'closed', addr
            sock.close()
            rsock.close()
            continue
        data = decrypt(data)
        print 'proxy:', repr(data)
        rsock = socket.socket()
        rsock.connect(request_addr)
        rsock.send(data)
        respond = rsock.recv(BUF_SIZE)
        print 'respond:', repr(respond)
        respond = encrypt(respond)
        sock.send(respond)
    except Exception as e:
        print e
    finally:
        sock.close()
        print 'close', addr
        print

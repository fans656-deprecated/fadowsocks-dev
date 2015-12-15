import socket
from common import encrypt, decrypt, parse_request_addr, BUF_SIZE
import config

lsock = socket.socket()
lsock.bind(config.server)
lsock.listen(1024)
print 'listen at', lsock.getsockname()
while True:
    sock, addr = lsock.accept()
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

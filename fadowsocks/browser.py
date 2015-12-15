import socket
import struct
import time

domain_name = 'xiami.com'
by_domain = 1

def request_by_domain():
    data = (
        '\x05\x01\x00\x03' +
        struct.pack('!B', len(domain_name)) +
        domain_name +
        struct.pack('!H', 80))
    sock.send(data)

def request_by_ip():
    ip = socket.gethostbyname(domain_name)
    data = (
        '\x05\x01\x00\x01' +
        socket.inet_aton(ip) +
        struct.pack('!H', 80))
    sock.send(data)

sock = socket.socket()
sock.connect(('localhost', 6560))
sock.send('\x05\00')
sock.recv(1024) # greeting
if by_domain:
    request_by_domain()
else:
    request_by_ip()
sock.recv(1024) # grant
sock.send('HEAD / HTTP/1.1\r\nHost: {}\r\n\r\n'.format(domain_name))
data = sock.recv(1024)
print repr(data)

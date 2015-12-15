import socket
import struct

sock = socket.socket()
sock.connect(('localhost', 6560))
sock.send('\x05\x00')
sock.recv(2)
domain_name = 'www.google.com'
sock.send('\x05\x01\x00\x03' +
          struct.pack('!B', len(domain_name)) +
          domain_name +
          struct.pack('!H', 80))
s = sock.recv(1024)
print repr(s)
sock.send('HEAD / HTTP/1.1\r\nHost: baidu.com\r\n\r\n')
while True:
    data = sock.recv(1024)
    if not data:
        break
    for line in data.split('\n'):
        print line[:79]

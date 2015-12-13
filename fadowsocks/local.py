import socket
import struct

server_addr = ('104.224.168.15', 6569)

def method2name(method):
    try:
        return {
            '\x00': 'No authentication',
            '\x01': 'GSSAPI',
            '\x02': 'Username/Password',
        }[method]
    except KeyError:
        if '\x03' <= method <= '\x7f':
            return 'IANA assigned method'
        elif '\x80' <= method <= '\xfe':
            return 'Reserved method for private use'
        else:
            return 'Unknown'

def rot13(s, encrypt=True):
    direction = 1 if encrypt else -1
    return ''.join(chr((ord(c) + 256 + 13 * direction) % 256) for c in s)

def delegate_to_server(local_sock, domain_name, port):
    remote_sock = socket.socket()
    remote_sock.connect(server_addr)
    s = '\xf6'
    s += struct.pack('!B', len(domain_name))
    s += rot13(domain_name)
    s += rot13(struct.pack('!H', port))
    remote_sock.send(s)
    while True:
        data = local_sock.recv(1024)
        if not data:
            local_sock.close()
            remote_sock.close()
            break
        print '->', repr(data)
        data = rot13(data)
        print '.>', repr(data)
        remote_sock.send(data)
        data = remote_sock.recv(1024)
        if not data:
            local_sock.close()
            remote_sock.close()
            break
        print '<.', repr(data)
        data = rot13(data, False)
        print '<-', repr(data)
        local_sock.send(data)

lsock = socket.socket()
lsock.bind(('localhost', 6560))
lsock.listen(1024)
while True:
    sock, addr = lsock.accept()
    print 'accept', addr
    socks_ver = sock.recv(1)
    if socks_ver != '\x05':
        sock.close()
        continue
    print 'got SOCKS5 greeting'
    n_methods = int(struct.unpack('!B', sock.recv(1))[0])
    if n_methods:
        methods = sock.recv(n_methods)
        print 'Method supported by client:'
        for method in methods:
            print ' ' * 4, method2name(method)
    sock.send('\x05\x00')
    socks_ver = sock.recv(1)
    cmd = sock.recv(1)
    if cmd == '\x01':
        print 'establish a TCP/IP stream connection'
    elif cmd == '\x02':
        print 'establish a TCP/IP port binding'
    elif cmd == '\x03':
        print 'associate a UDP port'
    reserved = sock.recv(1)
    addr_type = sock.recv(1)
    if addr_type == '\x01':
        print 'IPv4 address'
        break
    elif addr_type == '\x03':
        print 'Domain name'
        name_len = int(struct.unpack('!B', sock.recv(1))[0])
        domain_name = sock.recv(name_len)
        print 'Domain name:', domain_name
    elif addr_type == '\x04':
        print 'IPv6 address'
        break
    port = int(struct.unpack('!H', sock.recv(2))[0])
    print 'Port:', port
    sock.send('\x05\x00\x00\x01' + '\x00' * 6)
    print 'granted, delegate to server', server_addr
    try:
        delegate_to_server(sock, domain_name, port)
    except Exception:
        pass

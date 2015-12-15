import socket
import struct

BUF_SIZE = 32 * 1024

def parse_request_addr(cmd):
    cmd_code = cmd[1]
    if cmd_code == '\x01': # TCP connection
        addr_type = cmd[3]
        if addr_type == '\x01': # IPv4
            port_index = 8
            host = cmd[4:port_index]
            host = socket.inet_ntoa(host)
        elif addr_type == '\x03': # domain name
            name_len = int(struct.unpack('!B', cmd[4])[0])
            port_index = 5 + name_len
            host = cmd[5:port_index]
        elif addr_type == '\x04': # IPv6
            raise NotImplementedError('IPv6 address type')
        else:
            raise NotImplementedError('unknown address type')
        port = int(struct.unpack('!H', cmd[port_index:port_index+2])[0])
        return host, port
    elif cmd_code == '\x02': # TCP port binding
        raise NotImplementedError('tcp port binding')
    elif cmd_code == '\x03': # associate UDP port
        raise NotImplementedError('udp port')
    else:
        raise NotImplementedError('unknown command')

def encrypt(data):
    return ''.join(chr((ord(ch) + 1) % 256) for ch in data)

def decrypt(data):
    return ''.join(chr((ord(ch) + 256 - 1) % 256) for ch in data)

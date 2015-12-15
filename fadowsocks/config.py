import os

vps = os.environ.get('bandwagon', False)

if vps:
    host = os.environ.get('vps', 'localhost')
else:
    host = 'localhost'
server = (host, 6569)

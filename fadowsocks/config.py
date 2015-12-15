import os

local = os.environ.get('bandwagon', False)

if local:
    host = 'localhost'
else:
    host = os.environ.get('vps', 'localhost')
server = (host, 6569)

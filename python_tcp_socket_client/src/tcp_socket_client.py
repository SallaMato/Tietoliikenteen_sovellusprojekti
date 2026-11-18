import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('172.20.241.9', 20000))
s.sendall(b'56\n')

chunks = []
while True:
    data = s.recv(1024)
    if len(data) == 0:
        break
    chunks.append(data.decode('utf-8'))

for i in chunks:
    print(i, end = '')

s.close()

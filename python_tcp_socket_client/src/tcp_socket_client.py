import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('172.20.241.9', 20000))
s.sendall(b'4\n')

chunks = []
while True:
    data = s.recv(1024)
    if len(data) == 0:
        print("data len was 0")
        break
    chunks.append(data.decode('utf-8'))

for i in chunks:
    print(i, end = '')

filename = f"mittausdata.txt"

with open(filename, "w", encoding="utf-8") as f:
    f.writelines(chunks)

s.close()

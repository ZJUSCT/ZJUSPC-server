from clientBase import ClientBase
import json

# host = "172.25.2.1"
# port = 8080
host = "127.0.0.1"
port = 1122
buffsize = 2048

class Client(ClientBase):
	def __init__(self, inputFromStd = False, host = host, port = port, buffsize = buffsize):
		super(Client, self).__init__(inputFromStd, host, port, buffsize)
	def onMessage(self, msg):
		print(msg)

if __name__ == "__main__":
	c = Client()
	c.work()
from socket import*
import threading
import os

class ClientBase:
	def __init__(self, host, port, buffsize):
		self.host = host
		self.port = port
		self.buffsize = buffsize
		self.s = socket(AF_INET, SOCK_STREAM)
		self.s.connect((host, port))
		threading._start_new_thread(self.messenger, ())
	def messenger(self):	# listener(node)
		while True:
			try:
				data = self.s.recv(self.buffsize)
			except:
				print("server has been terminated!")
				os._exit()
			self.onMessage(data.decode("utf8"))
	def send(self, msg):
		self.s.send(msg.encode("utf8"))
	# virtual method
	def onMessage(self, msg):
		pass
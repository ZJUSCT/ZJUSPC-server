from socket import*
import threading

class ClusterBase:
	def __init__(self, host, port, buffsize):
		self.host = host
		self.port = port
		self.buffsize = buffsize
		self.s = socket(AF_INET, SOCK_STREAM)
		self.s.bind((host, port))
		self.s.listen(7)
		self.nodes = []
		# self.connectNodes()
		threading._start_new_thread(self.connector, ())
	def connector(self):
		while True:
			node, addr = self.s.accept()
			self.onConnect(node)
			self.nodes.append(node)
			threading._start_new_thread(self.messenger, (node,))
			print("connetction established:", addr)
	def disconnector(self, node):
		self.onDisconnect(node)
		self.nodes.remove(node)
		print("connection lost!")
	def messenger(self, node):	# listener(node)
		while True:
			try:
				data = node.recv(self.buffsize)
			except:
				self.disconnector(node)
				return
			self.onMessage(data.decode("utf8"))
	def broadcast(self, msg):
		for node in self.nodes:
			node.send(msg.encode("utf8"))
	# virtual method
	def onMessage(self, msg):
		pass
	def onConnect(self, node):
		pass
	def onDisconnect(self, node):
		pass
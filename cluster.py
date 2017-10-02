import json
import threading
import time
from clusterBase import ClusterBase
import copy

host = "172.25.2.1"
port = 8087
#host = ""
#port = 1122
buffsize = 2048

class Queue:
	def __init__(self):
		self.data = []
	def put(self, x):
		self.data.append(x)
	def get(self):
		item = self.data[0]
		self.data = self.data[1:]
		return item
	def empty(self):
		return len(self.data) == 0

class Cluster(ClusterBase):
	def __init__(self, host = host, port = port, buffsize = buffsize):
		super(Cluster, self).__init__(host, port, buffsize)
		self.time = ""
		self.nextInfo = {}
		self.data = {"nodes":{}}
		self.mutex = threading.Lock()
		self.mutex.acquire(0)
		self.infoLock = threading.Lock()
		self.listLock = threading.Lock()
		self.msgList = Queue()
	def onMessage(self, msg, node):
		try:
			msg = json.loads(msg)
		except:	# node died
			return
		#print(msg)
		if "sys" in msg:
			if self.infoLock.acquire():
				self.nextInfo[msg["node"]] = {
					"msg": msg,
					"socket": node,
				}
				self.infoLock.release()
		else:
			time = msg["time"]
			#print("received status at", time)
			if self.time and time != self.time:		# new second
				self.data["time"] = time
				if self.listLock.acquire():
					self.data["info"] = {}
					if self.infoLock.acquire():
						for x in self.nextInfo:
							self.data["info"][x] = self.nextInfo[x]["msg"]
						self.infoLock.release()
					self.msgList.put(copy.copy(self.data))
					self.listLock.release()
				#self.data["time"] = time
				self.time = time
				self.data = {"nodes":{}}
				if not self.mutex.acquire(0):
					self.mutex.release()
			self.time = time
			self.data["nodes"][msg["node"]] = msg
			#self.data["nodes"][msg["node"]] = [
			#	100 - float(msg["CPU"]["%idle"]),
			#	float(msg["memory"]["%memused"])
			#]
	def onDisconnect(self, node):
		if self.infoLock.acquire():
			for x in self.nextInfo:
				if self.nextInfo[x]["socket"] == node:
					print("node", x, "closed connection")
					del self.nextInfo[x]
					break
			self.infoLock.release()

if __name__ == "__main__":
	c = Cluster()
	while True:
		s = input(">")
		c.broadcast(s)

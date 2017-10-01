import json
from clusterBase import ClusterBase

# host = "172.25.2.1"
# port = 8080
host = ""
port = 1122
buffsize = 2048

class DataGen:
	def __init__(self):
		self.data = [
			[67, 25, 49, 12],
			[100, 34, 86, 13],
			[],
			[1, 12, 21, 67],
			[],
			# if node not running then put a []
		]
	def getData(self):
		import random
		for i in range(0, len(self.data)):
			for j in range(0, len(self.data[i])):
				self.data[i][j] = (self.data[i][j] + random.randrange(-10, 10)) % 100
		from copy import deepcopy as cp
		return cp(self.data)
dataGen = DataGen()

class Cluster(ClusterBase):
	def __init__(self, host = host, port = port, buffsize = buffsize):
		super(Cluster, self).__init__(host, port, buffsize)
	def onMessage(self, msg):
		print(msg)
	# def connectNodes(self):
		# pass
	def getStatus(self):
		# msg = json.dumps({"acquire": ["status"]})
		# self.broadcast(msg)
		return dataGen.getData()
	def getNodes(self):
		return ["cpu00", "cpu01", "cpu02", "gpu00", "mic00"]

if __name__ == "__main__":
	c = Cluster()
	while True:
		s = input(">")
		c.broadcast(s)
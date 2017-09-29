import sys
import signal
import ssl
import time
import json
import struct
from copy import deepcopy as cp
import threading
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket, SimpleSSLWebSocketServer
from optparse import OptionParser

clients = []

interval = 1
port = 7194
maxLen = 61

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
		return cp(self.data)
dataGen = DataGen()

def getNodes():
	return ["cpu00", "cpu01", "cpu02", "gpu00", "mic00"]

class Cluster:
	def __init__(self):
		# start the server!
		self.nodeList = getNodes()
		self.data = [[[[], ""] for x in range(0, maxLen)] for y in range(0, len(self.nodeList))]
		# [
		# 	[
		# 		[[],], [], [], [], [] #maxLen (time)
		# 	], #node0
		# 	[
		# 		[], [], [], [], []
		# 	], #node1
		# 	[
		# 		[], [], [], [], []
		# 	], #node2
		# ]
		# id for node, id.id for time
		self.getStatus()

	def getStatus(self):
		self.currentStatus = dataGen.getData()
		for i in range(0, len(self.nodeList)):
			del self.data[i][0]
			self.data[i].append([self.currentStatus[i], str(time.time())])
		return self.currentStatus

	def getInit(self):
		return {
			"head": self.nodeList,
			"status": self.currentStatus
		}

cluster = Cluster()

def dispatchData():
	status = cluster.getStatus()
	# keep fetching data for log and next connection
	for client in clients:
		client.sendMessage(json.dumps({
			"basis": status,
			"process": [
				[3187, "pts/0", "00:00:00", "bash"],
				[3353, "pts/0", "00:00:00", "ps"],
			]
		}))
	t = threading.Timer(interval, dispatchData)
	t.start()

class ZJUSPCServer(WebSocket):
	def handleMessage(self):
		self.data = json.loads(self.data)
		msg = { "extra": {} } # sending extra package on server receive..
		if "node" in self.data:
			msg["extra"]["presentStatus"] = cluster.data[int(self.data["node"])]
		if "viewState" in self.data:
			pass
		self.sendMessage(json.dumps(msg))
		# for client in clients:
		# 	if client != self:
		# 		client.sendMessage(self.address[0] + u" - " + self.data)

	def handleConnected(self):
		print(self.address, "connected")
		clients.append(self)
		self.sendMessage(json.dumps({
			"init": cluster.getInit(),
			"basis": cluster.currentStatus,
		}))

	def handleClose(self):
		clients.remove(self)
		print(self.address, "closed")
	
if __name__ == "__main__":
	global server

	parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
	parser.add_option("--host", default="", type="string", action="store", dest="host", help="hostname (localhost)")
	parser.add_option("--port", default=port, type="int", action="store", dest="port", help="port (8000)")
	parser.add_option("--ssl", default=0, type="int", action="store", dest="ssl", help="ssl (1: on, 0: off (default))")
	parser.add_option("--cert", default="./cert.pem", type="string", action="store", dest="cert", help="cert (./cert.pem)")
	parser.add_option("--key", default="./key.pem", type="string", action="store", dest="key", help="key (./key.pem)")
	parser.add_option("--ver", default=ssl.PROTOCOL_TLSv1, type=int, action="store", dest="ver", help="ssl version")

	(options, args) = parser.parse_args()

	if options.ssl == 1:
		server = SimpleSSLWebSocketServer(options.host, options.port, ZJUSPCServer, options.cert, options.key, version=options.ver)
	else:
		server = SimpleWebSocketServer(options.host, options.port, ZJUSPCServer)

	def close_sig_handler(signal, frame):
		server.close()
		sys.exit()

	signal.signal(signal.SIGINT, close_sig_handler)

	t = threading.Timer(interval, dispatchData)
	t.start()
	server.serveforever()
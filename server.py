import sys
import signal
import ssl
import time
import json
import struct
import threading
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket, SimpleSSLWebSocketServer
from optparse import OptionParser

from cluster import Cluster

host = "10.78.18.246"
#host = "10.78.18.247"
port = 8087
#port = 8080
#host = ""
#port = 8087

clients = []
interval = 1
diff = 0.07
maxLen = 61

class ClusterInterface:
	def __init__(self):
		self.cluster = Cluster()
		self.nodeList = {}
		self.nodeInfo = []
		self.data = []
	def updateNodeInfo(self, info):
		i = 0
		self.nodeInfo = info
		self.data = [None for x in info]
		for x in info:
			if x not in self.nodeList:
				#print("added", x)
				self.nodeList[x] = [
					[
						[], ""
					] for y in range(0, maxLen)
				]
			self.data[i] = self.nodeList[x]
			i += 1
	def getStatus(self):
		print("listening...")
		if self.cluster.mutex.acquire(True, interval + diff):
			print("sdasd")
			if self.cluster.listLock.acquire():
				item = self.cluster.msgList.get()
				if not self.cluster.msgList.empty():
					self.cluster.mutex.release()
				self.cluster.listLock.release()
			print("get status")
		else:
			item = {"nodes":{}, "info":{}}
			print("get nothing")
		return item
	def getInit(self):
		return [self.status["info"][x] for x in self.status["info"]]
	def dispatchData(self):
		while True:
			# info = self.pullNodeInfo()
			self.status = self.getStatus()
			# keep fetching data for log and next connection
			data = {
				"time": self.status["time"] if "time" in self.status else "??:??:??",
				#"process": [
				#	[3187, "pts/0", "00:00:00", "bash"],
				#	[3353, "pts/0", "00:00:00", "ps"],
				#]
			}
			nodeInfo = [x for x in self.status["info"]]
			if nodeInfo != self.nodeInfo:
				self.updateNodeInfo(nodeInfo)
				data["init"] = self.getInit()
			data["basis"] = self.getBasis()
			print(data)
			for client in clients:
				client.sendMessage(json.dumps(data))
	def getBasis(self):
		return [
			[
				100 - float(self.status["nodes"][x]["CPU"]["%idle"]),
				float(self.status["nodes"][x]["memory"]["%memused"])
			] if x in self.status["nodes"] else [] 
				for x in self.nodeInfo
		]

cluster = ClusterInterface()

class ZJUSPCServer(WebSocket):
	def handleMessage(self):
		self.data = json.loads(self.data)
		print("received: ", self.data)
		msg = { "extra": {} } # sending extra package on server receive..
		if "node" in self.data:
			msg["extra"]["presentStatus"] = cluster.data[int(self.data["node"])]
		if "viewState" in self.data:
			pass
		#print(msg)
		self.sendMessage(json.dumps(msg))
		# for client in clients:
		# 	if client != self:
		# 		client.sendMessage(self.address[0] + u" - " + self.data)

	def handleConnected(self):
		print(self.address, "connected")
		clients.append(self)
		self.sendMessage(json.dumps({
			"init": cluster.getInit(),
			"basis": cluster.getBasis(),
		}))

	def handleClose(self):
		clients.remove(self)
		print(self.address, "closed")
	
if __name__ == "__main__":
	global server

	parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
	parser.add_option("--host", default=host, type="string", action="store", dest="host", help="hostname (localhost)")
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
	
	threading._start_new_thread(cluster.dispatchData, ())
	print("start server")
	server.serveforever()

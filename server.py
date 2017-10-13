import sys
import signal
import ssl
import time
import json
import struct
import threading
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket, SimpleSSLWebSocketServer
from optparse import OptionParser

from cluster import Cluster, countInterval

host = "10.78.18.246"
#host = "10.78.18.247"
port = 8087
#port = 8080
#host = ""
#port = 8087

clients = []
interval = 1 * countInterval
diff = 0.25 * countInterval
maxLen = 61

class ClusterInterface:
	def __init__(self):
		self.cluster = Cluster()
		self.nodeList = {}
		self.nodeInfo = []
		self.data = []
	def updateNodeInfo(self, info):
		print("update node info")
		i = 0
		self.nodeInfo = info
		self.data = [None for x in info]
		for x in info:
			if x not in self.nodeList:
				#print("added", x)
				self.nodeList[x] = [
					[
						[
							-1,
							-1,
							-1,
						], "Server not started"
					] for y in range(0, maxLen)
				]
			self.data[i] = self.nodeList[x]
			i += 1
		print("info:",info)
	def getClusterStatus(self):
		if self.cluster.listLock.acquire():
			#print(self.cluster.msgList.data)
			item = self.cluster.msgList.get()
			if not self.cluster.msgList.empty():
				self.cluster.mutex.release()
			else:
				self.cluster.mutex.acquire(0)
			self.cluster.listLock.release()
		return item
	def getStatus(self):
		if self.cluster.mutex.acquire(True, interval + diff):
			item = self.getClusterStatus()
			self.cluster.deleteLock.acquire(0)
			self.cluster.deleteLock.release()
		else:
			if not self.cluster.deleteLock.acquire(0):
				self.cluster.updateData(self.cluster.time)
				item = self.getClusterStatus()
			elif self.cluster.interval == 1:
				item = self.cluster.data
				item["info"] = {}
				if self.cluster.infoLock.acquire():
					for x in self.cluster.nextInfo:
						item["info"][x] = self.cluster.nextInfo[x]["msg"]
						self.cluster.infoLock.release()
				item["time"] = self.cluster.time
			else:
				item = {"nodes":{}, "info":{}, "time":""}
			self.cluster.deleteLock.release()
		return item
	def getInit(self):
		return {
			"head": [self.status["info"][x] for x in self.status["info"]],
			#"data": self.data
		}
	def dispatchData(self):
		while True:
			# info = self.pullNodeInfo()
			self.status = self.getStatus()
		#	print(self.status)
			#print(self.status)
			# keep fetching data for log and next connection
			data = {
				"time": self.status["time"] if "time" in self.status else "",
				"extra": {},
				"process": {},
				#"process": [
				#	[3187, "pts/0", "00:00:00", "bash"],
				#	[3353, "pts/0", "00:00:00", "ps"],
				#]
			}
			#print(self.status)
			nodeInfo = [x for x in self.status["info"]]
			if nodeInfo != self.nodeInfo:
				self.updateNodeInfo(nodeInfo)
				data["init"] = self.getInit()
			data["basis"] = self.getBasis()
			for client in clients:
				client.processMessage(data)
				#client.sendMessage(json.dumps(data))
			for x in self.nodeList:
				del self.nodeList[x][0]
				self.nodeList[x].append([self.genBasis(x), self.status["time"]])
	def genBasis(self, x):
		return [
			float(self.status["nodes"][x]["CPU"]["ldavg-1"]),
			float(self.status["nodes"][x]["memory"]["kbmemused"]) / 1048576.0,
			float(self.status["nodes"][x]["memory"]["%memused"]),
		] if x in self.status["nodes"] else [
			-1,
			-1,
			-1,
		] 
	def getBasis(self):
		return [
			self.genBasis(x) for x in self.nodeInfo
		]

cluster = ClusterInterface()

class ZJUSPCServer(WebSocket):
	def __init__(self, *args):
		super(ZJUSPCServer, self).__init__(*args)
		self.node = None
		self.viewState = None
	def handleMessage(self):
		self.data = json.loads(self.data)
		print("received: ", self.data)
		msg = { "extra": {}, "process": {} } # sending extra package on server receive..
		if "node" in self.data:
			msg["extra"]["presentStatus"] = cluster.data[int(self.data["node"])]
			self.node = self.data["node"]
		if "viewState" in self.data:
			self.viewState = self.data["viewState"]
		self.processMessage(msg)
	def modifyCPU(self, node, msg):
		msg["extra"]["CPU"] = cluster.status["nodes"][node]["CPU"] if node in cluster.status["nodes"] else {}
	def modifyMemory(self, node, msg):
		msg["extra"]["memory"] = cluster.status["nodes"][node]["memory"] if node in cluster.status["nodes"] else {}
	def modifyGPU(self, node, msg):
		msg["extra"]["GPU"] = cluster.status["nodes"][node]["GPU"] if node in cluster.status["nodes"] else {}
	def modifyTemp(self, node, msg):
		msg["extra"]["temperature"] = cluster.status["nodes"][node]["temperature"] if node in cluster.status["nodes"] else {}
	def modifyProcess(self, node, msg):
		msg["process"] = cluster.status["nodes"][node]["process"] if node in cluster.status["nodes"] else {}
	def processMessage(self, msg):
		if self.node is not None:
			if int(self.node) < len(cluster.nodeInfo):
				nodeName = cluster.nodeInfo[int(self.node)]
				{
					"CPU": self.modifyCPU,
					"memory": self.modifyMemory,
					"GPU": self.modifyGPU,
					"temperature": self.modifyTemp,
					"process": self.modifyProcess,
				}.get(self.viewState, lambda a,b: 0)(nodeName, msg)
		#print(msg)
		self.sendMessage(json.dumps(msg))
	def handleConnected(self):
		print(self.address, "connected")
		clients.append(self)
		msg = {
			"init": cluster.getInit(),
			"basis": cluster.getBasis(),
			"extra": {},
			"process": {},
		}
		self.processMessage(msg)
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

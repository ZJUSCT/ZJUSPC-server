import sys
import signal
import ssl
import json
import struct
import threading
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from optparse import OptionParser

clients = []

interval = 1

import random
test = {
	"data": [
		[67, 25, 49],
		[100, 34, 86],
		[1, 12, 21],
	]
}

def getClusterStatus():
	for i in range(0, len(test["data"])):
		for j in range(0, len(test["data"][i])):
			test["data"][i][j] += random.randrange(-5, 5)
	return test["data"]

def dispatchData():
	if len(clients) > 0:
		data = getClusterStatus()
		for client in clients:
			client.sendMessage(json.dumps(data))
	t = threading.Timer(interval, dispatchData)
	t.start()

class ZJUSPCServer(WebSocket):
	def handleMessage(self):
		pass
		# for client in clients:
		# 	if client != self:
		# 		client.sendMessage(self.address[0] + u" - " + self.data)

	def handleConnected(self):
		print self.address, "connected"
		clients.append(self)
		self.sendMessage(json.dumps({
			"nodesInit": ["N1", "N2", "N3"],
		}))

	def handleClose(self):
		clients.remove(self)
		print self.address, "closed"
	
if __name__ == "__main__":
	global server

	parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
	parser.add_option("--host", default="", type="string", action="store", dest="host", help="hostname (localhost)")
	parser.add_option("--port", default=8000, type="int", action="store", dest="port", help="port (8000)")
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
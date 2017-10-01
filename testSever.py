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

host = "10.78.18.246"
port = 4052

class Server(WebSocket):
	def handleMessage(self):
		print(self.message)
	def handleConnected(self):
		print(self.address, "connected")
	def handleClose(self):
		print(self.address, "closed")

if __name__ == "__main__":
	global server 
	server = SimpleWebSocketServer(host, port, Server)
	server.serveforever()
from clientBase import ClientBase
import json
import threading
from functools import reduce
import os
import re
import shlex
import subprocess

host = "172.25.2.1"
port = 8087
#host = "127.0.0.1"
#port = 1122
buffsize = 2048

cmd = ["sar -uqrR -m CPU -m TEMP 1", "nohup nvidia-smi -l 1", "python ipmi.py", "top -d 1 -bic -w 1048576"]
cmd = list(map(shlex.split, cmd))

class Client(ClientBase):
	def __init__(self, host = host, port = port, buffsize = buffsize):
		super(Client, self).__init__(host, port, buffsize)
		self.procs = [
			processCPU,
			processMpg,
			processMem,
			processLd,
			processCPUF,
			processTemp
		]
		self.initMsg()
	def initMsg(self):
		self.grp = 0
		self.msg = {
			"CPU": {},
			"memory": {},
			"temperature": {},
			"GPU": {},
			"process": {},
		}
	def onMessage(self, msg):
		pass
		# self.send(data)
	def handleSmi(self, p):
		#print(self)
		line = p.stdout.readline().decode("utf8").strip()
		lines = []
		while line != "":
			line = p.stdout.readline().decode("utf8").strip()
			lines.append(line)
		nGPU = int((len(lines) - 7) / 3)
		for x in range(0, nGPU):
			l1 = re.findall(r"^\|\s+\S+\s+([^\|]+)\|\s+(\S+)\s+(\S+)\s+\|\s+(\S+)", lines[3 * x + 6])[0]
			g = re.findall(r"(\S+)", l1[0])
			l1 = [reduce(lambda a,b:a+" "+b, g[0:-1]), g[-1]] + [l1[i] for i in range(1, len(l1))]
			l2 = re.findall(r"^\|\s+(\S+)\s+(\S+)\s+(\S+)\s+([^\|]+)\|\s+([^\|]+)\|\s+(\S+)\s+(\S+)", lines[3 * x + 7])[0]
			self.msg["GPU"][str(x)] = {
				"Fan": l2[0],
				"Temp": l2[1],
				"Name": l1[0],
				"Perf": l2[2],
				"Pwr:Usage/Cap": l2[3],
				"Memory-Usage": l2[4],
				"Persistence-M": l1[2],
				"Bus-Id": l1[3],
				"Disp.A": l1[3],
				"Volatile Uncorr. ECC": l1[4],
				"GPU-Util": l2[5],
				"Compute M.": l2[6]
			}
		for i in range(0, 5):
			line = p.stdout.readline().decode("utf8").strip()
		while line[0] != "+":
			line = p.stdout.readline().decode("utf8").strip()
		#print(self.msg)
	def initSmi(self, p):
		line = p.stdout.readline().decode("utf8").strip()
	def handleSar(self, p):
		line = p.stdout.readline().decode("utf8").strip()
		if self.grp >= len(self.procs):
			self.msg["time"] = re.findall(r"(\S+)\s", line)[0]
			if re.findall(r"(\S+)\s+", line)[1] == "PM":
				tl = re.findall(r"([0-9]+)", self.msg["time"])
				tl[0] = str(int(tl[0]) + 12)
				self.msg["time"] = str(tl[0]) + ":" + str(tl[1]) + ":" + str(tl[2])
			self.msg["node"] = node
			self.send(json.dumps(self.msg))
			self.initMsg()
		line = p.stdout.readline().decode("utf8").strip()
		func = self.procs[self.grp]
		while line:
			#print(line)
			func(line, self.msg)
			line = p.stdout.readline().decode("utf8").strip()
		self.grp += 1
	def initSar(self, p):
		line = p.stdout.readline().decode("utf8").strip()
		info = re.findall(r"^([^\(]+)\(([^\)]+)\)[^\(]*\((\S+)", line)[0]
		line = p.stdout.readline().decode("utf8").strip()
		global node
		sys, node, ncpu = info
		self.send(json.dumps({
			"sys": sys,
			"node": node,
			"ncpu": ncpu,
		}))
	def initIpmi(self, p):
		line = p.stdout.readline().decode("utf8").strip()
	def handleIpmi(self, p):
		line = p.stdout.readline().decode("utf8").strip()
		info = []
		while line[:3] != "QvQ":
			info.append(line)
			line = p.stdout.readline().decode("utf8").strip()
		def simpleSplit(l):
			a=list(map(str.strip, l.split('|')))
			return a[:2]
		self.msg["temperature"] = dict(map(simpleSplit, info))
	def initTop(self, p):
		pass
	def handleTop(self, p):
		for i in range(0, 8):
			line = p.stdout.readline().decode("utf8").strip()
		lines = []
		while line != "":
			lines.append(line)
			line = p.stdout.readline().decode("utf8").strip()
		def splitter(l):
			return re.findall(r"^\s*(\S+)\s*(\S+)\s*(\S+)\s*(\S+)\s*(\S+)\s*(\S+)\s*(\S+)\s*(\S+)\s*(\S+)\s*(\S+)\s*(\S+)\s*(.+)", l)[0]
		lines = list(map(splitter, lines))
		self.msg["process"] = lines
	
def processCPU(line, msg):
	l = re.findall(r"(\S+)", line)
	#print(l)
	msg["CPU"]["%user"] = l[3]
	msg["CPU"]["%nice"] = l[4]
	msg["CPU"]["%system"] = l[5]
	msg["CPU"]["%iowait"] = l[6]
	msg["CPU"]["%steal"] = l[7]
	msg["CPU"]["%idle"] = l[8]
def processMpg(line, msg):
	l = re.findall(r"(\S+)", line)
	msg["memory"]["frmpg/s"] = l[2]
	msg["memory"]["bufpg/s"] = l[3]
	msg["memory"]["campg/s"] = l[4]
def processMem(line, msg):
	l = re.findall(r"(\S+)", line)
	msg["memory"]["kbmemfree"] = l[2]
	msg["memory"]["kbmemused"] = l[3]
	msg["memory"]["%memused"] = l[4]
	msg["memory"]["kbbuffers"] = l[5]
	msg["memory"]["kbcached"] = l[6]
	msg["memory"]["kbcommit"] = l[7]
	msg["memory"]["%commit"] = l[8]
	msg["memory"]["kbactive"] = l[9]
def processLd(line, msg):
	l = re.findall(r"(\S+)", line)
	msg["CPU"]["runq-sz"] = l[2]
	msg["CPU"]["plist-sz"] = l[3]
	msg["CPU"]["ldavg-1"] = l[4]
	msg["CPU"]["ldavg-5"] = l[5]
	msg["CPU"]["ldavg-15"] = l[6]
	msg["CPU"]["blocked"] = l[7]
def processCPUF(line, msg):
	l = re.findall(r"(\S+)", line)
	msg["CPU"]["MHz"] = l[3]
def processTemp(line, msg):
	l = re.findall(r"(\S+)", line)
	#

handleFunc = [Client.handleSar, Client.handleSmi, Client.handleIpmi, Client.handleTop]
initFunc = [Client.initSar, Client.initSmi, Client.initIpmi, Client.initTop]

def infLoop(fn, *args):
	while True:
		fn(*args)

if __name__ == "__main__":
	c = Client()
	p = []
	for l in cmd:
		try:
			p.append(subprocess.Popen(l, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT))
		except Exception as e:
			p.append(None)
	for i in range(0, len(cmd)):
		initFunc[i](c, p[i])
	for i in range(1, len(cmd)):
		if p[i] is not None:
			threading._start_new_thread(
				infLoop,
				(lambda i:(handleFunc[i], c, p[i]))(i)
			)
	if p[0] is not None:
		infLoop(handleFunc[0], c, p[0])
	#while True:
		#for x in node.
		#c.sendNodeMessage(p)

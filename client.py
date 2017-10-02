from clientBase import ClientBase
import json
import os
import re
import shlex
import subprocess

host = "172.25.2.1"
port = 8087
#host = "127.0.0.1"
#port = 1122
buffsize = 2048

cmd = "sar -uqrR -m CPU -m TEMP 1"
cmd = shlex.split(cmd)

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
			"load": {},
			"temperature": {},
			"GPU": {},
		}
	def onMessage(self, msg):
		pass
		# self.send(data)
	def sendNodeMessage(self, p):
		line = p.stdout.readline().decode("utf8").strip()
		if self.grp >= len(self.procs):
			self.msg["time"] = re.findall(r"(\S+)\s", line)[0]
			if re.findall(r"(\S+)\s+", line)[1] == "PM":
				tl = re.findall(r"([0-9]+)", self.msg["time"])
				tl[0] = str(int(tl[0]) + 12)
				self.msg["time"] = str(tl[0]) + ":" + str(tl[1]) + ":" + str(tl[2])
			self.msg["node"] = node
			self.msg["nCPU"] = cpu
			self.send(json.dumps(self.msg))
			self.initMsg()
		line = p.stdout.readline().decode("utf8").strip()
		func = self.procs[self.grp]
		while line:
			#print(line)
			func(line, self.msg)
			line = p.stdout.readline().decode("utf8").strip()
		self.grp += 1
	def reportNodeInfo(self, sys, node):
		self.send(json.dumps({
			"sys": sys,
			"node": node
		}))
	
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
	msg["load"]["runq-sz"] = l[2]
	msg["load"]["plist-sz"] = l[3]
	msg["load"]["ldavg-1"] = l[4]
	msg["load"]["ldavg-5"] = l[5]
	msg["load"]["ldavg-15"] = l[6]
	msg["load"]["blocked"] = l[7]
def processCPUF(line, msg):
	l = re.findall(r"(\S+)", line)
	msg["CPU"]["MHz"] = l[3]
def processTemp(line, msg):
	l = re.findall(r"(\S+)", line)
	#

if __name__ == "__main__":
	c = Client()
	p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	line = p.stdout.readline().decode("utf8").strip()
	info = re.findall(r"^([^\(]+)\(([^\)]+)\)[^\(]*\((\S+)", line)[0]
	global sys, node, cpu
	sys, node, cpu = info
	c.reportNodeInfo(sys, node)
	line = p.stdout.readline().decode("utf8").strip()
	while True:
		c.sendNodeMessage(p)

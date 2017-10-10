import sys
import subprocess
from threading import Timer as timer

cmd = ["ipmitool", "sensor"]

def ipmi():
	print("QvQ")
	info = subprocess.check_output(cmd).decode('utf-8')
	for l in info.splitlines():
		if 'degrees C' in l:
			print(l)
	sys.stdout.flush()
	t = timer(0.2, ipmi)
	t.start()

t = timer(0.2, ipmi)
t.start()
#while True:
#	pass

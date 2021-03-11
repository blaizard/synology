#!/usr/bin/python3
# -*- coding: iso-8859-15 -*-

import os
import json
import re
import subprocess
import time
from datetime import datetime

# Note: the followign should be added to ~/.ssh/config
# in order to prevent disconnection.
# Host *
# ServerAliveInterval 120
#
# Also to access the server from external IP, use the followng option in
# /etc/ssh/sshd_config
# GatewayPorts yes
#
# Also install netstat on the remote server (apt-get install net-tools)
#
# After all of this, delete pending connections and restart sshd daemon (service sshd restart)

CURRENT_DIRECTORY_PATH = os.path.realpath(os.path.dirname(__file__))
PATH_LOG = os.path.join(CURRENT_DIRECTORY_PATH, "bridge.log")
PATH_CONFIG = os.path.join(CURRENT_DIRECTORY_PATH, ".bridge.json")

"""
Execute process
"""
def shell(command, noWait=False):
	proc = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	if noWait:
		time. sleep(2)

	if proc.poll() or noWait == False:
		(stdout, stderr) = proc.communicate()
		exitCode = proc.returncode
		if exitCode != 0:
			raise Exception(stderr)
		return stdout

	return ""

"""
Add entry to the log
"""
def logPrint(action, message):
	entry = "[%s] [%s] %s" % (str(datetime.now()), action.upper(), message)
	entry = entry.replace("\n", " ").replace("\r", "")
	with open(PATH_LOG, "a") as f:
		f.write(entry + "\n")
	print(entry)

if __name__ == '__main__':

	config = {
		"ports": [
			# List of ports to be forwarded.
			# Should be written either as a list of port numbers or a string delimited
			# by ":" specifiyng the port mapping.
		],
		# Authentication used for the SSH command
		"auth": "admin@myserver.com"
	}

	try:
	
		# Load the configuration
		if not os.path.exists(PATH_CONFIG):
			with open(PATH_CONFIG, "w") as f:
				f.write(json.dumps(config, sort_keys=True, indent=4, separators=(',', ': ')))
		with open(PATH_CONFIG, "r") as f:
			configUser = json.load(f)
			config.update(configUser)
	
		# Generate the ssh command to connect to the target
		command = ["ssh", "-o", "StrictHostKeyChecking no", "-nfNT"] + config["auth"]
		for port in config["ports"]:
			portList = str(port).split(":")
			assert len(portList) <= 2, "Wrong format for port '%s'" % (str(port))
			srcPort = portList[0]
			dstPort = portList[1] if len(portList) == 2 else portList[0]
			command += ["-R", "{}:localhost:{}".format(srcPort, dstPort)]
	
		# Check if process is running
		processList = shell(["ps", "-eo", "pid,command"])
		regexpr = r"ssh.*-nfNT\s+" + r"\s+".join([re.escape(str(cmd)) for cmd in config["auth"]]) + r"\b"
		runningList = []
		for process in processList.splitlines():
			process = process.decode()
			if re.search(regexpr, process, re.IGNORECASE):
				pid = process.strip().split()[0]
				runningList.append(pid)
	
		# If running
		if len(runningList) > 0:
	
			# Check if the tunnel is still responsive
			openPortList = shell(["ssh"] + config["auth"] + ["netstat", "-an"])
			nbConnectionsActive = 0
			for port in config["ports"]:
				regexpr = r"tcp.*:\b" + re.escape(str(port).split(":")[0]) + r"\b.*LISTEN"
				for openPort in openPortList.splitlines():
					openPort = openPort.decode()
					if re.search(regexpr, openPort, re.IGNORECASE):
						nbConnectionsActive += 1
						break
			connectionActive = True if nbConnectionsActive == len(config["ports"]) else False
	
			# If broken, kill it
			if not connectionActive:
				logPrint("broken", "Unresponsive tunnel, killing it")
				for pid in runningList:
					shell(["kill", "-9", str(pid)])
				runningList = []
	
		# If nothing is running
		if len(runningList) == 0:
			logPrint("bridge", "Creating bridge on port(s) %s" % (", ".join([str(port) for port in config["ports"]])))
			try:
				shell(command, noWait=True)
			except Exception as e:
				logPrint("error", "Failed while creating bridge with error: %s" % (str(e)))
				
	except Exception as e:
		logPrint("error", "Unexpected error: %s" % (str(e)))
		raise e

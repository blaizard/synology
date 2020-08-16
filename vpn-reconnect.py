#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

import os
import json
import re
import subprocess
import time
from datetime import datetime

CURRENT_DIRECTORY_PATH = os.path.realpath(os.path.dirname(__file__))
PATH_LOG = os.path.join(CURRENT_DIRECTORY_PATH, "vpn-reconnect.log")
PATH_CONFIG = os.path.join(CURRENT_DIRECTORY_PATH, ".vpn-reconnect.json")

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
		return stdout.decode()

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
		# Those identifier are foun with cat /usr/syno/etc/synovpnclient/openvpn/ovpnclient.conf
		# Id is something like o1234567890123
		"id": None,
		"name": None,
		"protocol": "openvpn"
	}

	try:
	
		# Load the configuration
		if not os.path.exists(PATH_CONFIG):
			with open(PATH_CONFIG, "w") as f:
				f.write(json.dumps(config, sort_keys=True, indent=4, separators=(',', ': ')))
		with open(PATH_CONFIG, "r") as f:
			configUser = json.load(f)
			config.update(configUser)
	
		# Check if the VPN is active
		vpnActive = False
		try:
			result = shell(["ifconfig", "tun0"])
			if "00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00" in result:
				vpnActive = True
		except:
			pass

		if not vpnActive:
			logPrint("info", "VPN inactive, attempt to reconnect...")

			with open("/usr/syno/etc/synovpnclient/vpnc_connecting", "w") as f:
				f.write("conf_id={}\r\n".format(config["id"]))
				f.write("conf_name={}\r\n".format(config["name"]))
				f.write("proto={}\r\n".format(config["protocol"]))

			shell(["synovpnc", "reconnect", "--protocol={}".format(config["protocol"]), "--name={}".format(config["name"])])
			logPrint("info", "Reconnection completed")
				
	except Exception as e:
		logPrint("error", "Unexpected error: %s" % (str(e)))
		raise

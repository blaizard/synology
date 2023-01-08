#!/usr/bin/python3

import pathlib
import subprocess
import sys
import http.client as httplib

scriptDirectoryPath = pathlib.Path(__file__).parent.resolve()

def isInternet() -> bool:
	conn = httplib.HTTPSConnection("8.8.8.8", timeout=5)
	try:
		conn.request("HEAD", "/")
		return True
	except Exception:
		return False
	finally:
		conn.close()

if __name__ == '__main__':

	result = subprocess.run(["/bin/bash", str(scriptDirectoryPath / "reconnect_vpn" / "reconnect-vpn.sh")])
	# Reconnect failed
	if result.returncode == 2:
		if isInternet():
			subprocess.run(["reboot"])

	sys.exit(result.returncode)

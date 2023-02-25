#!/usr/bin/python3

import pathlib
import subprocess
import sys
import http.client as httplib
import json
import time
import typing
import datetime

scriptDirectoryPath = pathlib.Path(__file__).parent.resolve()
configPath = scriptDirectoryPath / "vpn-reconnect.json"

def isHTTPConnection(url: str, timeoutS: int = 5) -> None:
	"""Check if there is a connection to an HTTP server."""

	conn = httplib.HTTPSConnection(url, timeout=timeoutS)
	try:
		conn.request("HEAD", "/")
		return True
	except Exception:
		return False
	finally:
		conn.close()

def getDateTime() -> str:
	return str(datetime.datetime.now())

def reboot() -> None:
	"""Reboot the system."""

	subprocess.run(["reboot"])

EVENT_NO_INTERNET = "no internet"
EVENT_NO_REMOTE = "no remote"
EVENT_REBOOT = "reboot"
EVENT_NO_REBOOT_YET = "no reboot yet"
EVENT_RECONNECT = "reconnect"
EVENT_RECONNECT_FAILED = "reconnect failed"
EVENT_NO_PROFILE = "no profile"
EVENT_EXCEPTION = "exception"
EVENT_GOOD = "good"

LogEntryStorage = typing.Tuple[int, str, typing.Optional[str]]

class LogEntry:
	def __init__(self, item: LogEntryStorage) -> None:
		self.item = item
	
	@property
	def timestamp(self) -> int:
		return self.item[0]

	@property
	def duration(self) -> int:
		return int(time.time() - self.timestamp)

	@property
	def event(self) -> str:
		return self.item[1]

	@property
	def args(self) -> typing.Optional[str]:
		return self.item[2]

class Log:

	def __init__(self, data: typing.List[LogEntryStorage]) -> None:
		self.data = data

	@property
	def last(self) -> typing.Optional[LogEntry]:
		"""Get the latest entry from the log."""

		if self.data:
			return LogEntry(self.data[-1])
		return None

	@property
	def lastReboot(self) -> typing.Optional[LogEntry]:
		"""Get the latest entry from the log."""

		for item in reversed(self.data):
			if item[1] == EVENT_REBOOT:
				return LogEntry(item)

		return None

	def add(self, event: str, args: typing.Optional[str] = None) -> None:
		"""Add a new event to the list."""

		# If the previous event is the same, do nothing.
		if self.last and self.last.event == event:
			return

		self.data.append((int(time.time()), event, getDateTime() if args is None else args))
		if len(self.data) > 64:
			self.data = self.data[-64:]

def main(config: typing.Any, log: Log) -> bool:
	"""Check and maintain the VPN connection.
	
	Returns:
		True if a reboot is needed, False otherwise.
	"""

	# Check if there is access to internet.
	# There is nothing to just but wait.
	if not isHTTPConnection(config["internet"], timeoutS = 30):
		log.add(EVENT_NO_INTERNET)
		return False

	# Attempt to re-connect if the connection is not up.
	result = subprocess.run(["/bin/bash", str(scriptDirectoryPath / "reconnect_vpn" / "reconnect-vpn.sh")])

	# No profile, therefore nothing to do.
	if result.returncode == 3:
		log.add(EVENT_NO_PROFILE)
		return False

	# Reconnect failed.
	if result.returncode == 2:
		log.add(EVENT_RECONNECT_FAILED)
		return True

	# Reconnect successfully.
	if result.returncode == 1:
		log.add(EVENT_RECONNECT)

	# Already connected.
	if result.returncode == 0:
		log.add(EVENT_GOOD)

	# Assert that it can reach the remote server.
	if not isHTTPConnection(config["remote"], timeoutS = 30):
		log.add(EVENT_NO_REMOTE)
		return True

	return False

if __name__ == '__main__':

	# Read the configuration.
	configRaw = json.loads(configPath.read_text()) if configPath.is_file() else {}
	config = {
		"internet": "8.8.8.8",
		"remote": "8.8.8.8",
		"logs": []
	}
	config.update(configRaw)

	isReboot = False
	log = Log(config["logs"])
	try:
		isReboot = main(config=config, log=log)

		if isReboot:
			# Check when was the last reboot
			maybeReboot = log.lastReboot
			if maybeReboot is not None and maybeReboot.duration < 24 * 3600:
				log.add(EVENT_NO_REBOOT_YET)
				isReboot = False

	except Exception as e:
		log.add(EVENT_EXCEPTION, str(e))

	finally:
		if isReboot:
			log.add(EVENT_REBOOT)
		config["last"] = getDateTime()
		configPath.write_text(json.dumps(config, indent=4))

	# Reboot if needed.
	if isReboot:
		reboot()

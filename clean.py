#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

import os
import sys
import time
import re
import subprocess
import shutil
import json
from datetime import datetime

CURRENT_DIRECTORY_PATH = os.path.realpath(os.path.dirname(__file__))

PATH_LOG = os.path.join(CURRENT_DIRECTORY_PATH, "clean.log")
PATH_CONFIG = os.path.join(CURRENT_DIRECTORY_PATH, ".clean.json")
PATH_TRASH = os.path.join(CURRENT_DIRECTORY_PATH, "trash")

now = time.time()
oldTime = now - (60 * 60 * 24) * 2 # 2 days ago

atLeastOneAction = False

def printAction(type, message):
	print "%s\t%s" % (type, message)
	with open(PATH_LOG, "a") as myfile:
		myfile.write("[%s]\t%s\t%s\n" % (str(datetime.now()), type, message))
	atLeastOneAction = True

"""
Search for pattern
"""
def searchDirectory(config, regexpr, callback):

	if not config["path"]:
		return

	r = re.compile(regexpr)

	for root, dirs, files in os.walk(config["path"]):
		for file in files:
			if r.match(file):
				callback(os.path.join(root, file), config)

"""
Search for pattern
"""
def cleanupTrash(config):

	for root, dirs, files in os.walk(PATH_TRASH):
		for file in files:
			path = os.path.join(root, file)
			mtime = os.path.getmtime(path)
			if mtime < (now - (60 * 60 * 24) * config["trash"]["expirationDays"]):
				os.remove(path)
				printAction("DELETE", path)

"""
Move a file to trash
"""
def moveToTrash(path, config):
	destination = PATH_TRASH + path

	# Destination directory
	destinationDir = os.path.dirname(destination)
	if not os.path.exists(destinationDir):
		os.makedirs(destinationDir)

	# Move and touch the file to update its modification time
	shutil.move(path, destination)
	with open(destination, 'ab'):
		os.utime(destination, None)

	printAction("TRASH", "%s -> %s" % (path, destination))

"""
Move a file to trash only if old
"""
def moveToTrashIfOld(path, config):
	mtime = os.path.getmtime(path)

	if "deleteExpirationDays" not in config or mtime < (now - (60 * 60 * 24) * config["deleteExpirationDays"]):
		moveToTrash(path, config)

"""
Check if it is a live photo and move it to trash
"""
def handleiOSLivePhoto(path, config):

	correspondingImg = path.replace('.MOV', '.JPG')
	if os.path.isfile(correspondingImg):

		try:
			t = videoDuration(path)
			# Shorter than 4 seconds
			# There are some iOS Live Photo that are >3 seconds.
			if t < 4:
				moveToTrash(path, config)
		except:
			print "WARNING cannot read video duration of %s" % (path)

"""
Get the video duration
"""
def videoDuration(path):

	proc = subprocess.Popen(["ffmpeg", "-i", path, "-f", "null"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = proc.communicate()

	# Find the duration of the first channel
	regexpr = re.compile('Duration:\s*([^\s]+),')
	match = regexpr.findall(stdout + stderr)
	if not match:
		raise Exception("Unable to read video duration of %s" % (path))

	# Parse the time
	t = datetime.strptime(match[0], '%H:%M:%S.%f')
	return (t - datetime(1900,1,1)).total_seconds()

# Main
if __name__ == '__main__':

	config = {
		"directoryList": [
			{
				# "absolute/path/where/videos/are/located"
				"path": None,
				"deleteiOSLivePhoto": True,
				"deleteTranscodedVideos": True,
				"deleteExpirationDays": 2
			}
		],
		"trash": {
			# Number of days before the file gets deleted from the trash
			"expirationDays": 7
		}
	}

	# Load the configuration
	if not os.path.exists(PATH_CONFIG):
		with open(PATH_CONFIG, 'w') as f:
			f.write(json.dumps(defaultConfig, sort_keys=True, indent=4, separators=(',', ': ')))
	with open(PATH_CONFIG, 'r') as f:
		configUser = json.load(f)
		config.update(configUser)

	for dirConfig in config["directoryList"]:

		# Handle iOS live photos and delete them
		if "deleteiOSLivePhoto" in dirConfig and dirConfig["deleteiOSLivePhoto"]:
			searchDirectory(dirConfig, '.*\.MOV$', handleiOSLivePhoto)

		# Cleanup transcoded videos
		if "deleteTranscodedVideos" in dirConfig and dirConfig["deleteTranscodedVideos"]:
			searchDirectory(dirConfig, '.*\((low|medium|high)\).*', moveToTrashIfOld)

	# Delete old files in trash
	cleanupTrash(config)

	# This will force sending an email if something happen
	if atLeastOneAction:
		sys.exit(1)
	sys.exit(0)

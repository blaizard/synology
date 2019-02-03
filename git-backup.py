#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

import os
import sys
import json
from datetime import datetime
import urllib2
import base64
import subprocess

CURRENT_DIRECTORY_PATH = os.path.realpath(os.path.dirname(__file__))
PATH_CONFIG = os.path.join(CURRENT_DIRECTORY_PATH, ".git-backup.json")
PATH_LOG = os.path.join(CURRENT_DIRECTORY_PATH, "git-backup.log")

def printLog(type, message):
	print("%s\t%s" % (type, message))
	with open(PATH_LOG, "a") as myfile:
		myfile.write("[%s]\t%s\t%s\n" % (str(datetime.now()), type, message))
	atLeastOneAction = True

"""
Backup all Github repositories (public and private)
"""
def githubBackup(config):

	if ("user" not in config) or ("token" not in config):
		raise Exception("Missing user and/or token in the configuration")

	request = urllib2.Request("https://api.github.com/user/repos?per_page=100")
	base64string = base64.encodestring("%s/token:%s" % (config["user"], config["token"])).replace("\n", "")
	request.add_header("Authorization", "Basic %s" % base64string)
	response = None
	repoList = []
	try:
		response = urllib2.urlopen(request)
		repoList = json.loads(response.read())
	finally:
		if response:
			response.close()

	# List the repos
	repoUrlList = []
	for repo in repoList:
		# Ignore forked repos
		if (not repo["fork"]) or ("ignoreFork" not in config) or (not config["ignoreFork"]):
			repoUrlList.append(repo["full_name"])

	# Clone the repositories
	for uri in repoUrlList:
		url = "https://%s:%s@github.com/%s.git" % (config["user"], config["token"], uri)
		gitBackup(config["path"], url)

"""
Backing up git repository
"""
def gitBackup(path, url):
	repoPath = os.path.join(path, os.path.splitext(os.path.basename(url))[0])
	# If file exists, do a git pull
	if os.path.exists(repoPath):
		try:
			subprocess.check_call(["git", "pull", url], cwd=repoPath)
		except Exception as e:
			printLog("git pull of %s failed: %s" % (repoPath, str(e)))
			raise
	else:
		subprocess.check_call(["git", "clone", url], cwd=path)

# Main
if __name__ == '__main__':

	config = {
		"repos": [
			#{
			#	"type": "github",
			#	"user": USERNAME,
			#	"token": API_TOKEN,
			#	"ignoreFork": True,
			#	"path": ABSOUTE_PATH
			#}
		]
	}

	# Load the configuration
	if not os.path.exists(PATH_CONFIG):
		with open(PATH_CONFIG, 'w') as f:
			f.write(json.dumps(config, sort_keys=True, indent=4, separators=(',', ': ')))
	with open(PATH_CONFIG, 'r') as f:
		configUser = json.load(f)
		config.update(configUser)

	for repo in config["repos"]:
		try:
			if "path" not in repo:
				raise Exception("Missing path in the configuration")

			# Create the output directory if it does not exists
			if not os.path.exists(repo["path"]):
				os.makedirs(repo["path"])

			if repo["type"] == "github":
				githubBackup(repo)
			elif repo["type"] == "git":
				gitBackup(repo["path"], url)
			else:
				raise Exception("Unknown repository type \"" + repo["type"] + "\"")
		except Exception as e:
			printLog("ERROR", "Repository failed to backup: %s" % (str(e)))

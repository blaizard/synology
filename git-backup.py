#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

import os
import sys
import json
import socket
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

class Rest:
	def __init__(self, endpoint = None, headers = {}):
		self.endpoint = endpoint
		self.headers = headers

	def _prepareRequest(self, path, headers = {}, data = None):
		request = urllib2.Request("{}{}".format(self.endpoint, path) if self.endpoint else path, data)
		
		# Update headers
		newHeader = headers.copy()
		newHeader.update(self.headers)
		for key, value in newHeader.items():
			request.add_header(key, value)
		
		return request

	def _sendRequest(self, request, raiseOnError):
		response = None
		lastErrorCode = 0
		try:
			retryCounter = 4
			while retryCounter:
				retryCounter -= 1
				try:
					response = urllib2.urlopen(request)
					break

				except urllib2.HTTPError as e:
					lastErrorCode = e.code
					# 422 Unprocessable Entity - the server understands the content type of the request entity, and the syntax of the request entity is correct, but it was unable to process the contained instructions.
					if retryCounter and lastErrorCode in [422]:
						printLog("WARNING", "HTTP error, return code {}, retrying".format(lastErrorCode))
					else:
						raise

				#except Exception as e:
				#	if retryCounter:
				#		printLog("WARNING", "Error: {}, retying".format(str(e)))
				#	else:
				#		raise

			return response.read(), response.getcode()

		except:
			if raiseOnError:
				raise
			return "", lastErrorCode

		finally:
			if response:
				response.close()

	def json(self, raiseOnError = True, **kwargs):
		request = self._prepareRequest(**kwargs)
		response, status = self._sendRequest(request, raiseOnError)
		if response:
			return json.loads(response), status
		return {}, status

class Gitea:
	def __init__(self, config):

		self.rest = Rest(endpoint = "{}/api/v1".format(config.get("giteaEndpoint")), headers = {
			"Content-type": "application/json",
			"Authorization": "token {}".format(config.get("giteaToken"))
		})

		output, status = self.rest.json(path = "/user")
		self.uid = output["id"]
		print("Using gitea user ID: {}".format(self.uid))

	def process(self, url, user = None, password = None):
		url.split("/")[-1].replace(".git", "")
		m = {
			"repo_name": url.split("/")[-1].replace(".git", ""),
			"clone_addr": url,
			"mirror": True,
			"private": bool(user and password),
			"uid": self.uid,
		}

		if bool(user and password):
			m["auth_username"] = user
			m["auth_password"] = password

		jsonString = json.dumps(m)
		output, status = self.rest.json(path = "/repos/migrate", raiseOnError = False, data = jsonString)

		if status in [201]:
			printLog("INFO", "Gitea mirror repository created: '{}'".format(m["repo_name"]))
		elif status not in [409]:
			printLog("ERROR", "HTTP error, return code {} while creating repository '{}'".format(status, m["repo_name"]))
			raise

class Hooks:
	def __init__(self, config):
		self.hooks = []
		if "giteaToken" in config and "giteaToken" in config:
			self.hooks.append(Gitea(config))

	def process(self, **kwargs):
		for hook in self.hooks:
			hook.process(**kwargs)

"""
Backup all Github repositories (public and private)
"""
def githubBackup(config):

	if ("user" not in config) or ("token" not in config):
		raise Exception("Missing user and/or token in the configuration")

	hooks = Hooks(config)

	base64string = base64.encodestring("%s/token:%s" % (config["user"], config["token"])).replace("\n", "")
	repoList, status = Rest().json(path = "https://api.github.com/user/repos?per_page=100", headers = {
		"Authorization": "Basic {}".format(base64string)
	})

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
		hooks.process(url = url)

"""
Backing up git repository
"""
def gitBackup(path, url):
	repoPath = os.path.join(path, os.path.splitext(os.path.basename(url))[0])
	
	retryCounter = 4
	while retryCounter:
		retryCounter -= 1
		
		try:
			# If file exists, do a git pull
			if os.path.exists(repoPath):
				subprocess.check_call(["git", "pull", url], cwd=repoPath)
			else:
				subprocess.check_call(["git", "clone", url], cwd=path)
			break

		except Exception as e:
			printLog("ERROR", "git command for %s failed: %s" % (repoPath, str(e)))
			if not retryCounter:
				raise
			printLog("INFO", "retrying...")

# Main
if __name__ == '__main__':

	config = {
		"repos": [
			#{
			#	"type": "github",
			#	"user": USERNAME,
			#	"token": API_TOKEN,
			#	"ignoreFork": True,
			#	"path": ABSOUTE_PATH,
			#	"giteaEndpoint": "http://localhost:6008",
			#	"giteaToken": API_TOKEN
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

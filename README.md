# Synology
Useful collection of scripts for Synology NAS

All scripts comes with a configuration, please make sure you understand the script before running it. Also I am not responsible for any damage cause by the script, you are running it at your own responsibility.

## Clean

Cleanup files within a collection of directories that matches the following characteristics:
- Delete the short video associated with an iOS Live Photos
- Delete old transcoded videos

All deleted files are moved to a trash, that will be deleted few days later

Recommandation: add this script to run every day with the Task Scheduler.

## Bridge

Create a reverse proxy between your DSM server and the host. This is useful if your IP is not available from internet or you cannot open ports.

Recommandation: add this script to run every 5min with the Task Scheduler.

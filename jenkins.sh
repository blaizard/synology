#!/bin/bash

# Set the appropriate permissions for docker
sudo chown -R 1000:1000 /var/run/docker.sock

# ---- To update a Jenkins -----------------------------------------------------

# Connect to the docker container
sudo docker exec -u 0 -it jenkins bash
# download URL
wget http://updates.jenkins-ci.org/latest/jenkins.war
# move it
mv ./jenkins.war /usr/share/jenkins
# give the right permissions
chmod 777 /usr/share/jenkins/jenkins.war
# close the bash session
exit
# Restart Jenkins by doing a:
sudo docker container restart jenkins
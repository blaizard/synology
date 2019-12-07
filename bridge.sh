#!/bin/sh

# Note: the followign should be added to ~/.ssh/config
# in order to prevent disconnection.
# Host *
# ServerAliveInterval 120
#
# Also to access the server from external IP, use the followng option in
# /etc/ssh/sshd_config
# GatewayPorts yes

path=`dirname "$0"`
confPath="$path/.bridge.conf"

# Look for the configuration file, if it does not exists, create it
if [[ ! -e "$confPath" ]]; then

	cat > "$confPath" << EOF
# List of ports to be forwarded, must be separated with a space
PORT_LIST='5001 5002'

# Authentication to connect to the SSH server. The following should be sufficient to connect: 'ssh $SSH_AUTH'
SSH_AUTH='admin@myserver.com'
EOF

fi

# Load the configuration
. "$confPath"

# Generate the ssh command to connect to the target
SSH_ARGS=
for port in $PORT_LIST
do
	sshArgs="$sshArgs -R $port:localhost:$port"
done
command="ssh -nNT $sshArgs $SSH_AUTH"

# Check if the bridge is running
isRunning=`ps aux | grep "ssh" | grep "$SSH_AUTH" | grep -v grep`

# Check if the tunnel is alive
if [ ! -z "$isRunning" ]; then

	firstPort=`echo "$PORT_LIST" | awk '{print $1}'`
	ssh $SSH_AUTH netstat -an | egrep "tcp.*:$firstPort.*LISTEN"  > /dev/null 2>&1
	if [ $? -ne 0 ] ; then
		echo "[`date`] [BROKEN] Unresponsive tunnel, killing it" >> $path/bridge.log
		pkill -f -x "$command"
		isRunning=''
	fi

fi

# Run the tunnel if not already running
if [ -z "$isRunning" ]; then

	echo "[`date`] [BRIDGE] Creating bridge on port(s) $PORT_LIST" >> $path/bridge.log
	nohup $command >> $path/bridge.log&

fi

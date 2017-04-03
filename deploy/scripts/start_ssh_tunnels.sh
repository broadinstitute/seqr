# if you run this script on your laptop, it will open ssh tunnels to the different processes on this VM, so you can, for example, go to http://localhost:9001 to view the supervisord control panel for this VM 

HOST=$1   # the IP-address or domain name of the VM
HOST=104.196.152.168

pids=""

# 6060
# 9001

# backend
# 8983  solr
# 6060  seqr hail server

for PORT in 8983 6060; do
   ssh -nNT -L ${PORT}:localhost:${PORT} ${USER}@${HOST} &
   pids="$pids $!" &
done

wait $pids



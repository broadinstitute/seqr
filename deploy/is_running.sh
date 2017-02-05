for i in mongod postmaster phenotips gunicorn nginx  supervisord; do 
    if pgrep -f $i > /dev/null
    then
	echo "RUNNING: $i"
    else
	echo "NOT RUNNING: $i"
    fi

done;

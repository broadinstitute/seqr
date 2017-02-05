for i in mongod postmaster xwiki gunicorn nginx  supervisord; do 
    if pgrep -x $i > /dev/null
    then
	echo "RUNNING: $i"
    else
	echo "NOT RUNNING: $i"
    fi

done;

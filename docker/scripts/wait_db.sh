#!/bin/bash

attempt=0
max_attempts=120
while ! mysqladmin ping -h"$DB_HOST" -P"$DB_PORT" --silent; do
	#wait 120 sec
	if [ $attempt -ge $max_attempts ]; then
		echo "Can not connect to database during $max_attempts sec"
		exit 1
	fi
	attempt=$[$attempt+1]
	echo "Wait for MySQL Server ${DB_HOST}:${DB_PORT} [attempt $attempt/$max_attempts]"
    sleep 1
done
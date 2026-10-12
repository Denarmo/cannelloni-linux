#!/bin/sh

cd $(dirname "$0")

if [ ! -f /usr/sbin/frontend_start.original ]; then
	mv /usr/sbin/frontend_start /usr/sbin/frontend_start.original
fi

cp boot.sh /usr/sbin/frontend_start

mkdir -p /usr/share/cannelloni
cp *.bmp /usr/share/cannelloni

/usr/sbin/frontend_start
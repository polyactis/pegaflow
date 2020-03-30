#!/bin/bash
# 201-8-26 wrap around mkdirhier/mkdir so that it won't report error when the directory already exists
if test -x /usr/bin/mkdirhier
then
	echo "using mkdirhier"
	/usr/bin/mkdirhier $1
else
	mkdir -p $1
fi
echo "return code is $?"

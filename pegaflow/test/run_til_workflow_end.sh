#!/bin/bash

if test $# -lt 1
then
    echo
    echo "Usage: $0 jobstate_file"
    echo
    echo "Description:"
    echo "  This shell script runs until the workflow ends."
    echo "  It checks the jobstate.log file every 5 secs until MONITORD_FINISHED shows up in the jobstate file."
    echo
    echo "Example:"
    echo "	$0 work/wc.python.code.2020.Apr.1T202041/jobstate.log"
    echo 
exit
fi
jobstate_file=$1

while sleep 5; do
    if grep MONITORD_FINISHED $jobstate_file; then
        break;
    fi
    sleep 5
done
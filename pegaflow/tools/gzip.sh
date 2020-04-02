#!/bin/bash
# 2012-7.19 wrap around gzip so that input of gzip won't be deleted
if test $# -lt 2
then
	echo "Usage: $0 inputFile gzipOutputFile"
	echo
	echo "Note:"
	echo "	the gzipOutputFile should have .gz as suffix."
	echo
	echo "Example:"
	echo "	$0 input.txt input.txt.gz"
exit
fi

shellDir=`dirname $0`
source $shellDir/common.sh

inputFname=$1
outputFname=$2

exitIfFileExists $outputFname

#TODO: add a flag to choose bgzip in case tabix indexing is needed.
gzip -c $inputFname > $outputFname

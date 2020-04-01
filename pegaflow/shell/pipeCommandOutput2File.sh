#!/bin/bash
if test $# -lt 2
then
	echo
	echo "Usage: $0 outputFname commandPath [commandArguments]"
	echo
	echo "Note:"
	echo "	1. This shell script runs the command, specified by commandPath, and pipes its output to outputFname."
	echo "     The commandArguments will be added to the command."
	echo "	2. If outputFname is .gz, the output will be gzipped."
	echo
	echo "Example:"
	echo "	$0 output.depth.tsv.gz ~/bin/samtools depth input.bam"
	echo "	$0 flagstat.output.tsv ~/bin/samtools flagstat input.bam"
exit
fi
set -e
set -vx

outputFname=$1
commandPath=$2
shift
shift
#after 2 shift, all arguments left
arguments=$*


commandline="$commandPath $arguments"
outputFilenameLength=`expr length $outputFname`
gzSuffixStartPosition=`echo $outputFilenameLength-3+1|bc`
gzSuffix=`expr substr $outputFname $gzSuffixStartPosition 3`

echo gzSuffix is $gzSuffix.
echo commandline is $commandline.

if test "$gzSuffix" = ".gz"; then
	$commandline | gzip > $outputFname
	exitCodeAll="${PIPESTATUS[0]} ${PIPESTATUS[1]}"	#must be together in one line. PIPESTATUS[1] in subsequent lines has different meaning.
	exitCode1=`echo $exitCodeAll|awk -F ' ' '{print $1}'`
	exitCode2=`echo $exitCodeAll|awk -F ' ' '{print $2}'`
	
	echo "exit codes: $exitCode1, $exitCode2"
	
	if test "$exitCode1" = "0" && test "$exitCode2" = "0"
	then
		exit 0
	else
		exit 3
	fi
else
	$commandline > $outputFname
fi

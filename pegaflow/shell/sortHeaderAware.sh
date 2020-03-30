#!/bin/bash

set -e

TOPDIR=`pwd`

if test $# -lt 3 ; then
	echo ""
	echo "Usage:  $0 inputFname outputFname noOfHeaderLines [sortArgument1] [sortArgument2] ..."
	echo ""
	echo "Note:"
	echo "	#. This program is wrapper around sort with the ability to skip predefined headers."
	echo "	#. It will recognize .gz in outputFname and pipe the output through gzip."
	echo ""
	echo ""
	echo "Examples:"
	echo "  # sort a genomic file with one header line. 1st column is chromosome. 2nd column is position (integer)."
	echo "	$0 snpLocus.tsv snpLocusSorted.gz 1 -k1,1 -k2,2n"
	exit 1
fi

shellDir=`dirname $0`
source $shellDir/common.sh

inputFname=$1
outputFname=$2
noOfHeaderLines=$3
shift
shift
shift
sortArguments=$*

dataStartLineNumber=`echo $noOfHeaderLines+1|bc`
outputFilenameLength=`expr length $outputFname`
gzSuffixStartPosition=`echo $outputFilenameLength-3+1|bc`
gzSuffix=`expr substr $outputFname $gzSuffixStartPosition 3`

echo dataStartLineNumber is $dataStartLineNumber.
echo gzSuffix is $gzSuffix.

#The parentheses create a subshell, wrapping up the stdout so you can pipe it or redirect it as if it had come from a single command.
if test $noOfHeaderLines -gt 0; then
	if test "$gzSuffix" = ".gz"; then
		(head -n $noOfHeaderLines $inputFname && tail -n +$dataStartLineNumber $inputFname | sort $sortArguments) | gzip > $outputFname
		exitCodeAll="${PIPESTATUS[0]} ${PIPESTATUS[1]}"	#must be together in one line. PIPESTATUS[1] in subsequent lines has different meaning.
	else
		(head -n $noOfHeaderLines $inputFname && tail -n +$dataStartLineNumber $inputFname | sort $sortArguments) > $outputFname
		exitCodeAll="${PIPESTATUS[0]}"	#must be together in one line. PIPESTATUS[1] in subsequent lines has different meaning.
	fi
else
	if test "$gzSuffix" = ".gz"; then
		sort $sortArguments $inputFname | gzip > $outputFname
		exitCodeAll="${PIPESTATUS[0]} ${PIPESTATUS[1]}"	#must be together in one line. PIPESTATUS[1] in subsequent lines has different meaning.
	else
		sort $sortArguments $inputFname > $outputFname
		exitCodeAll="${PIPESTATUS[0]}"	#must be together in one line. PIPESTATUS[1] in subsequent lines has different meaning.
	fi
fi
echo "exitCodeAll is $exitCodeAll."
if test "$gzSuffix" = ".gz"; then
	#exitCodeAll="${PIPESTATUS[0]} ${PIPESTATUS[1]}"	#must be together in one line. PIPESTATUS[1] in subsequent lines has different meaning.
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
	exit $exitCodeAll
fi

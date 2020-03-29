#!/bin/bash

#2014.09.16 pause (flush stderr) and "exit 9 " upon receiving TERM signal
trap "exit 9" TERM
# 2014.09.16 used to kill itself to exit the whole program/script ("exit" only exits the function, not the whole script)
export TOP_PID=$$

#2014.09.11
## Example:
##	exitIfNonZeroExitCode "copy failed."
exitIfNonZeroExitCode () {
	exitCode=$?
	msg=$1
	if [ $exitCode != 0 ]; then
		echo "Error message: $msg" 1>&2
		echo "Exit code: $exitCode" 1>&2
		kill -s TERM $TOP_PID
		exit $exitCode

	fi
}

#2014.09.05 function to check if a file/folder exists, if it is , return `readlink -f ..` of it
## Examples
##	readlinkIfExistAndExitIfNot /usr/local/mydata
readlinkIfExistAndExitIfNot () {
	inputFileOrFolder=$1
	if test -r $inputFileOrFolder; then
		echo `readlink -f $inputFileOrFolder`;
	else
		#pipe stdout to stderr because it's error message
		echo "Error: $inputFileOrFolder does not exist (or not readable)." 1>&2
		kill -s TERM $TOP_PID
		exit 1;
	fi
}

#2014.09.05
mkdirhierAndExitIfFail () {
	outputFolder=$1;
	if [ ! -d $outputFolder ]; then
		mkdirhier $outputFolder	#otherwise readlink -f won't work
		exitCode=$?
		if [ $exitCode != 0 ]; then
			echo "mkdirhier $outputFolder failed with exit code $exitCode" 1>&2
			kill -s TERM $TOP_PID
			exit $exitCode
		fi
	fi
}

#2014.09.02 function to add values to environmental variables, check redundancy first
## example:
## 	addValueToEnvironmentalVariable PATH "/usr/local/sbin" 0 
addValueToEnvironmentalVariable () {
	variableName=$1
	value=$2
	position=$3
	defaultPosition=-1	#-1: append. 0: prepend
	if [ "a$position" == "a" ]; then
		position=$defaultPosition
	fi
	# use ${!variableName} to get value of a variable named variableName
	if [[ "${!variableName}" =~ "$value" ]]; then
		echo "value: $value already in variable: $variableName." 1>&2
	else
		if [[ $position == 0 ]]; then
			#without export, bash interprets the whole line as a executable
			export $variableName=$value:${!variableName}
		else
			export $variableName=${!variableName}:$value
		fi
	fi
}

findValueGivenAnOptionName () {
	if [ -z "$1" ]
	then
		echo "Option Name is not provided." 1>&2
		echo ;
	else
		optionNamePosition=`echo $arguments|awk -F ' ' '{i=1; while (i<=NF){if ($i=="'$1'") {print i}; ++i}}'`
		#echo $1 position: $optionNamePosition
		if [ -z "$optionNamePosition" ]
		then
			echo;
		else
			optionValuePosition=`echo $optionNamePosition+1|bc`
			#echo optionValuePosition $optionValuePosition
			optionValue=`echo $arguments|awk -F ' ' '{ if ('$optionValuePosition'<=NF) {print $'$optionValuePosition'} else print }'`
			echo $optionValue
		fi
	fi
}

checkVCFFileIfEmpty () {
	fname=$1
	if test -r $fname
	then
		suffix=`echo $fname|awk -F '.' '{print $NF}'`
		if test "$suffix" = "gz"
		then
			numberOfLoci=`gunzip -c $fname|grep -v "^#"|wc -l|awk -F ' ' '{print $1}'`
		else
			numberOfLoci=`grep -v "^#" $fname|wc -l|awk -F ' ' '{print $1}'`
		fi
		if test $numberOfLoci -gt 0
		then
			echo 0;
		else
			echo 1;
		fi
	else
		echo 1;
	fi
}



outputEmptyVCFWithInputHeader () {
	if [ -n "$vcfInputFname" ]
	then
		egrep "^#" $vcfInputFname 1>$outputVCFFname
	else
		if [ -n "$gzvcfInputFname" ]
		then
			gunzip -c $gzvcfInputFname | egrep "^#" 1>$outputVCFFname
		else
			touch $outputVCFFname
		fi
	fi
	#this echo is to avoid non-zero exit by egrep (nothing matches)
	echo "empty vcf with header from $vcfInputFname is created." 1>&2
}

checkIfFileExists () {
	fname=$1
	if test -r $fname
	then
		echo 0;
	else
		echo 1;
	fi
}
exitIfFileExists () {
	fname=$1
	if test -r $fname
	then
		echo "$fname exists. Do not want to append/overwrite it. Check and rename it." 1>&2
		echo 0;
		exit 2;
	else
		echo 1;
	fi
}

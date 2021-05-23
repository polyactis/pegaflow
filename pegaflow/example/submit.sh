#!/bin/bash

# stop & exit if any error
set -e

TOPDIR=`pwd`
storageSiteNameDefault="local"
submitOptionDefault="--submit"
scratchTypeDefault="1"
cleanupClusterSizeDefault=15
submitDir="submit"

## two files to store the names of the successfully-submitted and submit-failed workflows respectively.
runningWorkflowLogFnameDefault=runningWorkflows.txt
failedWorkflowLogFnameDefault=failedWorkflows.txt

# figure out where Pegasus is installed
export PEGASUS_HOME=`which pegasus-plan | sed 's/\/bin\/*pegasus-plan//'`
if [ "x$PEGASUS_HOME" = "x" ]; then
	echo "Unable to determine the location of your Pegasus installation."
	echo "Please make sure pegasus-plan is in your path"
	exit 1
fi 
echo "pegasus home is " $PEGASUS_HOME

## the submitter's home directory
# it's a must to export HOME in condor environment because HOME is not set by default.
HOME_DIR=$HOME

## unused.
PEGASUS_PYTHON_LIB_DIR=`$PEGASUS_HOME/bin/pegasus-config --python`

if test $# -lt 2 ; then
	echo "Usage:"
	echo "  $0 dagFile computingSiteName [keepIntermediateFiles] [cleanupClusterSize] "
	echo "      [submitOption] [storageSiteName] [finalOutputDir] [relativeSubmitDir]"
	echo ""
	echo "Note:"
	echo "  - computingSiteName: the computing cluster on which the jobs will run. "
	echo "     Possible values: local (single-node), condor (computing cluster with condor setup). "
	echo "     The site in dagFile should match this."
	echo "  - keepIntermediateFiles: 1 means no intermediate-file cleanup. Anything else (default) means cleanup."
	echo "     1 will change the default submit option ($submitOptionDefault) to --submit --cleanup none."
	echo "     This is useful if you want to keep all intermediate files."
	echo "  - cleanupClusterSize: how many jobs get clustered into one job on each level."
	echo "     Default is $cleanupClusterSizeDefault."
	echo "  - submitOption: options passed to pegasus-plan. Default is $submitOptionDefault. "
	echo "     '--submit' means pegasus will plan & submit the workflow."
	echo "     '--submit --cleanup none' means pegasus will not add intermediate-file cleanup jobs."
	echo "     If you set it to empty string, '', only planning will be done but no submission."
	echo "     This option overwrites the keepIntermediateFiles option."
	echo "  - storageSiteName: the site to which final output is staged to. "
	echo "     Default is $storageSiteNameDefault. Almost never need to be changed."
	echo "  - finalOutputDir: the directory that will contain the final output files."
	echo "     These files must be designated as transfer=True in the workflow."
	echo "     If this folder doesn't exist, pegasus would create one. "
	echo "     Default is dagFile name (without the first folder if there is one) + year+date+time."
	echo "  - relativeSubmitDir: the pegasus submit folder relative to ${submitDir}/."
	echo "     This folder will contain all job submission files, job stdout/stderr output, logs, etc."
	echo "     Default is the same as finalOutputDir."
	echo "  - finalOutputDir and relativeSubmitDir can be the same. But they must be different from previous workflows."
	echo ""
	echo "Examples:"
	echo "  #run on a condor computing cluster"
	echo "  $0 dags/TrioInconsistency15DistantVRC.xml condor"
	echo
	echo "  #run on a single node"
	echo "  $0 dags/TrioInconsistency15DistantVRC.xml local"
	echo
	echo "  #plan & submit and keep intermediate files"
	echo "  $0 dags/TrioInconsistency15DistantVRC.xml condor 1"
	echo
	echo "  #only planning (no running) by setting submitOption to an empty string (options in the middle do not matter)"
	echo "  $0 dags/TrioInconsistency15DistantVRC.xml condor 0 20 \"  \" "
	echo
	echo "  #run the workflow, keep intermediate files. Set the finalOutputDir and relativeSubmitDir."
	echo "  $0 dags/TrioInconsistency15DistantVRC.xml condor 1 20 \"--submit\" local "
	echo "     TrioInconsistency/TrioInconsistency15DistantVRC_20110929T1726 "
	echo "     TrioInconsistency/TrioInconsistency15DistantVRC_20110929T1726 "
	echo
	exit 1
fi

dagFile=$1
computingSiteName=$2
keepIntermediateFiles=$3
cleanupClusterSize=$4
submitOption=$5
storageSiteName=$6
finalOutputDir=$7
relativeSubmitDir=$8

#no cleanup when keepIntermediateFiles = 1
if test "$keepIntermediateFiles" = "1"; then
	submitOptionDefault="--submit --cleanup none"
fi

if test -z "$cleanupClusterSize"
then
	cleanupClusterSize=$cleanupClusterSizeDefault
fi

echo cleanupClusterSize is $cleanupClusterSize.

echo "Default submitOption is changed to $submitOptionDefault."

if test -z "$submitOption"
then
	submitOption=$submitOptionDefault
fi

if [ -z $storageSiteName ]; then
	storageSiteName=$storageSiteNameDefault
fi

# The stageout folder that will contain all the final output.
if [ -z $finalOutputDir ]; then
	#time without :. like 16:30:30 => 163030
	t=`python3 -c "import time; print(time.asctime().split()[3].replace(':', ''))"`
	month=`python3 -c "import time; print(time.asctime().split()[1])"`
	day=`python3 -c "import time; print(time.asctime().split()[2])"`
	year=`python3 -c "import time; print(time.asctime().split()[-1])"`
    #remove the first folder (usually "dags/") in the dag file path
	finalOutputDir=`python3 -c "import sys, os; pathLs=os.path.splitext(sys.argv[1])[0].split('/'); n=len(pathLs); print('/'.join(pathLs[-(n-1):]))" $dagFile`.$year.$month.$day\T$t;
	echo Final output will be in $finalOutputDir
fi

if test -z "$relativeSubmitDir"
then
	relativeSubmitDir=$finalOutputDir
fi

runningWorkflowLogFname=$runningWorkflowLogFnameDefault
failedWorkflowLogFname=$failedWorkflowLogFnameDefault

echo "Submitting to $computingSiteName for computing."
echo "storageSiteName is $storageSiteName."
echo "runningWorkflowLogFname is $runningWorkflowLogFname."
echo "failedWorkflowLogFname is $failedWorkflowLogFname."
echo "The workflow submit option is $submitOption."
echo "relativeSubmitDir is $relativeSubmitDir."
echo "PYTHONPATH is $PYTHONPATH."

# The following two lines shall be added to any condor cluster that do not use shared file system or 
# 	a filesystem that is not good at handling numerous small files in one folder.
#		<profile namespace="condor" key="should_transfer_files">YES</profile>
#		<profile namespace="condor" key="when_to_transfer_output">ON_EXIT_OR_EVICT</profile>
# Example to set the PYTHONPATH:
#		<profile namespace="env" key="PYTHONPATH">$PYTHONPATH:$PEGASUS_PYTHON_LIB_DIR</profile>

## create the site catalog
cat >sites.xml <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<sitecatalog xmlns="http://pegasus.isi.edu/schema/sitecatalog"
             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
             xsi:schemaLocation="http://pegasus.isi.edu/schema/sitecatalog http://pegasus.isi.edu/schema/sc-4.0.xsd"
             version="4.0">
	<site handle="local" arch="x86_64" os="LINUX">
		<directory type="shared-scratch" path="$TOPDIR/scratch">
			<file-server operation="all" url="file://$TOPDIR/scratch"/>
		</directory>
		<directory type="local-storage" path="$TOPDIR/output/$finalOutputDir">
			<file-server operation="all" url="file://$TOPDIR/output/$finalOutputDir"/>
		</directory>
		<profile namespace="env" key="PEGASUS_HOME" >$PEGASUS_HOME</profile>
		<profile namespace="env" key="HOME">$HOME</profile>
		<profile namespace="env" key="PATH" >$HOME_DIR/bin:$PATH</profile>
		<profile namespace="env" key="PYTHONPATH">$PYTHONPATH</profile>
		<profile namespace="env" key="LC_ALL">$LC_ALL</profile>
	</site>
	<site handle="condor" arch="x86_64" os="LINUX">
		<directory type="shared-scratch" path="$TOPDIR/scratch">
			<file-server operation="all" url="file://$TOPDIR/scratch"/>
		</directory>
		<!-- Change the style to HTCondor for jobs to be executed in the HTCondor Pool.
			By default, Pegasus creates jobs suitable for grid execution. -->
		<profile namespace="pegasus" key="style" >condor</profile>
		<!-- Change the universe to vanilla to make the jobs go to remote compute
			nodes. The default is local which will only run jobs on the submit host -->
		<profile namespace="condor" key="universe" >vanilla</profile>
		<profile namespace="env" key="PEGASUS_HOME" >$PEGASUS_HOME</profile>
		<profile namespace="env" key="HOME" >$HOME_DIR</profile>
		<profile namespace="env" key="PATH" >$HOME_DIR/bin:$PATH</profile>
		<profile namespace="env" key="PYTHONPATH">$PYTHONPATH</profile>
		<profile namespace="env" key="LC_ALL">$LC_ALL</profile>
	</site>
</sitecatalog>
EOF
# plan and submit the  workflow

export CLASSPATH=.:$PEGASUS_HOME/lib/pegasus.jar:$CLASSPATH
echo Java CLASSPATH is $CLASSPATH
#2013.03.30 "--force " was once added due to a bug. it'll stop file reuse.
commandLine="pegasus-plan -Dpegasus.file.cleanup.clusters.size=$cleanupClusterSize \
	--conf pegasusrc --sites $computingSiteName --dax $dagFile \
	--dir ${submitDir} --relative-dir $relativeSubmitDir --verbose \
	--output-site $storageSiteName --cluster horizontal $submitOption "

echo commandLine is $commandLine

$commandLine

exitCode=$?
if test $exitCode = "0"; then
	echo ${submitDir}/$relativeSubmitDir >> $runningWorkflowLogFname
else
	echo ${submitDir}/$relativeSubmitDir >> $failedWorkflowLogFname
fi

# add the option below for debugging
#	-vvvvv \
#	--cleanup none\

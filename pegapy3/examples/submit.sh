#!/bin/bash

source ~/.bash_profile
# stop & exit if any error
set -e

TOPDIR=`pwd`
storageSiteNameDefault="local"
submitOptionDefault="--submit"
scratchTypeDefault="1"
cleanupClustersSizeDefault=15

#2013.04.24 two files to store the names of the successfully-submitted and submit-failed workflows respectively.
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

# 20110828 same as the submitter's home directory
# it's a must to export HOME in condor environment because HOME is not set by default.
HOME_DIR=$HOME

PEGASUS_PYTHON_LIB_DIR=`$PEGASUS_HOME/bin/pegasus-config --python`

#a random number
freeSpace="50000G"


if test $# -lt 2 ; then
	echo "Usage:"
	echo "  $0 dagFile computingSiteName [keepIntermediateFiles] [cleanupClustersSize] [scratchType] [submitOption] [storageSiteName] [finalOutputDir] [submitFolderName]"
	echo ""
	echo "Note:"
	echo "	#. computingSiteName is the computing cluster on which the jobs will run. Options are: local (single-node), ycondor (the whole cluster). The site in dagFile should match this."
	echo ""
	echo "	#. keepIntermediateFiles (setting it to 1 means no cleanup, otherwise or default is cleanup.). It changes the default submit option ($submitOptionDefault) to --submit --cleanup none ."
	echo "	#. cleanupClustersSize controls how many jobs get clustered into one on each level. Default is $cleanupClustersSizeDefault ."
	echo "	#. scratchType is the type of scratch file system to use."
	echo "		Only valid for hcondor site. "
	echo
	echo "	#. submitOption are options passed to pegasus-plan. Default is $submitOptionDefault. "
	echo "		'--submit' means pegasus will plan & submit the workflow."
	echo "		'--submit --cleanup none' means pegasus will not add cleanup jobs = all intermediate files will be kept."
	echo "		If you set it to empty string, '', only planning will be done but no submission."
	echo "		This option overwrites the keepIntermediateFiles option, which modifies the default submitOption."
	echo "	#. storageSiteName is the site to which final output is staged to. default is $storageSiteNameDefault."
	echo "	#. finalOutputDir is the directory which would contain the files requested to be transferred out by the end of the workflow. If it doesn't exist, pegasus would create one. Default is dagFile (without first folder if there is one) + year+date+time"
	echo "	#. submitFolderName is the submit folder which contains all job description files, job stdout/stderr output, logs, etc.It is optional. If not given, value of finalOutputDir is taken as submitFolderName."
	echo "	#. finalOutputDir and submitFolderName could be same. But they should be different from previous workflows."
	echo ""
	echo "Examples:"
	echo "	#plan & submit and do not keep intermediate files, cleanup clustering=30"
	echo "	$0 dags/TrioInconsistency15DistantVRC.xml ycondor"
	echo "	$0 dags/TrioInconsistency/TrioInconsistency15DistantVRC.xml ycondor 0 30"
	echo
	echo "	#plan & submit, keep intermediate files, cleanupClustersSize=10 doesn't matter, run on scratch type 2 on hcondor"
	echo "	$0 dags/TrioInconsistency15DistantVRC.xml hcondor 1 10 2"
	echo
	echo "	#only planning, no running (keepIntermediateFiles & cleanupClustersSize & scratchType do not matter) by assigning empty spaces to submitOption"
	echo "	$0 dags/TrioInconsistency15DistantVRC.xml ycondor 0 20 1 \"  \" "
	echo
	echo "	#run the workflow while keeping intermediate files. good for testing in which you often need to modify .dag.rescue log to backtrack finished jobs"
	echo "	$0 dags/TrioInconsistency/TrioInconsistency15DistantVRC.xml hcondor 1 20 1 \"--submit\" local TrioInconsistency/TrioInconsistency15DistantVRC_20110929T1726 TrioInconsistency/TrioInconsistency15DistantVRC_20110929T1726 "
	exit 1
fi

dagFile=$1
computingSiteName=$2
keepIntermediateFiles=$3
cleanupClustersSize=$4
shift
scratchType=$4
submitOption=$5
storageSiteName=$6
finalOutputDir=$7
submitFolderName=$8

#2013.2.12 no cleanup only when keepIntermediateFiles = 1
if test "$keepIntermediateFiles" = "1"; then
	submitOptionDefault="--submit --cleanup none"
fi

#2013.03.26
if test -z "$cleanupClustersSize"
then
	cleanupClustersSize=$cleanupClustersSizeDefault
fi

echo cleanupClustersSize is $cleanupClustersSize.


echo "Default submitOption is changed to $submitOptionDefault."

if test -z "$submitOption"
then
	submitOption=$submitOptionDefault
fi


if [ -z $storageSiteName ]; then
	storageSiteName=$storageSiteNameDefault
fi


if [ -z $finalOutputDir ]; then
	t=`python -c "import time; print time.asctime().split()[3].replace(':', '')"`
	month=`python -c "import time; print time.asctime().split()[1]"`
	day=`python -c "import time; print time.asctime().split()[2]"`
	year=`python -c "import time; print time.asctime().split()[-1]"`
	finalOutputDir=`python -c "import sys, os; pathLs= os.path.splitext(sys.argv[1])[0].split('/'); n=len(pathLs); print '/'.join(pathLs[-(n-1):])" $dagFile`.$year.$month.$day\T$t;
	echo Final output will be in $finalOutputDir
fi

if test -z "$submitFolderName"
then
	submitFolderName=$finalOutputDir
fi


runningWorkflowLogFname=$runningWorkflowLogFnameDefault
failedWorkflowLogFname=$failedWorkflowLogFnameDefault

echo "Submitting to $computingSiteName for computing."
echo "runningWorkflowLogFname is $runningWorkflowLogFname."
echo "failedWorkflowLogFname is $failedWorkflowLogFname."
echo "storageSiteName is $storageSiteName."
echo "Final workflow submit option is $submitOption."



# The following two lines shall be added to any condor cluster that do not use shared file system or 
# 	a filesystem that is not good at handling numerous small files in one folder.
#		<profile namespace="condor" key="should_transfer_files">YES</profile>
#		<profile namespace="condor" key="when_to_transfer_output">ON_EXIT_OR_EVICT</profile>
#
# create the site catalog
#		<profile namespace="env" key="PYTHONPATH">$PYTHONPATH:$PEGASUS_PYTHON_LIB_DIR</profile>
cat >sites.xml <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<sitecatalog xmlns="http://pegasus.isi.edu/schema/sitecatalog" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pegasus.isi.edu/schema/sitecatalog http://pegasus.isi.edu/schema/sc-3.0.xsd" version="3.0">
	<site  handle="local" arch="x86_64" os="LINUX">
		<grid  type="gt2" contact="localhost/jobmanager-fork" scheduler="Fork" jobtype="auxillary"/>
		<head-fs>
			<scratch>
				<local>
					<!-- this is used by condor local universe executables (i.e. pegasus-cleanup/transfer if you setup that way) -->
					<file-server protocol="file" url="file://" mount-point="$TOPDIR/scratch"/>
					<internal-mount-point mount-point="$TOPDIR/scratch" free-size="$freeSpace" total-size="$freeSpace"/>
				</local>
				<shared>
					<file-server protocol="file" url="file://" mount-point="$TOPDIR/scratch"/>
					<internal-mount-point mount-point="$TOPDIR/scratch" free-size="$freeSpace" total-size="$freeSpace"/>
				</shared>
			</scratch>
			<storage>
				<!-- this is where the final output will be staged (when the storageSiteName is "local", default) -->
				<local>
					<!-- this is used when pegasus-cleanup/transfer are set in condor local universe) -->
					<file-server protocol="file" url="file://" mount-point="$TOPDIR/$finalOutputDir"/>
					<internal-mount-point mount-point="$TOPDIR/$finalOutputDir" free-size="$freeSpace" total-size="$freeSpace"/>
				</local>
				<shared>
					<!-- this is used when pegasus-cleanup/transfer are set in condor vanilla universe) -->
					<file-server protocol="file" url="file://" mount-point="$TOPDIR/$finalOutputDir"/>
					<internal-mount-point mount-point="$TOPDIR/$finalOutputDir" free-size="$freeSpace" total-size="$freeSpace"/>
				</shared>
			</storage>
		</head-fs>
		<replica-catalog  type="LRC" url="rlsn://dummyValue.url.edu" />
		<profile namespace="env" key="PEGASUS_HOME" >$PEGASUS_HOME</profile>
		<profile namespace="env" key="HOME">$HOME</profile>
		<profile namespace="env" key="PATH" >$HOME_DIR/bin:$PATH</profile>
	</site>
	<site  handle="ycondor" arch="x86_64" os="LINUX">
		<grid  type="gt2" contact="localhost/jobmanager-fork" scheduler="Fork" jobtype="auxillary"/>
		<grid  type="gt2" contact="localhost/jobmanager-fork" scheduler="unknown" jobtype="compute"/>
		<head-fs>
			<scratch>
				<!-- this is where the computing output will be at for ycondor site -->
				<local>
					<!-- this is used by condor local universe executables (i.e. pegasus-cleanup/transfer if you setup that way) -->
					<file-server protocol="file" url="file://" mount-point="$TOPDIR/scratch"/>
					<internal-mount-point mount-point="$TOPDIR/scratch" free-size="$freeSpace" total-size="$freeSpace"/>
				</local>
				<shared>
					<!-- this is used by condor vanilla universe executables (most executables should be) -->
					<file-server protocol="file" url="file://" mount-point="$TOPDIR/scratch"/>
					<internal-mount-point mount-point="$TOPDIR/scratch" free-size="$freeSpace" total-size="$freeSpace"/>
				</shared>
			</scratch>
			<storage>
				<!-- this is where the final output will be staged when the storageSiteName is "ycondor", otherwise never used. -->
				<local>
					<!-- this is used when pegasus-cleanup/transfer are set in condor local universe) -->
					<file-server protocol="file" url="file://" mount-point="$TOPDIR/$finalOutputDir"/>
					<internal-mount-point mount-point="$TOPDIR/$finalOutputDir" free-size="$freeSpace" total-size="$freeSpace"/>
				</local>
				<shared>
					<!-- this is used when pegasus-cleanup/transfer are set in condor vanilla universe) -->
					<file-server protocol="file" url="file://" mount-point="$TOPDIR/$finalOutputDir"/>
					<internal-mount-point mount-point="$TOPDIR/$finalOutputDir" free-size="$freeSpace" total-size="$freeSpace"/>
				</shared>
			</storage>
		</head-fs>
		<replica-catalog  type="LRC" url="rlsn://dummyValue.url.edu" />
		<profile namespace="pegasus" key="style" >condor</profile>
		<profile namespace="condor" key="universe" >vanilla</profile>
		<profile namespace="env" key="PEGASUS_HOME" >$PEGASUS_HOME</profile>
		<profile namespace="env" key="HOME" >$HOME_DIR</profile>
		<profile namespace="env" key="PATH" >$HOME_DIR/bin:$PATH</profile>
	</site>
</sitecatalog>
EOF
# plan and submit the  workflow

export CLASSPATH=.:$PEGASUS_HOME/lib/pegasus.jar:$CLASSPATH
echo Java CLASSPATH is $CLASSPATH

#2013.03.30 "--force " was once added due to a bug. it'll stop file reuse.
commandLine="pegasus-plan -Dpegasus.file.cleanup.clusters.size=$cleanupClustersSize --conf pegasusrc --sites $computingSiteName --dax $dagFile --dir work --relative-dir $submitFolderName --output-site $storageSiteName --cluster horizontal $submitOption "

echo commandLine is $commandLine

$commandLine

exitCode=$?
#2013.04.24
if test $exitCode = "0"; then
	echo work/$submitFolderName >> $runningWorkflowLogFname
else
	echo work/$submitFolderName >> $failedWorkflowLogFname
fi

# add the option below for debugging
#	-vvvvv \
#	--cleanup none\

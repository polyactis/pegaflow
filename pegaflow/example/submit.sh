#!/bin/bash

# stop & exit if any error
set -e

TOPDIR=`pwd`
storage_site_default="local"
submit_option_default="--submit"
scratch_type_default="1"
cleanup_cluster_size_default=15
submit_dir="submit"

## two files to store the names of the successfully-submitted and submit-failed workflows respectively.
running_workflow_log_fname_default=runningWorkflows.txt
failed_workflow_log_fname_default=failedWorkflows.txt

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
	echo "  $0 dagFile computing_site [keep_intermediate_files] [cleanup_cluster_size] "
	echo "      [submit_option] [storage_site] [final_output_dir] [relative_submit_dir]"
	echo ""
	echo "Note:"
	echo "  - computing_site: the computing cluster on which the jobs will run. "
	echo "     Possible values: local (single-node), condor (computing cluster with condor setup). "
	echo "     The site in dagFile should match this."
	echo "  - keep_intermediate_files: 1 means no intermediate-file cleanup. Anything else (default) means cleanup."
	echo "     1 will change the default submit option ($submit_option_default) to --submit --cleanup none."
	echo "     This is useful if you want to keep all intermediate files."
	echo "  - cleanup_cluster_size: how many jobs get clustered into one job on each level."
	echo "     Default is $cleanup_cluster_size_default."
	echo "  - submit_option: options passed to pegasus-plan. Default is $submit_option_default. "
	echo "     '--submit' means pegasus will plan & submit the workflow."
	echo "     '--submit --cleanup none' means pegasus will not add intermediate-file cleanup jobs."
	echo "     If you set it to empty string, '', only planning will be done but no submission."
	echo "     This option overwrites the keep_intermediate_files option."
	echo "  - storage_site: the site to which final output is staged to. "
	echo "     Default is $storage_site_default. Almost never need to be changed."
	echo "  - final_output_dir: the directory that will contain the final output files."
	echo "     These files must be designated as transfer/stage_out=True in the workflow."
	echo "     If this folder doesn't exist, pegasus would create one. "
	echo "     Default is dagFile name (without the first folder if there is one) + year+date+time."
	echo "  - relative_submit_dir: the pegasus submit folder relative to ${submit_dir}/."
	echo "     This folder will contain all job submission files, job stdout/stderr output, logs, etc."
	echo "     Default is the same as final_output_dir."
	echo "  - final_output_dir and relative_submit_dir can be the same. But they must be different from previous workflows."
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
	echo "  #only planning (no running) by setting submit_option to an empty string (options in the middle do not matter)"
	echo "  $0 dags/TrioInconsistency15DistantVRC.xml condor 0 20 \"  \" "
	echo
	echo "  #run the workflow, keep intermediate files. Set the final_output_dir and relative_submit_dir."
	echo "  $0 dags/TrioInconsistency15DistantVRC.xml condor 1 20 \"--submit\" local "
	echo "     TrioInconsistency/TrioInconsistency15DistantVRC_20110929T1726 "
	echo "     TrioInconsistency/TrioInconsistency15DistantVRC_20110929T1726 "
	echo
	exit 1
fi

dagFile=$1
computing_site=$2
keep_intermediate_files=$3
cleanup_cluster_size=$4
submit_option=$5
storage_site=$6
final_output_dir=$7
relative_submit_dir=$8

#no cleanup when keep_intermediate_files = 1
if test "$keep_intermediate_files" = "1"; then
	submit_option_default="--submit --cleanup none"
fi

if test -z "$cleanup_cluster_size"
then
	cleanup_cluster_size=$cleanup_cluster_size_default
fi

echo cleanup_cluster_size is $cleanup_cluster_size.

echo "Default submit_option is changed to $submit_option_default."

if test -z "$submit_option"
then
	submit_option=$submit_option_default
fi

if [ -z $storage_site ]; then
	storage_site=$storage_site_default
fi

# The stageout folder that will contain all the final output.
if [ -z $final_output_dir ]; then
	#time without :. like 16:30:30 => 163030
	t=`python3 -c "import time; print(time.asctime().split()[3].replace(':', ''))"`
	month=`python3 -c "import time; print(time.asctime().split()[1])"`
	day=`python3 -c "import time; print(time.asctime().split()[2])"`
	year=`python3 -c "import time; print(time.asctime().split()[-1])"`
    #remove the first folder (usually "dags/") in the dag file path
	final_output_dir=`python3 -c "import sys, os; pathLs=os.path.splitext(sys.argv[1])[0].split('/'); n=len(pathLs); print('/'.join(pathLs[-(n-1):]))" $dagFile`.$year.$month.$day\T$t;
	echo "Final output will be in $final_output_dir"
fi

if test -z "$relative_submit_dir"
then
	relative_submit_dir=$final_output_dir
fi

running_workflow_log_fname=$running_workflow_log_fname_default
failed_workflow_log_fname=$failed_workflow_log_fname_default

echo "Submitting to $computing_site for computing."
echo "storage_site is $storage_site."
echo "running_workflow_log_fname is $running_workflow_log_fname."
echo "failed_workflow_log_fname is $failed_workflow_log_fname."
echo "The workflow submit option is $submit_option."
echo "relative_submit_dir is $relative_submit_dir."
echo "PYTHONPATH is $PYTHONPATH."

# The following two lines shall be added to any condor cluster that do not use shared file system or 
# 	a filesystem that is not good at handling numerous small files in one folder.
#		<profile namespace="condor" key="should_transfer_files">YES</profile>
#		<profile namespace="condor" key="when_to_transfer_output">ON_EXIT_OR_EVICT</profile>
# Example to set the PYTHONPATH:
#		<profile namespace="env" key="PYTHONPATH">$PYTHONPATH:$PEGASUS_PYTHON_LIB_DIR</profile>

# 20210616 site catalog will be generated by the workflow itself. No longer needed.
## create the site catalog
#cat >sites.yml <<EOF
#pegasus: "5.0"
#sites:
#- name: "condor"
#  arch: "x86_64"
#  os.type: "linux"
#  directories:
#  - type: "sharedScratch"
#    path: "$TOPDIR/scratch"
#    fileServers:
#    - {url: "file://$TOPDIR/scratch", operation: all}
#  profiles:
#    env:
#      PEGASUS_HOME: "$PEGASUS_HOME"
#      HOME: "$HOME"
#      PATH: "$HOME_DIR/bin:$PATH"
#      PYTHONPATH: "$PYTHONPATH"
#      LC_ALL: "$LC_ALL"
#    condor:
#      universe: "vanilla"
#    pegasus: {style: condor, data.configuration: sharedfs}
#- name: "local"
#  directories:
#  - type: "sharedScratch"
#    path: "$TOPDIR/scratch"
#    fileServers:
#    - {url: "file://$TOPDIR/scratch", operation: all}
#  - type: "localStorage"
#    path: "$TOPDIR/output/"
#    fileServers:
#    - {url: "file://$TOPDIR/scratch", operation: all}
#  profiles:
#    env:
#      PEGASUS_HOME: "$PEGASUS_HOME"
#      HOME: "$HOME"
#      PATH: "$HOME_DIR/bin:$PATH"
#      PYTHONPATH: "$PYTHONPATH"
#      LC_ALL: "$LC_ALL"
#EOF

## plan and submit the  workflow
export CLASSPATH=.:$PEGASUS_HOME/lib/pegasus.jar:$CLASSPATH
echo Java CLASSPATH is $CLASSPATH
#2013.03.30 "--force " was once added due to a bug. it'll stop file reuse.
command_line="pegasus-plan -Dpegasus.file.cleanup.clusters.size=$cleanup_cluster_size \
	--conf pegasus.properties \
	--sites $computing_site --output-site $storage_site \
	--dir ${submit_dir} --relative-dir $relative_submit_dir --verbose \
	--output-dir ${final_output_dir} \
	--cluster horizontal $submit_option $dagFile"

# add the option below for debugging
#	-vvvvv \
#	--cleanup none\

echo command_line is $command_line

$command_line

exit_code=$?
if test $exit_code = "0"; then
	echo ${submit_dir}/$relative_submit_dir >> $running_workflow_log_fname
else
	echo ${submit_dir}/$relative_submit_dir >> $failed_workflow_log_fname
fi


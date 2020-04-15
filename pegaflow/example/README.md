# This folder contains an example to inherit Workflow.py.

[WordCountFiles.py](WordCountFiles.py) is an Object-Oriented example that runs `wc` (word-count) on all files with a given suffix in an input folder.

[WCFiles_Function.py](WCFiles_Function.py) provides the same function as [WordCountFiles.py](WordCountFiles.py), but is written in a procedural-programming way. No classes.

[submit.sh](submit.sh) is a workflow submit script that invokes pegasus-plan. It also generates `sites.xml`, a configuration file specific to your workflow (where to store job files, where to run jobs, where to transfer final output). `sites.xml` will be copied into the workflow work folder (work/...), once a workflow is planned and submitted. Overwriting it is OK.

[pegasusrc](pegasusrc) contains a few pre-set Pegasus settings that [submit.sh](submit.sh) will read from.

A user should copy both [submit.sh](submit.sh) and [pegasusrc](pegasusrc) to his/her running environment.


To get help on the arguments of [WordCountFiles.py](WordCountFiles.py) or [WCFiles_Function.py](WCFiles_Function.py):
```bash
./WordCountFiles.py -h

./WCFiles_Function.py -h
```

To run on a condor cluster (https://research.cs.wisc.edu/htcondor/ must be setup beforehand):

```bash
# Count all .py files in /usr/lib/python3.6
# "-C 10" enables job clustering. 10 jobs into one job. 'wc' runs fast. Better to cluster them.
$ ./WordCountFiles.py -i /usr/lib/python3.6/ --inputSuffixList .py -l condor -o wc.python.code.xml -C 10

# OR run this. WCFiles_Function.py has the same function as WordCountFiles.py but is written in a procedural-programming way.
$ ./WCFiles_Function.py -i /usr/lib/python3.6/ --inputSuffixList .py -l condor -o wc.python.code.xml -C 10


# Plan and submit the workflow.
# Try "./submit.sh condor ./wc.python.code.xml 1" if you want to keep intermediate files.
$ ./submit.sh condor ./wc.python.code.xml

# A work folder work/... is created to house job description/submit files, job status files, etc.

# A running folder scratch/... is created.
#  All input files will be symlinked or copied into this folder.
#  All pegasus jobs will run inside that folder and also output in that folder.

# If the workflow succeeds in the end, final output will be copied into a new folder, ./..., in the current directory.

# Check the status of the workflow:
$ pegasus_status work/...
STAT  IN_STATE  JOB                                                                                                           
Run      00:13  wc_python_condor_2-0 ( /home/user/src/pegaflow/pegaflow/example/work/wc.python.code.2020.Apr.1T113305 )       
Idle     00:08   ┣━merge_pegasus-pipe2File-1_0_PID1_ID27                                                         
Idle     00:08   ┣━merge_pegasus-pipe2File-1_0_PID1_ID26                                                     
Idle     00:08   ┣━merge_pegasus-pipe2File-1_0_PID1_ID29                                    
Idle     00:08   ┣━merge_pegasus-pipe2File-1_0_PID1_ID28                                  
Idle     00:08   ┣━merge_pegasus-pipe2File-1_0_PID1_ID23                                                  
Idle     00:03   ┣━merge_pegasus-pipe2File-1_0_PID1_ID22                         
Idle     00:03   ┣━merge_pegasus-pipe2File-1_0_PID1_ID25                                                  
Idle     00:03   ┣━merge_pegasus-pipe2File-1_0_PID1_ID24                                                         
Idle     00:03   ┣━merge_pegasus-pipe2File-1_0_PID1_ID1                                                          
Idle     00:03   ┗━merge_pegasus-pipe2File-1_0_PID1_ID2                                     
Summary: 11 Condor jobs total (I:10 R:1)                                                               
                                                                                                               
UNREADY   READY     PRE  QUEUED    POST SUCCESS FAILURE %DONE                                            
      2      26       0      10       0       6       0  13.6                                                          
Summary: 1 DAG total (Running:1)


# If it failed, run this to check which jobs failed:
$ pegasus-analyzer work/...

# Re-submit it after fixing program bugs. It will start only the failed jobs.
$ pegasus-run work/...

```

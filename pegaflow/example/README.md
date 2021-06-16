# 1. An example to inherit Workflow.py

- [1. An example to inherit Workflow.py](#1-an-example-to-inherit-workflowpy)
  - [1.1. Test on a Condor cluster](#11-test-on-a-condor-cluster)

[WordCountFiles.py](WordCountFiles.py) is an Object-Oriented example that runs `wc` (word-count) on all files with a given suffix in an input folder.

[WCFiles_Function.py](WCFiles_Function.py) provides the same function as [WordCountFiles.py](WordCountFiles.py), but is written in a procedural-programming way. No classes.

[submit.sh](submit.sh) is a workflow submit script that invokes pegasus-plan. It also generates `sites.xml`, a configuration file specific to your workflow (where to store job files, where to run jobs, where to transfer final output). `sites.xml` will be copied into the workflow submit folder (submit/...), during the planning phase. Overwriting it is OK.

[pegasusrc](pegasusrc) contains a few pre-set Pegasus settings that [submit.sh](submit.sh) will read from.

A user should copy both [submit.sh](submit.sh) and [pegasusrc](pegasusrc) to his/her running environment.

To get help on the arguments of [WordCountFiles.py](WordCountFiles.py) or [WCFiles_Function.py](WCFiles_Function.py):

```bash
./WordCountFiles.py -h

./WCFiles_Function.py -h
```

## 1.1. Test on a Condor cluster

[Condor](https://research.cs.wisc.edu/htcondor/) and [Pegasus](http://pegasus.isi.edu/) must be installed and properly setup beforehand:

```bash
# Count all .py files in /usr/lib/python3.6
# "-C 10" enables job clustering. 10 jobs into one job. 'wc' runs fast. Better to cluster them.
$ ./WordCountFiles.py -i /usr/lib/python3.6/ --inputSuffixList .py -l condor -o wc.python.code.xml -C 10

# OR run this. WCFiles_Function.py has the same function as WordCountFiles.py but is written in a procedural-programming way.
$ ./WCFiles_Function.py -i /usr/lib/python3.6/ --inputSuffixList .py -l condor -o wc.python.code.xml -C 10

# Plan and submit the workflow.
# Try "./submit.sh ./wc.python.code.xml condor 1" if you want to keep intermediate files.
$ ./submit.sh ./wc.python.code.xml condor

# A submit folder submit/wc.python... is created to house job description/submit files, job status files, etc.

# A scratch folder scratch/wc.python... is created.
#  All input files will be symlinked or copied into the scatch folder.
#  All pegasus jobs will run inside that folder and also output in the scratch folder.

# If the workflow succeeds in the end, final output will be copied into a new folder, output/wc.python...

# Check the status of the workflow:
$ pegasus_status submit/wc.python.*
STAT  IN_STATE  JOB                                                                                                           
Run      00:13  wc_python_condor_2-0 ( /home/user/src/pegaflow/pegaflow/example/submit/wc.python.code.2020.Apr.1T113305 )
...
Idle     00:03   ┣━merge_pegasus-pipe2File-1_0_PID1_ID1
Idle     00:03   ┗━merge_pegasus-pipe2File-1_0_PID1_ID2
Summary: 11 Condor jobs total (I:10 R:1)

UNREADY   READY     PRE  QUEUED    POST SUCCESS FAILURE %DONE
      2      26       0      10       0       6       0  13.6
Summary: 1 DAG total (Running:1)

# If it failed, run this to check which jobs failed:
$ pegasus-analyzer submit/wc.python...

# Re-submit it after fixing program bugs. It will start only the failed jobs.
$ pegasus-run submit/...

```

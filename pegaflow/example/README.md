# This folder contains examples to use Workflow.py.

`submit.sh` is a workflow submit script that invokes pegasus-plan. It also generates `sites.xml`, a configuration file specific to your workflow (where to store job files, where to run jobs, where to transfer final output). `sites.xml` will be copied into the workflow work folder (work/...), once a workflow is planned and submitted. Overwriting it is OK.

pegasusrc contains a few pre-set Pegasus settings that `submit.sh` will read from.

`WordCountFiles.py` is a Pegasus workflow that runs `wc` (word-count) on all files with a given suffix in an input folder.

To get help on the arguments of `WordCountFiles.py`:
```bash
./WordCountFiles.py -h
```

To run on a condor cluster (https://research.cs.wisc.edu/htcondor/ must be setup beforehand):

```bash
# Count all .py files in /usr/lib/python3.6
# "-C 10" enables job clustering. 10 jobs into one job. 'wc' runs fast. Better to cluster them.
./WordCountFiles.py -i /usr/lib/python3.6/ --inputSuffixList .py -l condor -o wc.python.code.xml -C 10
./submit.sh condor ./wc.python.code.xml

# A work folder work/... is created to house job description/submit files, job status files, etc.

# A running folder scratch/... is created.
#  All input files will be symlinked or copied into this folder.
#  All pegasus jobs will run inside that folder and also output in that folder.
#  If the workflow succeeds in the end, final output will be copied into a new folder, ./..., in the current directory.

# Check the status of the workflow:
pegasus_status work/...

# If it failed, run this to check which jobs failed:
pegasus-analyzer work/...

# Re-submit it after fixing program bugs:
pegasus-run work/...

```

A user should copy the `submit.sh` and pegasusrc to his/her running environment.

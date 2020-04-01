# This folder contains examples to use Workflow.py.

submit.sh is a workflow submit script that invokes pegasus-plan. It also generates sites.xml, a catalog file for your computing environment.

pegasusrc contains a few pre-set Pegasus settings that submit.sh will read from.

WordCountFiles.py is a Pegasus workflow that runs "wc" (word-count) on all files with a given suffix in an input folder.

To run on a single node (condor still needs to be installed):
```bash
./WordCountFiles.py -i /usr/lib/python3.6/ --inputSuffixList .py -l local -o /tmp/count.python.code.xml
./submit.sh local ./example.xml
```

To run on a condor cluster (https://research.cs.wisc.edu/htcondor/ must be setup beforehand):

```bash
./WordCountFiles.py -i /usr/lib/python3.6/ --inputSuffixList .py -l condor -o /tmp/count.python.code.xml
./submit.sh condor ./example.xml
```


A user should copy the submit.sh and pegasusrc to his/her running environment.

# This folder contains examples to use Workflow.py.

submit.sh is a workflow submit script that invokes pegasus-plan. It also generates sites.xml, a catalog file for your computing environment.

pegasusrc contains a few pre-set Pegasus settings that submit.sh will read from.

WordCountFiles.py is a Pegasus workflow that runs "wc" (word-count) on all files with a given suffix in an input folder.

To get help on the arguments of WordCountFiles.py:
```bash
./WordCountFiles.py -h
```

To run on a single node (condor still needs to be installed):
```bash
./WordCountFiles.py -i /usr/lib/python3.6/ --inputSuffixList .py -l local -o count.python.code.xml
./submit.sh local ./count.python.code.xml
```

To run on a condor cluster (https://research.cs.wisc.edu/htcondor/ must be setup beforehand):

```bash
./WordCountFiles.py -i /usr/lib/python3.6/ --inputSuffixList .py -l condor -o count.python.code.xml
./submit.sh condor ./count.python.code.xml
```

Enable job clustering, 10 jobs into one job.
```bash
./WordCountFiles.py -i /usr/lib/python3.6/ --inputSuffixList .py -l condor -o count.python.code.xml -C 10
./submit.sh condor ./count.python.code.xml
```

A user should copy the submit.sh and pegasusrc to his/her running environment.

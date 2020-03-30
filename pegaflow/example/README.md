# This folder contains examples to use Workflow.py.

submit.sh is a workflow submit script that invokes pegasus-plan. It also generates sites.xml, a catalog file for your computing environment.

pegasusrc contains a few pre-set Pegasus settings that submit.sh will read from.


To run on a single node:
```bash
./ExampleWorkflow.py -l local -o ./example.xml

./submit.sh local ./example.xml
```


To run on a condor cluster (https://research.cs.wisc.edu/htcondor/ must be setup beforehand):
```bash
./ExampleWorkflow.py -l condor -o ./example.xml

./submit.sh condor ./example.xml
```


A user should copy the submit.sh and pegasusrc to his/her running environment.

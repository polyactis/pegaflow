# This folder contains an example on how to inherit Workflow.py.


submit.sh is a submit script that also generates sites.xml, a configuration file for your condor pool.

pegasusrc contains settings of Pegasus that submit.sh will read from.

To test-run:

```bash
./ExampleWorkflow.py -l ycondor -o ./example.xml

./submit.sh ycondor ./example.xml
```

A user should copy the submit.sh and pegasusrc to his/her pegasus folder.

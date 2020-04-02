# Pegasus Workflow Management System Python3 API

Pegaflow, https://github.com/polyactis/pegaflow, is a package of the Python3 APIs for Pegasus WMS (http://pegasus.isi.edu/). Pegasus(<5.0) offers Python2 support only. Pegasus allows a developer to connect dependent computing jobs into a DAG (Directed Acyclic Graph) and run jobs according to the dependency.

[Workflow.py](pegaflow/Workflow.py) is the key difference from the official Pegasus Python APIs. Inheriting [Workflow.py](pegaflow/Workflow.py), users can write Pegasus workflows in an Object-Oriented way. It significantly reduces the amount of coding in writing a Pegasus workflow.

Pegasus jobs do NOT support UNIX pipes while many UNIX programs can only output to stdout. A shell wrapper, [pegaflow/shell/pipeCommandOutput2File.sh](pegaflow/shell/pipeCommandOutput2File.sh), is offered to redirect the output (stdout) of a program to a file. [pegaflow/shell/](pegaflow/shell/) contains a few other useful shell scripts.

* The DAX API (v3) and the helper class Workflow.py
* The monitoring API
* The Stampede database API
* The Pegasus statistics API
* The Pegasus plots API
* Miscellaneous Pegasus utilities
* The Pegasus service, including the ensemble manager and dashboard

This package's source code is adapted from https://github.com/pegasus-isi/pegasus, version 4.9.1,


# Installation

Install pegaflow:

```python
pip3 install --upgrade pegaflow
```

Pegasus and HTCondor (Condor) are only required on computers where you intend to submit and run workflows. 

On computers where only DAX (DAG xml file) writing will be practiced, no need to install them.

* Pegasus https://github.com/pegasus-isi/pegasus
* HTCondor https://research.cs.wisc.edu/htcondor/, the underlying job scheduler.

If a user intends to use Non-DAX Pegasus APIs, the following Python packages need to be installed as well.

* "Werkzeug==0.14.1",
* "Flask==0.12.4",
* "Jinja2==2.8.1",
* "SQLAlchemy",
* "Flask-Cache==0.13.1",
* "requests==2.18.4",
* "MarkupSafe==1.0",
* "boto==2.48.0",
* "pam==0.1.4",
* "plex==2.0.0dev",
* "future"

# Examples

Check [pegaflow/example/](pegaflow/example/) for examples how to inherit [Workflow.py](pegaflow/Workflow.py) and run Pegasus workflows.

Here is a snippet of [pegaflow/example/WordCountFiles.py](pegaflow/example/WordCountFiles.py):

```python

#!/usr/bin/env python3

from pegaflow.DAX3 import File
from pegaflow.Workflow import Workflow, getAbsPathOutOfExecutable

# path to the source code's folder.
# a convenient variable to add executables from the same folder.
src_dir = os.path.dirname(os.path.abspath(__file__))

class WordCountFiles(Workflow):
    __doc__ = __doc__
    # Each entry of pathToInsertHomePathList should contain %s, i.e. '%s/bin/myprogram'
    #  and will be expanded to be '/home/user/bin/myprogram'.
    # Child classes can add stuff into this list.
    pathToInsertHomePathList = []
    def __init__(self, input_folder=None, inputSuffixList=None, output_path=None, \
        pegasusFolderName=None, \
        site_handler=None, input_site_handler=None, \
        max_walltime=4320, cluster_size=1,\
        ):
        #call the parent class first
        Workflow.__init__(self, inputSuffixList=inputSuffixList, output_path=output_path, \
            pegasusFolderName=pegasusFolderName, \
            site_handler=site_handler, input_site_handler=input_site_handler,\
            cluster_size=cluster_size, \
            tmpDir='/tmp/', max_walltime=max_walltime, \
            javaPath=None, jvmVirtualByPhysicalMemoryRatio=1.2,\
            debug=False, needSSHDBTunnel=False, report=False)
        self.input_folder = input_folder
    
    def registerExecutables(self):
        Workflow.registerExecutables(self)
        # self.sleep can be used as an Pegasus Executable after self.addExecutableFromPath().
        self.addExecutableFromPath(path="/bin/sleep", name='sleep', clusterSizeMultiplier=1)
        ...

    def run(self):
        ## setup_run() will call registerExecutables()
        self.setup_run()
        
        # Register all .py files from the input folder
        #  self.registerOneInputFile('/tmp/abc.txt') can be used to register one input file.
        inputData = self.registerFilesOfInputDir(inputDir=self.input_folder, \
            input_site_handler=self.input_site_handler, inputSuffixSet=self.inputSuffixSet)
        
        ...
        
        mergedOutputFile = File("merged.txt")
        # request 500MB memory, 30 minutes run time (walltime).
        # executable=self.mergeWC tells this function to use a different executable.
        #  In order to give this job a different name.
        #  If executable=None or not given, self.pipeCommandOutput2File is used.
        mergeJob= self.addPipeCommandOutput2FileJob(executable=self.mergeWC,\
            commandFile=catCommand, outputFile=mergedOutputFile, \
            transferOutput=True, 
            job_max_memory=500, walltime=30)

        for jobData in inputData.jobDataLs:
            outputFile = File(f'{jobData.file.name}.wc.output.txt')
            ## wc each input file
            # Argument "executable" is not given, use self.pipeCommandOutput2File.
            wcJob = self.addPipeCommandOutput2FileJob(
                commandFile=wcCommand,
                outputFile=outputFile,
                parentJob=None, parentJobLs=None, 
                extraArgumentList=[jobData.file], \
                extraDependentInputLs=[jobData.file], extraOutputLs=None, \
                transferOutput=False)
            # add wcJob.output (outputFile passed to addPipeCommandOutput2FileJob() above) as the input of mergeJob.
            #   It appends input to the end of a job's exising arguments).
            #   wcJob.output will be a dependent input of mergeJob.
            # addInputToMergeJob() also adds wcJob as a parent of mergeJob.
            self.addInputToMergeJob(mergeJob=mergeJob, inputF=wcJob.output, inputArgumentOption="",\
                            parentJobLs=[wcJob])
        # a sleep job to slow down the workflow for 30 seconds
        # sleepJob has no output.
        sleepJob = self.addGenericJob(executable=self.sleep, extraArgumentList=['30s'])
        # add sleepJob as mergeJob's parent.
        self.addInputToMergeJob(mergeJob=mergeJob, parentJobLs=[sleepJob])

        # end_run() will output the DAG to output_path
        self.end_run()


if __name__ == '__main__':
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("-i", "--input_folder", type=str, required=True,
        help="The folder that contains input files.")
    ap.add_argument("-l", "--site_handler", type=str, required=True,
        help="The name of the computing site where the jobs run and executables are stored. "
        "Check your Pegasus configuration in submit.sh.")
    #additional arguments
    ...
    args = ap.parse_args()
    instance = WordCountFiles(input_folder=args.input_folder, inputSuffixList=args.inputSuffixList, \
        output_path=args.output_path, \
        pegasusFolderName=args.pegasusFolderName, \
        site_handler=args.site_handler, input_site_handler=args.input_site_handler, \
        cluster_size=args.cluster_size, \
        max_walltime=args.max_walltime, \
        )
    instance.run()

```

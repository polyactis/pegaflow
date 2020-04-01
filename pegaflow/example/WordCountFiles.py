#!/usr/bin/env python3
"""
An example workflow that counts   is a class for other programs to inherit and helps to simplify pegasus workflow dax writing.
"""
import sys, os
from pegaflow.DAX3 import File, PFN, Profile, Namespace, Link, Use, Job, Dependency
from pegaflow.Workflow import Workflow, getAbsPathOutOfExecutable

# path to the source code's folder
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
        """
        """
        Workflow.registerExecutables(self)
        # self.sleep can be used as an Pegasus Executable after self.addExecutableFromPath().
        self.addExecutableFromPath(path="/bin/sleep", name='sleep', clusterSizeMultipler=1)
        # You can also give a different name to the same executable.
        # The Pegasus jobs are named after the executables.
        # Useful when you want to give the jobs different names.
        # For example:
        #  Java jobs need the same java executable but may be doing very different things.
        self.addExecutableFromPath(path="/bin/sleep", name='siesta', clusterSizeMultipler=1)

        # Add a 2nd pipeCommandOutput2File executable with a different name.
        #   This one will run "cat" to merge all output.
        self.addExecutableFromPath(path=getAbsPathOutOfExecutable(self.pipeCommandOutput2File), \
                name='mergeWC', clusterSizeMultipler=1)

    def run(self):
        ## setup_run() will call registerExecutables()
        self.setup_run()
        
        # Register all .py files from the input folder
        #  self.registerOneInputFile('/tmp/abc.txt') can be used to register one input file.
        inputData = self.registerFilesOfInputDir(inputDir=self.input_folder, \
            input_site_handler=self.input_site_handler, inputSuffixSet=self.inputSuffixSet)
        
        # Pegasus jobs do NOT allow pipes. So use pipeCommandOutput2File (already registered in Workflow.py).
        # register wc and cat as they will be used by pipeCommandOutput2File.
        wcCommand = self.registerOneExecutableAsFile(path="/usr/bin/wc")
        catCommand = self.registerOneExecutableAsFile(path="/bin/cat")
        
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
    ap.add_argument("-j", "--input_site_handler", type=str,
        help="It is the name of the site that has all the input files."
        "Possible values can be 'local' or the same as site_handler. If not sure, leave it alone."
        "If not given, it is asssumed to be the same as site_handler "
        " and the input files will be symlinked into the running folder."
        "If the job submission node does not share a file system with the computing site, input_site_handler=local,"
        " and the input files will be transferred to the computing site by pegasus-transfer (need setup).")
    ap.add_argument("-C", "--cluster_size", type=int, default=1,
        help="Default: %(default)s. "
        "This number decides how many of pegasus jobs should be clustered into one job. "
        "Good if your workflow contains many quick jobs. "
        "It will reduce Pegasus monitor I/O.")
    ap.add_argument("-o", "--output_path", type=str, required=True,
        help="The path to the output file that will contain the Pegasus DAG.")
    ap.add_argument("-F", "--pegasusFolderName", type=str,
        help='The path relative to the workflow running root. '
        'This folder will contain pegasus input & output. '
        'It will be created during the pegasus staging process. '
        'It is useful to separate multiple sub-workflows. '
        'If empty or None, everything is in the pegasus root.')
    ap.add_argument("--inputSuffixList", type=str, required=True,
        help='Coma-separated list of input file suffices. Used to exclude input files.'
        'If None, no exclusion. The dot is part of the suffix, i.e. .tsv, not tsv.'
        'Common zip suffices (.gz, .bz2, .zip, .bz) will be ignored in obtaining the suffix.')
    ap.add_argument("--max_walltime", type=int, default=4320,
        help='Default: %(default)s. Maximum run time (minutes) for any job. 4320=3 days.'
        'Used in addGenericJob().')
    args = ap.parse_args()
    instance = WordCountFiles(input_folder=args.input_folder, inputSuffixList=args.inputSuffixList, \
        output_path=args.output_path, \
        pegasusFolderName=args.pegasusFolderName, \
        site_handler=args.site_handler, input_site_handler=args.input_site_handler, \
        cluster_size=args.cluster_size, \
        max_walltime=args.max_walltime, \
        )
    instance.run()

#!/usr/bin/env python3
"""
An example workflow that counts   is a class for other programs to inherit and helps to simplify pegasus workflow dax writing.
"""
import sys, os
from pegaflow.DAX3 import File, PFN, Profile, Namespace, Link, Use, Job, Dependency
from pegaflow.Workflow import Workflow

sys.path.insert(0, os.path.expanduser('~/lib/python'))

class ExampleWorkflow(Workflow):
    __doc__ = __doc__
    # Each entry of pathToInsertHomePathList should contain %s, i.e. '%s/bin/myprogram'
    #  and will be expanded to be '/home/user/bin/myprogram'.
    # Child classes can add stuff into this list.
    pathToInsertHomePathList = []
    def __init__(self, input_folder=None, site_handler=None, input_site_handler=None, clusters_size=30, \
            pegasusFolderName=None, output_path=None):
        #call the parent class first
        Workflow.__init__(self, site_handler=site_handler, input_site_handler=input_site_handler,\
            clusters_size=clusters_size, pegasusFolderName=pegasusFolderName, \
            inputSuffixList=None, output_path=output_path, \
            tmpDir='/tmp/', max_walltime=4320, jvmVirtualByPhysicalMemoryRatio=1.2,\
            debug=False, needSSHDBTunnel=False, report=False)
        self.input_folder = input_folder
    
    def registerExecutables(self):
        """
        """
        Workflow.registerExecutables(self)
        self.addExecutableFromPath(path="/bin/cat", name='cat', clusterSizeMultipler=1)
        self.addExecutableFromPath(path="/usr/bin/wc", name='wc', clusterSizeMultipler=1)
        self.addExecutableFromPath(path="/bin/sleep", name='sleep', clusterSizeMultipler=1)

    def run(self):
        ## setup_run() will call registerExecutables()
        self.setup_run()
        
        inputData = self.registerFilesOfInputDir(inputDir=self.input_folder, \
            input_site_handler=self.input_site_handler, inputSuffixSet='.py')
        wcExecutable = self.registerOneExecutableAsFile(path="/usr/bin/wc")
        for jobData in inputData.jobDataLs:
            wcJob = self.addPipeCommandOutput2FileJob(executable=self.pipeCommandOutput2File, 
                commandFile=wcExecutable,
                outputFile=File(''),
                parentJob=None, parentJobLs=None, 
                extraArgumentList=[wcExecutable, jobData.file], \
                extraDependentInputLs=[jobData.file], extraOutputLs=None, \
                transferOutput=False)
        sleepJob = self.addGenericJob(executable=self.sleep, extraArguments='30s')
        # end_run() will output the DAG to output_path
        self.end_run()


if __name__ == '__main__':
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("-l", "--site_handler", type=str, required=True,
            help="The name of the computing site where the jobs run and executables are stored. "
            "Check your Pegasus configuration in submit.sh.")
    ap.add_argument("-j", "--input_site_handler", type=str,
            help="It is the name of the site that has all the input files."
            "Possible values can be 'local' or same as site_handler."
            "If not given, it is asssumed to be the same as site_handler and the input files will be symlinked into the running folder."
            "If input_site_handler=local, the input files will be transferred to the computing site by pegasus-transfer.")
    ap.add_argument("-C", "--clusters_size", type=int, default=30,
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
    ap.add_argument("--inputSuffixList", type=str,
            help='Coma-separated list of input file suffices. Used to exclude input files.'
            'If None, no exclusion. The dot is part of the suffix, .tsv not tsv.'
            'Common zip suffices (.gz, .bz2, .zip, .bz) will be ignored in obtaining the suffix.')
    ap.add_argument("--tmpDir", type=str, default='/tmp/',
            help='Default: %(default)s. A local folder for some jobs (MarkDup) to store temp data.'
                '/tmp/ can be too small sometimes.')
    ap.add_argument("--max_walltime", type=int, default=4320,
            help='Default: %(default)s. Maximum wall time for any job, in minutes. 4320=3 days.'
            'Used in addGenericJob(). Most clusters have upper limit for runtime.')
    ap.add_argument("--jvmVirtualByPhysicalMemoryRatio", type=float, default=1.2,
            help='Default: %(default)s. '
            'If a job virtual memory (usually 1.2X of JVM resident memory) exceeds request, '
            "it will be killed on some clusters. This will make sure your job requests enough memory.")
    ap.add_argument("--debug", action='store_true',
            help='Toggle debug mode.')
    ap.add_argument("--report", action='store_true',
            help="Toggle verbose mode. Default: %(default)s.")
    ap.add_argument("--needSSHDBTunnel", action='store_true',
            help="If all DB-interacting jobs need a ssh tunnel to access a database that is inaccessible to computing nodes.")
    args = ap.parse_args()
    instance = ExampleWorkflow(site_handler=args.site_handler, input_site_handler='ycondor', clusters_size=30, \
            pegasusFolderName='folder', inputSuffixList=None, output_path=args.output_path, \
            tmpDir='/tmp/', max_walltime=4320, jvmVirtualByPhysicalMemoryRatio=1.2,\
            debug=False, needSSHDBTunnel=False, report=False)
    instance.run()
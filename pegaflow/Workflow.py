#!/usr/bin/env python3
"""
1. Class Workflow is a class for other programs to inherit and simplify pegasus
    workflow dax generation.
2. Functions that help to simplify coding:
"""
import sys, os
import logging
from pathlib import Path
from typing import Dict, List, Optional, TextIO, Union

# --- Import Pegasus API -----------------------------------------------------------
from .api import Directory, File, FileServer, Job, Operation, \
    Properties, ReplicaCatalog, Site, SiteCatalog, Transformation, \
    TransformationCatalog
from .api import Arch, OS
from .api import Workflow as PegaWorkflow

from . import PassingData, getListOutOfStr
from . import getRealPrefixSuffix
from . import setJobResourceRequirement, getExecutableClusterSize
from . import create_pegasus_properties, create_site_catalog

src_dir = os.path.dirname(os.path.abspath(__file__))


class Workflow(PegaWorkflow):
    __doc__ = __doc__
    # Each entry of pathToInsertHomePathList should be a relative path.
    #  'bin/myprogram',
    #  and will be expanded to be '/home/user/bin/myprogram'.
    # Child classes can add stuff into this list.
    pathToInsertHomePathList = []
    home_path = ""
    
    pegasus_props:Properties = None

    # the folder to hold everything about the workflow, which is the parent folder of the output dag file.
    wf_dir:str = None
    
    def __init__(self,
        input_path: str = None,
        inputSuffixList: list = None,
        pegasusFolderName: str = 'folder',
        output_path: str = None,
        
        tmpDir: str = '/tmp/',
        max_walltime: int = 4320,
        home_path: str = None,
        javaPath: str = None,
        jvmVirtualByPhysicalMemoryRatio: float = 1.2,

        site_handler: str = None,
        input_site_handler: str = None,
        cluster_size: int = 1,
        
        needSSHDBTunnel: bool = False,
        direct_run=False,
        debug=False, report=False, commit: bool = False):
        """
        site_handler: The name of the computing site where the jobs run and
            executables are stored. Check your Pegasus configuration.
        input_site_handler: 'local or same as site_handler. It is the name
            of the site that has all the input files.'
            'If it is the same as site_handler, the input files will be
                symlinked.'
            'If input_site_handler=local, input files will be transferred to
                the computing cluster by pegasus-transfer.'
        cluster_size: 'The number of pegasus jobs that should be clustered
            into one job. '
            'Good if your workflow contains many quick jobs.
            It will reduce Pegasus monitor I/O.'
        pegasusFolderName: 'the path relative to the pegasus workflow root.
            This folder will contains pegasus input & output.'
            'It will be created during the pegasus staging process.
            It is useful to separate multiple sub-workflows.'
            'If empty or None, everything is in the pegasus root.'
        inputSuffixList: 'coma-separated list of input file suffices.
            If None, any suffix.'
            'Suffix include the dot, (i.e. .tsv).
            Typical zip suffices are excluded (.gz, .bz2, .zip, .bz).'
        output_path: 'the path to the output file that will
            contain the Pegasus DAG.'
        tmpDir: 'a local folder for some jobs (MarkDup) to store temp data.
            /tmp/ can be too small sometimes.'
        max_walltime: 'maximum wall time any job could have, in minutes.
            20160=2 weeks.'
            'used in addGenericJob().'
        jvmVirtualByPhysicalMemoryRatio: "if a job's virtual memory
            (usually 1.2X of JVM resident memory) exceeds request, "
            "it will be killed on some clusters, hoffman2.
            This will make sure your job requests enough memory
             from the job scheduler."
        direct_run: Run the workflow directly, with no need to run pegasus-plan.
        debug: 'toggle debug mode.'
        needSSHDBTunnel: 'If all DB-interacting jobs need a ssh tunnel to
             access a database that is inaccessible to computing nodes.'
        report: 'toggle verbose output.'
        commit: an argument for database-related workflows.
        """
        self.input_path = input_path   #folder or file
        self.inputSuffixList = getListOutOfStr(list_in_str=inputSuffixList,
            data_type=str, separator1=',', separator2='-')
        self.inputSuffixSet = set(self.inputSuffixList)
        self.pegasusFolderName = pegasusFolderName
        
        self.output_path = output_path

        self.tmpDir = tmpDir
        self.max_walltime = max_walltime
        self.home_path = home_path
        self.javaPath = javaPath
        self.jvmVirtualByPhysicalMemoryRatio = jvmVirtualByPhysicalMemoryRatio
        
        self.site_handler = site_handler
        self.input_site_handler = input_site_handler
        if not self.input_site_handler:
            self.input_site_handler = self.site_handler
        self.cluster_size = cluster_size

        self.needSSHDBTunnel = needSSHDBTunnel
        self.direct_run = direct_run
        self.debug = debug
        self.report = report
        self.commit = commit

        # change the workflow name to reflect the output filename
        workflow_name = os.path.splitext(os.path.basename(self.output_path))[0]
        # call parent
        self.name = workflow_name

        self.namespace = "pegasus"
        self.version="1.0"

        PegaWorkflow.__init__(self, self.name, infer_dependencies=True)

        self.wf_dir = Path(self.output_path).parent.resolve()

        for pathName in self.pathToInsertHomePathList:
            absPath = self.insertHomePath(getattr(self, pathName, None),
                self.home_path)
            if absPath:
                setattr(self, pathName, absPath)
            else:
                logging.warning(f"{pathName} has an empty absolute path. "
                    "Ignored in prepending home_path.")
        
        self.pegasus_props:Properties = create_pegasus_properties()
        self.add_transformation_catalog(TransformationCatalog())
        self.add_replica_catalog(ReplicaCatalog())
        #self._submit_dir is the Pegasus submit folder, generated by pegasus-submit.
        self.add_site_catalog(create_site_catalog(self.wf_dir, exec_site_name=self.site_handler))

        self.commandline = ' '.join(sys.argv)

        #global counter
        self.no_of_jobs = 0
        #flag to check if dag has been outputted or not
        self.isDAGWrittenToDisk = False

        #this must be ahead of connectDB().
        self.extra__init__()
        self.connectDB()

    def extra__init__(self):
        """
        placeholder
        """
        pass

    def writeXML(self, **keywords):
        """
        call self.write() instead
        """
        self.write(**keywords)
    
    # --- Write files in directory -------------------------------------------------
    def write(self, **keywords):
        """
        TODO: write properties, site_catalog, replica_catalog to files in the workflow folder.
        """
        self.pegasus_props.write()
        if not self.site_catalog is None:
            self.site_catalog.write()
        self.replica_catalog.write()
        self.transformation_catalog.write()
        print(f'{self.no_of_jobs} jobs in the DAG.', flush=True)
        print(f"Writing the DAG to {self.output_path} ... ", flush=True, end='')
        out = open(self.output_path, 'w')
        PegaWorkflow.write(self, out)
        out.write(f'#commandline: {self.commandline}\n')
        out.close()
        print("Done", flush=True)

    def constructOneExecutableObject(self, name=None, path=None,
        checkExecutable=True, is_stageable=False, **keywords):
        """
        checkExecutable: True to check if path is an executable file.
        is_stageable:
            True: this executable needs to be staged to the shared scratch folder
                or to a folder on the running folder.
            False: this executable is already installed on all nodes.
        """
        if checkExecutable:
            if path.find('file://') == 0:
                fs_path = path[6:]
            else:
                fs_path = path
            if not (os.path.isfile(fs_path) and os.access(fs_path, os.X_OK)):
                logging.error(f"From constructOneExecutableObject(): "
                    f"Exec {path} does not exist or is not an executable.")
                sys.exit(3)
        abspath = os.path.abspath(os.path.expanduser(path))
        executable = Transformation(name, site=self.site_handler, \
            pfn=abspath, 
            is_stageable=is_stageable, arch=Arch.X86_64,
            os_type=OS.LINUX)
        executable.abspath = abspath
        #executable.add_pegasus_profile(clusters_size=3)
        return executable

    def connectDB(self):
        """
        placeholder, to establish db connection
        """
        self.db_main = None

    def insertHomePath(self, inputPath=None, home_path=None):
        """
        inputPath could be None/empty
        """
        if inputPath:
            if inputPath[0]!='/':
                #prepend home to a relative path only
                inputPath = os.path.join(home_path, inputPath)
        else:
            inputPath = None
        return inputPath

    def registerJars(self):
        """
        register jars to be used in the workflow
        """
        pass

    def registerCustomJars(self):
        """
        custom jars specific to the workflow, not for child classes to have.
        """
        pass

    def registerCustomExecutables(self):
        """
        custom executable specific to the workflow,
            not for child classes to inherit.
        """
        pass


    def registerExecutables(self):
        """
        """
        if hasattr(self, 'javaPath') and self.javaPath \
                and os.path.isfile(self.javaPath):
            self.registerOneExecutable(name='java', path=self.javaPath,
                clusterSizeMultiplier=1)
        else:
            logging.warn(f"Java path: {self.javaPath}, does not exist.")
        self.registerOneExecutable(name='cp', path="/bin/cp",
            clusterSizeMultiplier=1)
        self.registerOneExecutable(name='mv', path="/bin/mv",
            clusterSizeMultiplier=1)
        self.registerOneExecutable(
            name='runShellCommand',
            path=os.path.join(src_dir, "tools/runShellCommand.sh"),
            clusterSizeMultiplier=1)
        self.registerOneExecutable(
            name='pipe2File',
            path=os.path.join(src_dir, 'tools/pipe2File.sh'),
            clusterSizeMultiplier=1)
        self.registerOneExecutable(
            name='sortHeaderAware', 
            path=os.path.join(src_dir, 'tools/sortHeaderAware.sh'),
            clusterSizeMultiplier=1)
        #to be used on pipe2File.sh
        self.sortExecutableFile = self.registerOneExecutableAsFile(
            path="/usr/bin/sort")
        #mkdirWrap is different from mkdir that it doesn't report error
        #  when the directory is already there.
        self.registerOneExecutable(
            name='mkdirWrap',
            path=os.path.join(src_dir, 'tools/mkdirWrap.sh'),
            clusterSizeMultiplier=1)
        self.registerOneExecutable(
            name='gzip',
            path=os.path.join(src_dir, "tools/gzip.sh"),
            clusterSizeMultiplier=1)
        
    def setExecutablesClusterSize(self, executableClusterSizeMultiplierList,
        defaultClusterSize:int=None):
        """
        make sure the profile of clusters.size is not added already.
        """
        if defaultClusterSize is None:
            defaultClusterSize = self.cluster_size
        for executableClusterSizeMultiplierTuple in \
            executableClusterSizeMultiplierList:
            executable = executableClusterSizeMultiplierTuple[0]
            if len(executableClusterSizeMultiplierTuple) == 1:
                clusterSizeMultiplier = 1
            else:
                clusterSizeMultiplier = executableClusterSizeMultiplierTuple[1]
            self.setExecutableClusterSize(
                executable=executable,
                clusterSizeMultiplier=clusterSizeMultiplier,
                defaultClusterSize=defaultClusterSize)
    
    def setExecutableClusterSize(self, executable:Transformation=None,
        clusterSizeMultiplier=1, defaultClusterSize:int=None):
        """
        """
        if defaultClusterSize is None:
            defaultClusterSize = self.cluster_size
        cluster_size = int(defaultClusterSize*clusterSizeMultiplier)
        if cluster_size > 1:
            executable.add_pegasus_profile(clusters_size=cluster_size)
        return executable

    def registerOneExecutable(self, name=None, path=None,
        clusterSizeMultiplier=1, **keywords):
        """
        clusterSizeMultiplier: fine-tune the cluster size for one executable.
            cluster-size of an executable = default-cluster-size * clusterSizeMultiplier.
            Set clusterSizeMultiplier to 0 if your job has a very long list of arguments.
                Otherwise, pegasus will fail your job due to too many arguments.
        
        Call constructOneExecutableObject() & setExecutableClusterSize()
        """
        if clusterSizeMultiplier is None:
            clusterSizeMultiplier = 1
        if not name:
            name = os.path.basename(os.path.splitext(path)[0])
        executable = self.constructOneExecutableObject(name=name, path=path)
        self.setExecutableClusterSize(executable=executable,
            clusterSizeMultiplier=clusterSizeMultiplier)
        self.transformation_catalog.add_transformations(executable)
        setattr(self, executable.name, executable)
        return executable

    def getFilesWithProperSuffixFromFolder(self, inputFolder=None,
        suffix='.h5'):
        """
        """
        logging.info("Getting files with %s as suffix from %s ..."%(
            suffix, inputFolder))
        input_path_list = []
        counter = 0
        for filename in os.listdir(inputFolder):
            prefix, file_suffix = os.path.splitext(filename)
            counter += 1
            if file_suffix==suffix:
                input_path_list.append(os.path.join(inputFolder, filename))
        logging.info("%s files out of %s total.\n"%(
            len(input_path_list), counter))
        return input_path_list

    def getFilesWithSuffixFromFolderRecursive(self, inputFolder, 
            suffixSet=None, fakeSuffix='.gz', return_path_list=None):
        """
        This function recursively finds all files whose suffix is in suffixSet.
        Return all files in return_path_list.
        Similar to getFilesWithProperSuffixFromFolder(),
            but recursively go through all sub-folders.
        It calls utils.getRealPrefixSuffix()
            to get the suffix.
        """
        logging.info(f"Getting files with suffix in {repr(suffixSet)}, "
            f"fake suffix={fakeSuffix}, from {inputFolder} ...")
        counter = 0
        for filename in os.listdir(inputFolder):
            input_path = os.path.join(inputFolder, filename)
            counter += 1
            if os.path.isfile(input_path):
                prefix, file_suffix = \
                    getRealPrefixSuffix(
                        filename, fakeSuffix=fakeSuffix)
                if file_suffix in suffixSet:
                    return_path_list.append(input_path)
            elif os.path.isdir(input_path):
                self.getFilesWithSuffixFromFolderRecursive(input_path, \
                    suffixSet=suffixSet, fakeSuffix=fakeSuffix,
                    return_path_list=return_path_list)
        logging.info(f"{len(return_path_list)} out of {counter} files.")

    def registerFilesOfInputDir(self, inputDir=None,  input_path_list=None,
        input_site_handler=None, \
        pegasusFolderName='', inputSuffixSet=None, indexFileSuffixSet=None,
        **keywords):
        """
        This function registers all files in inputDir (if present) and 
            input_path_list (if not None).
        indexFileSuffixSet is used to add additional index files related
            to an input file.
            Assume that index file name is original filename + indexFileSuffix.
            indexFileSuffixSet=set(['.tbi', '.fai'])
        """
        if input_path_list is None:
            input_path_list = []
        if inputDir and os.path.isdir(inputDir):
            fnameLs = os.listdir(inputDir)
            for fname in fnameLs:
                input_path = os.path.realpath(os.path.join(inputDir, fname))
                input_path_list.append(input_path)

        if inputSuffixSet is None:
            inputSuffixSet = getattr(self, 'inputSuffixSet', None)
        print(f"Registering {len(input_path_list)} input files with suffix in "
            f" {inputSuffixSet} ... ", flush=True, end='')
        returnData = PassingData(jobDataLs = [])
        counter = 0
        for input_path in input_path_list:
            counter += 1
            suffix = getRealPrefixSuffix(input_path)[1]
            #default fakeSuffixSet includes .gz
            if inputSuffixSet is not None and len(inputSuffixSet)>0 and suffix \
                not in inputSuffixSet:
                #skip input whose suffix is not in inputSuffixSet \
                # if inputSuffixSet is a non-empty set.
                continue
            if indexFileSuffixSet is not None and len(indexFileSuffixSet)>0 \
                and suffix in indexFileSuffixSet:
                #skip index files, they are affiliates of real input data files.
                continue

            # Add the file to the replica catalog
            lfn = os.path.join(pegasusFolderName, os.path.basename(input_path))
            input_file = File(lfn)
            input_file.name = lfn
            self.replica_catalog.add_replica(input_site_handler, lfn=input_file, pfn=input_path)
            input_file.abspath = input_path
            jobData = PassingData(output=input_file, job=None, jobLs=[],
                file=input_file, fileLs=[input_file], indexFileLs=[])
            # Find all index files if indexFileSuffixSet is given.
            if indexFileSuffixSet:
                for indexFileSuffix in indexFileSuffixSet:
                    indexFilename = '%s%s'%(input_path, indexFileSuffix)
                    if os.path.isfile(indexFilename):
                        indexFile = self.registerOneInputFile(
                            input_path=indexFilename,
                            input_site_handler=input_site_handler,
                            folderName=pegasusFolderName, \
                            useAbsolutePathAsPegasusFileName=False,
                            checkFileExistence=True)
                        jobData.fileLs.append(indexFile)
                        jobData.indexFileLs.append(indexFile)
            returnData.jobDataLs.append(jobData)
        print(f"{len(returnData.jobDataLs)} out of {len(input_path_list)} "
            f"possible files registered. Done.", flush=True)
        return returnData

    def registerFilesAsInputToJob(self, job:Job, inputFileList:List[File]):
        """
        call addJobUse()
        """
        for inputFile in inputFileList:
            self.addJobUse(job, inputFile)
    

    def registerOneInputFile(self,
        input_path=None,
        pegasusFileName=None,
        input_site_handler=None,
        folderName="",
        useAbsolutePathAsPegasusFileName=False,
        checkFileExistence=True):
        """
        Examples:
            pegasusFile = self.registerOneInputFile(input_path='/tmp/abc.txt',
                pegasusFileName='input/abc.txt')
        
        pegasusFileName:
            Can be a relative path, like 'input/input.txt'.
            No need to create folder "input".
            pegasus will create all preceding folders during stage-in.
        useAbsolutePathAsPegasusFileName:
            This would render the file to be referred as the absolute path on
             the running nodes.
            And pegasus will not symlink or copy/transfer the file.
            Set it to True only if you don't want to add the file to the job
              as an INPUT dependency (as it's accessed through abs path).
        folderName: if given, it will cause the file to be put into that folder
              (relative path) within the pegasus workflow running folder.
            This folder needs to be created by a mkdir job.
        Return: pegasusFile.abspath or pegasusFile.absPath is the absolute path
            of the file.
        """
        if input_site_handler is None:
            input_site_handler = self.input_site_handler
        if not pegasusFileName:
            if useAbsolutePathAsPegasusFileName:
                #this will stop symlinking/transferring ,
                #  and no need to add them as dependency for jobs.
                pegasusFileName = os.path.abspath(input_path)
            else:
                pegasusFileName = os.path.join(folderName,
                    os.path.basename(input_path))
        pegasusFile = File(pegasusFileName)
        pegasusFile.name = pegasusFileName
        if checkFileExistence and not os.path.isfile(input_path):
            logging.error(f"From registerOneInputFile(): {input_path} does not exist.")
            raise
        pegasusFile.abspath = os.path.abspath(input_path)
        pegasusFile.absPath = pegasusFile.abspath
        self.replica_catalog.add_replica(input_site_handler, lfn=pegasusFile,
            pfn=pegasusFile.abspath)
        return pegasusFile

    def registerOneJar(self, name=None, path=None, site_handler=None, \
        folderName="", useAbsolutePathAsPegasusFileName=False):
        """
        useAbsolutePathAsPegasusFileName=True if you do not plan
         to add a jar file as INPUT dependency for jobs
        """
        if site_handler is None:
            site_handler = self.site_handler
        if not folderName:
            folderName = "jar"
        pegasusFile = self.registerOneInputFile(input_path=path, 
            input_site_handler=site_handler, 
            folderName=folderName, 
            useAbsolutePathAsPegasusFileName=useAbsolutePathAsPegasusFileName)
        setattr(self, name, pegasusFile)
        return pegasusFile

    def registerOneExecutableAsFile(self, path=None, site_handler=None,
        pythonVariableName=None,
        folderName=None, useAbsolutePathAsPegasusFileName=False):
        """
        This function is used when an executable will be the input of another
            program. It is rarely needed.

        Examples:
            self.samtoolsExecutableFile = self.registerOneExecutableAsFile(
                path=self.samtools_path,\
                input_site_handler=self.input_site_handler)
            self.registerOneExecutableAsFile(
                pythonVariableName="bwaExecutableFile",
                path=self.bwa_path)

        Set pythonVariableName to overwrite the default. 
        Set useAbsolutePathAsPegasusFileName=True if you do NOT plan to
            add the file as INPUT dependency for jobs.
        """
        if site_handler is None:
            site_handler = self.site_handler
        if not folderName:
            folderName = "executable"
        if not pythonVariableName:
            pythonVariableName = f'{os.path.basename(path)}ExecutableFile'
        pegasusFile = self.registerOneInputFile(
            input_path=path, input_site_handler=site_handler, \
            folderName=folderName, \
            useAbsolutePathAsPegasusFileName=useAbsolutePathAsPegasusFileName)
        setattr(self, pythonVariableName, pegasusFile)
        return pegasusFile

    def addInputToMergeJob(self, mergeJob:Job=None,
        inputF:File=None, inputArgumentOption="",
        parentJobLs=None,
        extraDependentInputLs=None, **keywords):
        """
        This function adds inputF or parentJobLs[i].output
            (if inputF is not given) as input to mergeJob.
        inputArgumentOption (like '-i') is added in front of each input file.
        extraDependentInputLs is a list of dependent files to mergeJob,
            which will NOT be added to the commandline of mergeJob.
        i.e.
            self.addInputToMergeJob(mergeJob=mergeDataJob, 
                inputF=input_file])
            self.addInputToMergeJob(mergeJob=gatkUnionJob,
                parentJobLs=[gatk_job], inputArgumentOption="--variant")
        
        """
        if inputF is None and parentJobLs is not None:
            parentJob = parentJobLs[0]
            if hasattr(parentJob, 'output'):
                inputF = parentJob.output
        if inputF:
            self.addJobUse(mergeJob, inputF)
            if inputArgumentOption:
                #add it in front of each input file
                mergeJob.add_args(inputArgumentOption)
            mergeJob.add_args(inputF)

        if extraDependentInputLs:
            for inputFile in extraDependentInputLs:
                if inputFile:
                    self.addJobUse(mergeJob, inputFile)

        if parentJobLs:
            for parentJob in parentJobLs:
                if parentJob:
                    self.add_dependency(mergeJob, parents=[parentJob])

    def addSortJob(self, executable:Transformation=None, commandFile=None, \
        inputFile:File=None, outputFile:File=None, noOfHeaderLines=0, \
        extraArgumentList=None, extraArguments=None, 
        parentJobLs:Optional[List[Job]]=None, extraDependentInputLs=None,
        extraOutputLs=None,
        transferOutput=False, sshDBTunnel=None,
        job_max_memory=200, walltime=120, **keywords):
        """
        use sortHeaderAware executable (from pymodule/shell).
        Examples:
            sortedSNPID2NewCoordinateFile = File(
                os.path.join(reduceOutputDirJob.output, \
                    'SNPID2NewCoordinates.sorted.tsv.gz'))
            sortSNPID2NewCoordinatesJob = self.addSortJob(
                inputFile=reduceJob.output, \
                outputFile=sortedSNPID2NewCoordinateFile, noOfHeaderLines=1,
                extraArgumentList=["-k3,3 -k4,4n"], \
                parentJobLs=[reduceJob], \
                extraOutputLs=None, transferOutput=False, \
                sshDBTunnel=None,\
                job_max_memory=4000, walltime=120)
            # -t$'\t' for sort has to be removed as it won't be passed correctly.
            # the default sort field separator (non-blank to blank) works
            #  if no-blank is part of each cell value.
        """
        if executable is None:
            executable = self.sortHeaderAware
        if commandFile is None:
        	commandFile = self.sortExecutableFile
        if extraDependentInputLs is None:
            extraDependentInputLs = []
        if extraArgumentList is None:
            extraArgumentList = []

        extraArgumentList.insert(0, "%s"%(noOfHeaderLines))
        job = self.addGenericJob(executable=executable,
            inputFile=inputFile, inputArgumentOption="",
            outputFile=outputFile, outputArgumentOption="",
            extraArgumentList=extraArgumentList,
            extraArguments=extraArguments,
            extraOutputLs=extraOutputLs,
            transferOutput=transferOutput,
            parentJobLs=parentJobLs,
            extraDependentInputLs=extraDependentInputLs,
            sshDBTunnel=sshDBTunnel,\
            job_max_memory=job_max_memory, walltime=walltime)
        return job
    
    def addDBJob(self, executable=None, 
        inputFile=None, inputArgumentOption="-i",
        inputFileList=None, argumentForEachFileInInputFileList=None,
        outputFile=None, outputArgumentOption="-o",
        extraArguments=None, extraArgumentList=None,
        parentJobLs=None, extraDependentInputLs=None, extraOutputLs=None,
        transferOutput=False,
        job_max_memory=200, walltime=None, sshDBTunnel=None,
        key2ObjectForJob=None, objectWithDBArguments=None,
        **keywords):
        """
        similar to addGenericJob but these are jobs that need
            db-interacting arguments.

        inputFileList: a list of input files to be added to commandline as
            the last arguments.
            they would also be added as the job's dependent input.
        extraDependentInputLs: purely for dependency purpose, not added as
            input arguments. So if files have been put in inputFileList,
            then they shouldn't be in extraDependentInputLs.
        """
        if objectWithDBArguments is None:
            objectWithDBArguments = self
        job = self.addGenericJob(executable=executable, \
            inputFile=inputFile, inputArgumentOption=inputArgumentOption, \
            outputFile=outputFile, outputArgumentOption=outputArgumentOption,
            inputFileList=inputFileList,
            argumentForEachFileInInputFileList=argumentForEachFileInInputFileList,
            extraArguments=extraArguments,
            extraArgumentList=extraArgumentList,\
            parentJobLs=parentJobLs,
            extraDependentInputLs=extraDependentInputLs,
            extraOutputLs=extraOutputLs,
            transferOutput=transferOutput,
            job_max_memory=job_max_memory, sshDBTunnel=sshDBTunnel,
            key2ObjectForJob=key2ObjectForJob,\
            objectWithDBArguments=objectWithDBArguments, walltime=walltime,
            **keywords)

        #set the job.input
        if getattr(job, 'input', None) is None and job.inputLs:
            job.input = job.inputLs[0]
        return job
    
    def addData2DBJob(self, executable=None, 
        inputFile=None, inputArgumentOption="-i",
        inputFileList=None,
        argumentForEachFileInInputFileList=None,
        outputFile=None, outputArgumentOption="-o",
        data_dir=None, logFile=None, commit=False,
        extraArguments=None, extraArgumentList=None,
        parentJobLs=None, extraDependentInputLs=None,
        extraOutputLs=None,
        transferOutput=False,
        job_max_memory=200, sshDBTunnel=None,
        key2ObjectForJob=None, objectWithDBArguments=None, **keywords):
        """
        a generic wrapper for jobs that "inserts" data (from file) into database
        Example:
        
        job = self.addData2DBJob(executable=executable,
            inputArgumentOption="-i", inputFile=None,
            outputFile=None, outputArgumentOption="-o",
            data_dir=None, logFile=logFile, commit=commit,
            extraArguments=extraArguments,
            extraArgumentList=extraArgumentList,
            parentJobLs=parentJobLs,
            extraDependentInputLs=extraDependentInputLs,
            extraOutputLs=None,
            transferOutput=transferOutput,
            job_max_memory=job_max_memory,  sshDBTunnel=sshDBTunnel,
            walltime=walltime,\
            key2ObjectForJob=None, objectWithDBArguments=self, **keywords)

        """
        if extraArgumentList is None:
            extraArgumentList = []
        if extraOutputLs is None:
            extraOutputLs = []

        if data_dir:
            extraArgumentList.append('--data_dir %s'%(data_dir))
        if commit:
            extraArgumentList.append('--commit')
        if logFile:
            extraArgumentList.extend(["--logFilename", logFile])
            extraOutputLs.append(logFile)
        #do not pass the inputFileList to addGenericJob()
        #  because db arguments need to be added before them.
        job = self.addDBJob(executable=executable,
            inputArgumentOption=inputArgumentOption,
            inputFile=inputFile,
            inputFileList=inputFileList,
            argumentForEachFileInInputFileList=argumentForEachFileInInputFileList,
            outputArgumentOption=outputArgumentOption,
            outputFile=outputFile,
            extraArguments=extraArguments,
            extraArgumentList=extraArgumentList,
            parentJobLs=parentJobLs,
            extraDependentInputLs=extraDependentInputLs,
            extraOutputLs=extraOutputLs,
            transferOutput=transferOutput,
            job_max_memory=job_max_memory, sshDBTunnel=sshDBTunnel,
            key2ObjectForJob=key2ObjectForJob,
            objectWithDBArguments=objectWithDBArguments, **keywords)
        return job

    def addJobUse(self, job:Job=None, file:File=None, is_input=True, transfer=True,
        register_replica=False, **keywords):
        """
        20210616 is_input replaces link (Link.INPUT or Link.OUTPUT)
        transfer is equivalent to stage_out, only for output file.
        """
        if is_input:
            if hasattr(job, "inputLs"):
                job.inputLs.append(file)
            job.add_inputs(file)
        else:
            if hasattr(job, "outputLs"):
                job.outputLs.append(file)
            job.add_outputs(file, stage_out=transfer, register_replica=register_replica)
        return True

    def addJobDependency(self, parentJob=None, childJob=None):
        """
        make sure parentJob is of instance Job, sometimes, 
         it could be a fake job, like PassingData(output=...).
        check whether the dependency exists already.
        """
        addedOrNot = True
        if isinstance(parentJob, Job):
            self.add_dependency(childJob, parents=[parentJob])
            addedOrNot = True
        else:
            addedOrNot = False
        return addedOrNot

    def addDBArgumentsToOneJob(self, job:Job=None, objectWithDBArguments=None):
        """
        use long arguments , rather than short ones.
        A convenient function to add db-related arguments to a db-interacting job.
        """
        if objectWithDBArguments is None:
            objectWithDBArguments = self
        job.add_args("--drivername", objectWithDBArguments.drivername,
            "--hostname", objectWithDBArguments.hostname, \
            "--dbname", objectWithDBArguments.dbname, \
            "--db_user", objectWithDBArguments.db_user,
            "--db_passwd %s"%objectWithDBArguments.db_passwd)
        if objectWithDBArguments.schema:
            job.add_args("--schema", objectWithDBArguments.schema)
        if getattr(objectWithDBArguments, 'port', None):
            job.add_args("--port=%s"%(objectWithDBArguments.port))
        return job
    
    def addGenericJob(self, executable:Transformation=None,
        frontArgumentList:List[str]=None,
        inputArgumentOption="",
        inputFile:File=None,
        inputFileList:List[File]=None,
        argumentForEachFileInInputFileList=None,
        outputArgumentOption="",
        outputFile:File=None,
        extraArgumentList=None, extraArguments=None,
        parentJob:Job=None, parentJobLs:List[Job]=None,
        extraDependentInputLs=None,
        extraOutputLs=None, \
        transferOutput=False, sshDBTunnel=None, \
        key2ObjectForJob=None, objectWithDBArguments=None,
        objectWithDBGenomeArguments=None,\
        no_of_cpus=None, job_max_memory=200, walltime=180,
        max_walltime=None, **keywords):
        """
        A generic job adding function for other functions to use.
        The commandline order:
            executable [frontArgumentList] [DBArguments] [inputArgumentOption]
                [inputFile] [outputArgumentOption] [outputFile]
                [extraArgumentList] [extraArguments]

        job_max_memory: integer, unit in MB.
        max_walltime: integer, in minutes. maximum possible walltime for one
         or a cluster of jobs.
        walltime: walltime (max running time) for a single job. 
            For a clustered job, walltime is multiplied by the cluster_size,
             but less than max_walltime.
        objectWithDBArguments: an object that contains database arguments
            (host, dbname, username, etc.).
        argumentForEachFileInInputFileList: to be added in front of each file
         in inputFileList.
        frontArgumentList: a list of arguments to be put in front of anything else.
        parentJob: similar to parentJobLs, but only one job.
        inputFileList: a list of input files to be appended to the commandline.
            They would also be added as the job's dependent input.
            Difference from extraDependentInputLs:
                the latter is purely for dependency purpose,
                    not added as commandline arguments.
                So if a file has been put in inputFileList,
                then it shouldn't be in extraDependentInputLs.
        If transferOutput is None, do not register output files as OUTPUT with
            transfer flag.
        key2ObjectForJob: which is a dictionary with strings as key,
            to set key:object for each job.
        job.inputLs:
            Hold all input files, including inputFile.
        job.outputLs or job.outputList:
            Hold all output files, including outputFile.
        job.output: =outputFile.
            If it is not set, set it to the 1st entry of job.outputLs.
        """
        job = Job(executable)
        #self.addJobUse() will fill job.outputLs and job.inputLs
        job.outputLs = []
        job.inputLs = []
        if frontArgumentList:
            job.add_args(*frontArgumentList)
        if objectWithDBArguments:
            self.addDBArgumentsToOneJob(job=job,
                objectWithDBArguments=objectWithDBArguments)
        if objectWithDBGenomeArguments:
            self.addDBGenomeArgumentsToOneJob(job=job, 
                objectWithDBArguments=objectWithDBGenomeArguments)

        if inputFile:
            if inputArgumentOption:
                job.add_args(inputArgumentOption)
            job.add_args(inputFile)
            # addJobUse will append the file to job.inputLs
            self.addJobUse(job, file=inputFile, is_input=True)
            job.input = inputFile
        if outputFile:
            if outputArgumentOption:
                job.add_args(outputArgumentOption)
            job.add_args(outputFile)
            # addJobUse will append the file to job.outputLs
            self.addJobUse(job, file=outputFile, is_input=False,
                transfer=transferOutput)
            job.output = outputFile
        if extraArgumentList:
            job.add_args(*extraArgumentList)

        if extraArguments:
            job.add_args(extraArguments)

        # scale walltime according to cluster_size
        cluster_size = getExecutableClusterSize(executable)
        if cluster_size is not None and cluster_size and walltime is not None:
            cluster_size = int(cluster_size)
            if cluster_size>1:
                if max_walltime is None:
                    max_walltime = self.max_walltime
                walltime = min(walltime*cluster_size, max_walltime)

        setJobResourceRequirement(job, job_max_memory=job_max_memory,
            sshDBTunnel=sshDBTunnel,\
            no_of_cpus=no_of_cpus, walltime=walltime)
        self.add_jobs(job)
        job.parentJobLs = []
        if parentJob:
            isAdded = self.addJobDependency(parentJob=parentJob, childJob=job)
            if isAdded:
                job.parentJobLs.append(parentJob)
        if parentJobLs:
            for parentJob in parentJobLs:
                if parentJob:
                    isAdded = self.addJobDependency(parentJob=parentJob,
                        childJob=job)
                    if isAdded:
                        job.parentJobLs.append(parentJob)
        if extraDependentInputLs:
            for inputFile in extraDependentInputLs:
                if inputFile:
                    # addJobUse will append the file to job.inputLs
                    self.addJobUse(job, file=inputFile)
        if extraOutputLs:
            for output in extraOutputLs:
                if output:
                    # addJobUse will append the file to job.outputLs
                    self.addJobUse(job, file=output, is_input=False,
                        transfer=transferOutput, 
                        register_replica=False)
        if key2ObjectForJob:
            for key, objectForJob in key2ObjectForJob.items():
                setattr(job, key, objectForJob)

        #add all input files to the last (after db arguments,) otherwise,
        #  it'll mask others (cuz these don't have options).
        if inputFileList:
            for inputFile in inputFileList:
                if inputFile:
                    if argumentForEachFileInInputFileList:
                        job.add_args(argumentForEachFileInInputFileList)
                    job.add_args(inputFile)
                    # addJobUse will append the file to job.inputLs
                    self.addJobUse(job, file=inputFile)
        job.outputList = job.outputLs
        #if job.output is not set, set it to the 1st entry of job.outputLs
        if getattr(job, 'output', None) is None and job.outputLs:
            job.output = job.outputLs[0]
        if getattr(job, 'input', None) is None and job.inputLs:
            job.input = job.inputLs[0]
        self.no_of_jobs += 1
        return job

    def addJavaJob(self, executable=None, jarFile=None,
        frontArgumentList=None,
        inputFile=None, inputArgumentOption=None,
        inputFileList=None,argumentForEachFileInInputFileList=None,
        outputFile=None, outputArgumentOption=None,\
        extraArguments=None, extraArgumentList=None,
        extraDependentInputLs=None,
        extraOutputLs=None,
        parentJobLs=None, transferOutput=True,
        job_max_memory=1000, no_of_cpus=None, walltime=120, 
        key2ObjectForJob=None, sshDBTunnel=None, **keywords):
        """
        a generic function to add Java jobs:

fastaDictJob = self.addGenericJavaJob(executable=CreateSequenceDictionaryJava,
    jarFile=CreateSequenceDictionaryJar, \
    frontArgumentList=None,
    inputArgumentOption="REFERENCE=", inputFile=refFastaF,
    outputArgumentOption="OUTPUT=", outputFile=refFastaDictF,
    parentJobLs=parentJobLs, transferOutput=transferOutput,
    job_max_memory=job_max_memory,
    extraDependentInputLs=None, no_of_cpus=None, walltime=walltime,
    sshDBTunnel=None, **keywords)
        """
        if executable is None:
            executable = self.java
        if frontArgumentList is None:
            frontArgumentList = []
        if extraArgumentList is None:
            extraArgumentList = []
        if extraDependentInputLs is None:
            extraDependentInputLs = []
        if extraOutputLs is None:
            extraOutputLs = []
        
        memRequirementObject = self.getJVMMemRequirment(
            job_max_memory=job_max_memory, minMemory=4000)
        job_max_memory = memRequirementObject.memRequirement
        javaMemRequirement = memRequirementObject.memRequirementInStr

        #put java stuff in front of other front arguments
        frontArgumentList = [javaMemRequirement, '-jar', jarFile] + \
            frontArgumentList
        extraDependentInputLs.append(jarFile)
        job = self.addGenericJob(executable=executable,
            frontArgumentList=frontArgumentList, 
            inputArgumentOption=inputArgumentOption, inputFile=inputFile,
            argumentForEachFileInInputFileList=argumentForEachFileInInputFileList,
            inputFileList=inputFileList,
            outputArgumentOption=outputArgumentOption,
            outputFile=outputFile,
            extraArguments=extraArguments,
            extraArgumentList=extraArgumentList,
            parentJobLs=parentJobLs, 
            extraDependentInputLs=extraDependentInputLs,
            extraOutputLs=extraOutputLs,
            transferOutput=transferOutput,
            sshDBTunnel=sshDBTunnel, key2ObjectForJob=key2ObjectForJob,
            job_max_memory=job_max_memory,
            no_of_cpus=no_of_cpus, walltime=walltime, **keywords)
        return job

    def addPipe2FileJob(self, executable=None, commandFile=None,
        outputFile=None, extraArgumentList=None, 
        extraOutputLs=None, transferOutput=False, \
        parentJobLs=None, extraDependentInputLs=None, \
        sshDBTunnel=None,\
        job_max_memory=200, walltime=120, **keywords):
        """
        Call shell/pipe2File to redirect stdout output to outputFile.
            shell/pipe2File.sh outputFile commandFile [commandArguments]
        executable can be None (Default: self.pipe2File).
        commandFile could be None.

        Examples:
            bwaCommand = self.registerOneExecutableAsFile(path="/usr/bin/bwa")
            extraArgumentList=[alignment_method.command]	#add mem first
            extraArgumentList.extend(["-a -M", refFastaFile] + fastqFileList)
            alignmentJob = self.addPipe2FileJob(executable=self.BWA_Mem,
                commandFile=bwaCommand,
                outputFile=alignmentSamF, \
                extraArgumentList=extraArgumentList, \
                extraOutputLs=None, transferOutput=transferOutput, \
                parentJobLs=parentJobLs,
                extraDependentInputLs=[refFastaFile] + fastqFileList,
                job_max_memory=aln_job_max_memory, 
                walltime=aln_job_walltime, no_of_cpus=no_of_aln_threads,
                **keywords)
            
            sortedSNPID2NewCoordinateFile = File(os.path.join(
                reduceOutputDirJob.output, 'SNPID2NewCoordinates.sorted.tsv'))
            sortSNPID2NewCoordinatesJob = self.addPipe2FileJob(
                executable=self.pipe2File,
                commandFile=self.sortExecutableFile, \
                outputFile=sortedSNPID2NewCoordinateFile, \
                extraArgumentList=["-k 3,3 -k4,4n -t$'\t'", reduceJob.output],
                transferOutput=False, \
                parentJobLs=[reduceJob], \
                extraDependentInputLs=[reduceJob.output], \
                job_max_memory=4000, walltime=120)
            
            #skip executable
            sortedVCFFile = File(os.path.join(self.liftOverReduceDirJob.output, 
                '%s.sorted.vcf'%(seqTitle)))
            vcfSorterJob = self.addPipe2FileJob(
                commandFile=self.vcfsorterExecutableFile,
                outputFile=sortedVCFFile, \
                extraArgumentList=[
                    self.newRegisterReferenceData.refPicardFastaDictF,
                    selectOneChromosomeVCFJob.output],
                parentJobLs=[selectOneChromosomeVCFJob, self.liftOverReduceDirJob], \
                extraDependentInputLs=[
                    self.newRegisterReferenceData.refPicardFastaDictF, 
                    selectOneChromosomeVCFJob.output], \
                transferOutput=False, \
                job_max_memory=job_max_memory, walltime=walltime)

        """
        if executable is None:
            executable = self.pipe2File
        if extraDependentInputLs is None:
            extraDependentInputLs = []
        if not extraArgumentList:
            extraArgumentList = []
        if commandFile:
            extraDependentInputLs.append(commandFile)
            #add commandFile in front of all other arguments
            extraArgumentList.insert(0, commandFile)
        
        job= self.addGenericJob(executable=executable, \
            frontArgumentList=None,\
            inputArgumentOption=None, inputFile=None,
            outputArgumentOption=None, outputFile=outputFile,
            extraArgumentList=extraArgumentList,
            parentJobLs=parentJobLs,
            extraDependentInputLs=extraDependentInputLs,
            extraOutputLs=extraOutputLs, transferOutput=transferOutput,
            job_max_memory=job_max_memory,
            sshDBTunnel=sshDBTunnel, walltime=walltime, **keywords)
        return job
    
    def setJobOutputFileTransferFlag(self, job:Job=None, transferOutput:bool=False,
        outputLs:List[File]=None):
        """
        assume that all output files are in job.outputLs
        """
        if outputLs is None and getattr(job, 'outputLs', None):
            outputLs = job.outputLs
        #job outputs stage_out set to True, but no way to do that in Pegasus 5.0
        print(f"No way to set stage_out to True for {len(outputLs)} output files of {job}",
            flush=True)
        return

    def getJVMMemRequirment(self, job_max_memory=5000, minMemory=500,
        permSizeFraction=0, MaxPermSizeUpperBound=35000):
        """
        Java 8 does not support PermSize anymore. set permSizeFraction to 0.
        handle when job_max_memory is None and minMemory is None.
        if a job's virtual memory (1.2X=self.jvmVirtualByPhysicalMemoryRatio, 
            of memory request) exceeds request, it'll abort.
            so set memRequirement accordingly.
        lower permSizeFraction from 0.4 to 0.2
            minimum for MaxPermSize is now minMemory/2
        job_max_memory = MaxPermSize + mxMemory, unless either is below minMemory
            added argument permSizeFraction, MaxPermSizeUpperBound
        job_max_memory could be set by user to lower than minMemory.
            but minMemory makes sure it's never too low.
        """
        if job_max_memory is None:
            job_max_memory = 5000
        if minMemory is None:
            minMemory = 500
        #permSizeFraction is set to 0 due to newer Java no longer needs it.
        permSizeFraction = 0
        #MaxPermSize_user = int(job_max_memory*permSizeFraction)
        mxMemory_user = int(job_max_memory*(1-permSizeFraction))
        #MaxPermSize= min(MaxPermSizeUpperBound, max(minMemory/2, MaxPermSize_user))
        #PermSize=MaxPermSize*3/4
        mxMemory = max(minMemory, mxMemory_user)
        msMemory = int(mxMemory*3/4)
        #-XX:+UseGCOverheadLimit
        #Use a policy that limits the proportion of the VM's time
        #  that is spent in GC 
        #  before an OutOfMemory error is thrown. (Introduced in 6.)
        #-XX:-UseGCOverheadLimit would disable the policy.
        #  -XX:PermSize=%sm -XX:MaxPermSize=%sm"%\
        #  , PermSize, MaxPermSize)
        memRequirementInStr = f"-Xms{msMemory}m -Xmx{mxMemory}m"
        
        memRequirement = int(mxMemory*self.jvmVirtualByPhysicalMemoryRatio)
        #if a job's virtual memory (1.2X of memory request) exceeds request,
        #  it'll abort.
        return PassingData(memRequirementInStr=memRequirementInStr,
            memRequirement=memRequirement)

    def scaleJobWalltimeOrMemoryBasedOnInput(self, realInputVolume=10, \
        baseInputVolume=4, baseJobPropertyValue=120, \
        minJobPropertyValue=120, maxJobPropertyValue=1440):
        """
        assume it's integer.
        walltime is in minutes.
        """
        walltime = min(max(minJobPropertyValue, 
            float(realInputVolume)/float(baseInputVolume)*baseJobPropertyValue),
            maxJobPropertyValue)	#in minutes
        return PassingData(value=int(walltime))

    def addMkDirJob(self, outputDir=None, executable=None, 
        parentJobLs=None, extraDependentInputLs=None):
        """
        add a job to make a directory.
        i.e.
            simulateOutputDirJob = self.addMkDirJob(outputDir=simulateOutputDir)
        """
        if executable is None:
            executable = self.mkdirWrap
        job = self.addGenericJob(executable=executable,
            extraArgumentList=[outputDir],
            parentJobLs=parentJobLs,
            extraDependentInputLs=extraDependentInputLs,
            job_max_memory=50, walltime=10)
        job.folder = outputDir
        job.output = outputDir
        return job

    def setup_run(self):
        """
        Wrap all standard pre-run() related functions into this function.
        """
        if self.debug:
            import pdb
            pdb.set_trace()

        if getattr(self, 'db_main', None):
            session = self.db_main.session
            session.begin(subtransactions=True)

            if not getattr(self, 'data_dir', None):
                self.data_dir = self.db_main.data_dir

            if not getattr(self, 'local_data_dir', None):
                self.local_data_dir = self.db_main.data_dir

        self.workflow = self
        self.registerJars()
        self.registerCustomJars()
        self.registerExecutables()
        self.registerCustomExecutables()

        return self

    def end_run(self):
        """
        To be called in the end.
        Write the DAG to an output file and close the database connection.
        """
        # Write the DAX to stdout
        if self.isDAGWrittenToDisk:
            logging.warn("The dag has been written to a file "
                "already (write() has been called). No more writing.")
        else:
            self.write()
            self.isDAGWrittenToDisk = True

        if getattr(self, 'db_main', None):
            session = self.db_main.session
            if self.commit:
                session.commit()
            else:
                session.rollback()
        if self.direct_run:
            # plan and submit the workflow for execution
            print(f"Submitting the workflow ...", flush=True)
            self.plan(submit=True)

            # braindump becomes accessible following a call to wf.plan()
            print(f"submit_dir is {self.braindump.submit_dir}")

            # wait for workflow execution to complete
            print(f"Waiting for the workflow to finish ...", flush=True)
            self.wait()

            # workflow debugging and statistics
            print(f"Analyzing the workflow ...", flush=True)
            self.analyze()
            print(f"Calculating statistics on the workflow ...", flush=True)
            self.statistics()

if __name__ == '__main__':
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("-i", "--input_path", type=str, required=True,
        help="the path to the input folder or file.")
    ap.add_argument("--inputSuffixList", type=str,
        help='Coma-separated list of input file suffices. '
        'Used to exclude input files.'
        'If None, no exclusion.'
        'Please include the dot to the suffix, .tsv, not tsv.'
        'Common zip suffices (.gz, .bz2, .zip, .bz) will be ignored in '
        'obtaining the suffix.')
    ap.add_argument("-F", "--pegasusFolderName", type=str,
        help='The path relative to the workflow running root. '
        'This folder will contain pegasus input & output. '
        'It will be created during the pegasus staging process. '
        'It is useful to separate multiple sub-workflows. '
        'If empty or None, everything is in the pegasus root.')
    ap.add_argument("-o", "--output_path", type=str, required=True,
        help="The path to the output file that will contain the Pegasus DAG.")

    ap.add_argument("--tmpDir", type=str, default='/tmp/',
        help='Default: %(default)s. '
            'A local folder for some jobs (MarkDup) to store temp data.'
            '/tmp/ can be too small sometimes.')
    ap.add_argument("--max_walltime", type=int, default=4320,
        help='Default: %(default)s. '
        'Maximum wall time for any job, in minutes. 4320=3 days.'
        'Used in addGenericJob(). Most clusters have upper limit for runtime.')
    
    ap.add_argument("--javaPath", type=str,
        help='The path to java binary. Must be provided if you have Java jobs.')
    ap.add_argument("--jvmVirtualByPhysicalMemoryRatio", type=float, default=1.2,
        help='Default: %(default)s. '
        'If a job virtual memory (~1.2X of JVM resident memory) exceeds request, '
        "it may be killed. "
        "This will make sure your java jobs request enough memory.")
    
    ap.add_argument("-l", "--site_handler", type=str, required=True,
        help="The name of the computing site where the jobs run "
        "and executables are stored. "
        "Check your Pegasus configuration in submit.sh.")
    ap.add_argument("-j", "--input_site_handler", type=str,
        help="It is the name of the site that has all the input files."
        "Possible values can be 'local' or the same as site_handler. "
        "If not sure, leave it alone."
        "If not given, it is asssumed to be the same as site_handler "
        " and the input files will be symlinked into the running folder."
        "If the job submission node does not share a file system with the "
        "computing site, input_site_handler=local,"
        " and the input files will be transferred to the computing site by"
        " pegasus-transfer (need setup).")
    ap.add_argument("-C", "--cluster_size", type=int, default=1,
        help="Default: %(default)s. "
        "This number decides how many of pegasus jobs should be clustered "
        "into one job. Good if your workflow contains many quick jobs. "
        "It will reduce Pegasus monitor I/O.")
    ap.add_argument("--direct_run", action='store_true',
        help='Run the workflow directly, with no need to run pegasus-plan.')
    ap.add_argument("--debug", action='store_true',
        help='Toggle debug mode.')
    ap.add_argument("--report", action='store_true',
        help="Toggle verbose mode. Default: %(default)s.")
    ap.add_argument("--needSSHDBTunnel", action='store_true',
        help="If all DB-interacting jobs need a ssh tunnel to "
        "access a database that is inaccessible to computing nodes.")
    args = ap.parse_args()
    instance = Workflow(
        input_path=args.input_path,
        inputSuffixList=args.inputSuffixList,
        pegasusFolderName=args.pegasusFolderName,
        output_path=args.output_path,
        
        tmpDir=args.tmpDir, max_walltime=args.max_walltime,
        javaPath=args.javaPath,
        jvmVirtualByPhysicalMemoryRatio=args.jvmVirtualByPhysicalMemoryRatio,
        
        site_handler=args.site_handler,
        input_site_handler=args.input_site_handler,
        cluster_size=args.cluster_size,

        needSSHDBTunnel=args.needSSHDBTunnel,
        direct_run=args.direct_run,
        debug=args.debug, report=args.report)
    instance.setup_run()
    instance.end_run()

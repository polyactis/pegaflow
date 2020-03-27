#!/usr/bin/env python3
"""
a class for pegasus workflows to inherit
"""
import sys, os
from DAX3 import Executable, File, PFN, Profile, Namespace, Link, ADAG, Use, Job, Dependency

class PassingData(object):
    """
    a class to hold any data structure
    """
    
    def __init__(self, **keywords):
        """
        add keyword handling
        """
        for argument_key, argument_value in keywords.iteritems():
            setattr(self, argument_key, argument_value)
            #setattr(self, argument_key, argument_value)
    
    def __str__(self):
        """
        a string-formatting function
        """
        return_ls = []
        for attributeName in dir(self):
            if attributeName.find('__')==0:	#ignore the 
                continue
            value = getattr(self, attributeName, None)
            return_ls.append("%s = %s"%(attributeName, value))
            
        return ", ".join(return_ls)
    
    def __getitem__(self, key):
        """
        enable it to work like a dictionary
            i.e. pdata.chromosome or pdata['chromosome'] is equivalent if attribute 0 is chromosome.
        """
        return self.__getattribute__(key)

def getListOutOfStr(list_in_str=None, data_type=int, separator1=',', separator2='-'):
    """
    This function parses a list from a string representation of a list, such as '1,3-7,11'=[1,3,4,5,6,7,11].
    If only separator2, '-', is used ,all numbers have to be integers.
    If all are separated by separator1, it could be in non-int data_type.
    strip the strings as much as u can.
    if separator2 is None or nothing or 0, it wont' be used.

    Examples:
        self.chromosomeList = utils.getListOutOfStr('1-5,7,9', data_type=str, separator2=None)
    """
    list_to_return = []
    if list_in_str=='' or list_in_str is None:
        return list_to_return
    list_in_str = list_in_str.strip()	#2013.04.09
    if list_in_str=='' or list_in_str is None:
        return list_to_return
    if type(list_in_str)==int:	#just one integer, put it in and return immediately
        return [list_in_str]
    index_anchor_ls = list_in_str.split(separator1)
    for index_anchor in index_anchor_ls:
        index_anchor = index_anchor.strip()	#2013.04.09
        if len(index_anchor)==0:	#nothing there, skip
            continue
        if separator2:
            start_stop_tup = index_anchor.split(separator2)
        else:
            start_stop_tup = [index_anchor]
        if len(start_stop_tup)==1:
            list_to_return.append(data_type(start_stop_tup[0]))
        elif len(start_stop_tup)>1:
            start_stop_tup = map(int, start_stop_tup)
            list_to_return += range(start_stop_tup[0], start_stop_tup[1]+1)
    list_to_return = map(data_type, list_to_return)	#2008-10-27
    return list_to_return

def getRealPrefixSuffixOfFilenameWithVariableSuffix(path, fakeSuffix='.gz', fakeSuffixSet = set(['.gz', '.zip', '.bz2', '.bz'])):
    """
    The purpose of this function is to get the prefix, suffix of a filename regardless of whether it
        has two suffices (gzipped) or one. 
    i.e.
        A file name is either sequence_628BWAAXX_4_1.fastq.gz or sequence_628BWAAXX_4_1.fastq (without gz).
        This function returns ('sequence_628BWAAXX_4_1', '.fastq')

    "." is considered part of the filename suffix.
    
    """
    fname_prefix, fname_suffix =  os.path.splitext(path)
    if fakeSuffix and fakeSuffix not in fakeSuffixSet:
        fakeSuffixSet.add(fakeSuffix)
    while fname_suffix in fakeSuffixSet:
        fname_prefix, fname_suffix =  os.path.splitext(fname_prefix)
    return fname_prefix, fname_suffix


def addMkDirJob(workflow=None, mkdir=None, outputDir=None, namespace=None, version=None,\
            parentJobLs=None, extraDependentInputLs=None):
    """
    """
    # Add a mkdir job for any directory.
    job = Job(namespace=getattr(workflow, 'namespace', namespace), name=mkdir.name, \
                version=getattr(workflow, 'version', version))
    job.addArguments(outputDir)
    job.folder = outputDir	#custom attribute
    job.output = outputDir	#custom attribute
    workflow.addJob(job)
    if parentJobLs:
        for parentJob in parentJobLs:
            if parentJob:
                workflow.depends(parent=parentJob, child=job)
    if extraDependentInputLs:
        for input in extraDependentInputLs:
            if input is not None:
                job.uses(input, transfer=True, register=True, link=Link.INPUT)
    if hasattr(workflow, 'no_of_jobs'):
        workflow.no_of_jobs += 1
    return job

def setJobToProperMemoryRequirement(job=None, job_max_memory=500, no_of_cpus=1, walltime=180, sshDBTunnel=0):
    """
    job_max_memory is in MB.
    if job_max_memory is None, then skip setting memory requirement.
    if job_max_memory is "" or 0 or "0", then assign 500 (mb) to it.
    sshDBTunnel:
        =1: this job needs a ssh tunnel to access an external database server.
        =anything else: no need for that.
    set walltime default to 180 minutes (3 hours).
    walltime is in minutes.
    """
    condorJobRequirementLs = []
    if job_max_memory == "" or job_max_memory == 0 or job_max_memory =="0":
        job_max_memory = 500
    if job_max_memory is not None: 
        job.addProfile(Profile(Namespace.GLOBUS, key="maxmemory", value="%s"%(job_max_memory)))
        job.addProfile(Profile(Namespace.CONDOR, key="request_memory", value="%s"%(job_max_memory)))	#for dynamic slots
        condorJobRequirementLs.append("(memory>=%s)"%(job_max_memory))
    if sshDBTunnel==1:
        condorJobRequirementLs.append("(sshDBTunnel==%s)"%(sshDBTunnel))	#use ==, not =.
    
    if no_of_cpus is not None:
        job.addProfile(Profile(Namespace.CONDOR, key="request_cpus", value="%s"%(no_of_cpus)) )	#for dynamic slots
    
    if walltime is not None:
        #scale walltime according to clusters_size
        job.addProfile(Profile(Namespace.GLOBUS, key="maxwalltime", value="%s"%(walltime)) )
        #TimeToLive is in seconds
        condorJobRequirementLs.append("(Target.TimeToLive>=%s)"%(int(walltime)*60) )
    #key='requirements' could only be added once for the condor profile
    job.addProfile(Profile(Namespace.CONDOR, key="requirements", value=" && ".join(condorJobRequirementLs) ))

setJobProperRequirement = setJobToProperMemoryRequirement

def registerFile(workflow, filename):
    """
    function to register any file to the workflow.input_site_handler, 
    """
    file = File(os.path.basename(filename))
    file.addPFN(PFN("file://" + os.path.abspath(filename), \
                                workflow.input_site_handler))
    workflow.addFile(file)
    return file

def getAbsPathOutOfExecutable(executable):
    """
        This function extracts path out of a registered executable.
            executable is a registered pegasus executable with PFNs.
    """
    pfn = (list(executable.pfns)[0])
    #the url looks like "file:///home/crocea/bin/bwa"
    return pfn.url[7:]


def getAbsPathOutOfFile(file):
    """
    call getAbsPathOutOfExecutable
    """
    return getAbsPathOutOfExecutable(file)

def getExecutableClustersSize(executable=None):
    """
    default is None
    """
    clusters_size = None
    clusteringProf = Profile(Namespace.PEGASUS, key="clusters.size", value="1")
    for profile in executable.profiles:
        if clusteringProf.__hash__() == profile.__hash__():	#__hash__ only involves namespace + key 
            clusters_size = profile.value
    return clusters_size


class Workflow(ADAG):
    __doc__ = __doc__
    db_option_dict = {
                    ('drivername', 1,):['postgresql', 'v', 1, 'which type of database? mysql or postgresql', ],\
                    ('hostname', 1, ): ['localhost', 'z', 1, 'hostname of the db server', ],\
                    ('dbname', 1, ): ['', 'd', 1, 'database name', ],\
                    ('schema', 0, ): ['public', 'k', 1, 'database schema name', ],\
                    ('db_user', 1, ): [None, 'u', 1, 'database username', ],\
                    ('db_passwd', 1, ): [None, 'p', 1, 'database password', ],\
                    ('port', 0, ):[None, '', 1, 'database port number'],\
                    ('commit', 0, ):[None, '', 0, 'commit database transaction if there is db transaction'],\
                    ("data_dir", 0, ): ["", 't', 1, 'the base directory where all db-affiliated files are stored. '
                                    'If not given, use the default stored in db.'],\
                    ("local_data_dir", 0, ): ["", 'D', 1, 'this one should contain same files as data_dir but accessible locally. '
                            'If not given, use the default stored in db (db.data_dir). This argument is used to find all input files available.\n '
                            'It should be different from data_dir only when you generate a workflow on one computer and execute it on another which has different data_dir.'],\

                    }
    option_default_dict = {
                        ("home_path", 1, ): [os.path.expanduser("~"), 'e', 1, 'path to the home directory on the working nodes'],\
                        ("pegasusCleanupPath", 1, ): ["%s/bin/pegasus/bin/pegasus-cleanup", '', 1, 'path to pegasus-cleanup executable, it will be registered and run on local universe of condor pool (rather than the vanilla universe)'],\
                        ("pegasusTransferPath", 1, ): ["%s/bin/pegasus/bin/pegasus-transfer", '', 1, 'path to pegasus-transfer executable, it will be registered and run on local universe of condor pool (rather than the vanilla universe)'],\
                        ("site_handler", 1, ): ["condorpool", 'l', 1, 'which site to run the jobs: condorpool, hoffman2'],\
                        ("input_site_handler", 1, ): ["local", 'j', 1, 'which site has all the input files: local, condorpool, hoffman2. '
                            'If site_handler is condorpool, this must be condorpool and files will be symlinked. '
                            'If site_handler is hoffman2, input_site_handler=local induces file transfer and input_site_handler=hoffman2 induces symlink.'],\
                        ('clusters_size', 1, int):[30, 'C', 1, 'For short jobs that will be clustered, how many of them should be clustered int one'],\
                        ('pegasusFolderName', 0, ): ['folder', 'F', 1, 'the folder relative to pegasus workflow root to contain input & output. '
                                'It will be created during the pegasus staging process. It is useful to separate multiple workflows. '
                                'If empty, everything is in the pegasus root.', ],\
                        ('inputSuffixList', 0, ): [None, '', 1, 'coma-separated list of input file suffices. If None, any suffix. '
                            'Suffix include the dot, (i.e. .tsv). Typical zip suffices are excluded (.gz, .bz2, .zip, .bz).'],\
                        ('outputFname', 1, ): [None, 'o', 1, 'xml workflow output file'],\
                        ("tmpDir", 1, ): ["/tmp/", '', 1, 'for MarkDuplicates.jar, etc., default is /tmp/ but sometimes it is too small'],\
                        ('max_walltime', 1, int):[4320, '', 1, 'maximum wall time any job could have, in minutes. 20160=2 weeks.\n'
                            'used in addGenericJob().'],\
                        ('jvmVirtualByPhysicalMemoryRatio', 1, float):[1.0, '', 1, 
                            "if a job's virtual memory (usually 1.2X of JVM resident memory) exceeds request, "
                            "it will be killed on hoffman2. Hence this argument"],\
                        ("thisModulePath", 1, ): ["%s", '', 1, 'path of the module that owns this program. '
                            'used to add executables from this module.'],\
                        ('debug', 0, int):[0, 'b', 0, 'toggle debug mode'],\
                        ('needSSHDBTunnel', 0, int):[0, 'H', 0, 'DB-interacting jobs need a ssh tunnel (running on cluster behind firewall).'],\
                        ('report', 0, int):[0, 'r', 0, 'toggle report, more verbose stdout/stderr.']
                        }
                        #('bamListFname', 1, ): ['/tmp/bamFileList.txt', 'L', 1, 'The file contains path to each bam file, one file per line.'],\

    pathToInsertHomePathList = ['pegasusCleanupPath', \
                            'pegasusTransferPath', "thisModulePath"]

    def __init__(self, inputArgumentLs=None, **keywords):
        """
        """
        # call parent
        ADAG.__init__(self, "myworkflow")
        """
        # methods of ADAG
        >>> dir(a)
        ['__doc__', '__init__', '__module__', '__str__', '__unicode__', 'addDAG', 'addDAX', 'addDependency',
        'addExecutable', 'addFile', 'addInvoke', 'addJob', 'addTransformation', 'clearDependencies',
        'clearExecutables', 'clearFiles', 'clearInvokes', 'clearJobs', 'clearTransformations', 'count',
        'dependencies', 'depends', 'executables', 'files', 'getJob', 'hasDependency', 'hasExecutable',
        'hasFile', 'hasInvoke', 'hasJob', 'hasTransformation', 'index', 'invocations', 'invoke', 'jobs',
         'name', 'nextJobID', 'removeDependency', 'removeExecutable', 'removeFile', 'removeInvoke',
         'removeJob', 'removeTransformation', 'sequence', 'toXML', 'transformations', 'writeXML', 'writeXMLFile']

        """
        from pymodule import ProcessOptions
        self.ad = ProcessOptions.process_function_arguments(keywords, self.option_default_dict, error_doc=self.__doc__, \
                                                        class_to_have_attr=self)
        self.inputSuffixList = getListOutOfStr(list_in_str=self.inputSuffixList, data_type=str, separator1=',', separator2='-')
        self.inputSuffixSet = set(self.inputSuffixList)
        self.inputArgumentLs = inputArgumentLs
        if self.inputArgumentLs is None:
            self.inputArgumentLs = []

        #change the workflow name to reflect the output filename
        workflowName = os.path.splitext(os.path.basename(self.outputFname))[0]
        self.name = workflowName

        for pathName in self.pathToInsertHomePathList:
            absPath = self.insertHomePath(getattr(self, pathName, None), self.home_path)
            if absPath:
                setattr(self, pathName, absPath)
            else:
                sys.stderr.write("Warning: %s has empty absolute path. Skip.\n"%(pathName))
        
        #self.pymodulePath = self.insertHomePath(self.pymodulePath, self.home_path)

        # Add executables to the DAX-level replica catalog
        # In this case the binary is keg, which is shipped with Pegasus, so we use
        # the remote PEGASUS_HOME to build the path.
        self.architecture = "x86_64"
        self.operatingSystem = "linux"
        self.namespace = "pegasus"
        self.version="1.0"

        self.commandline = ' '.join(sys.argv)

        #global counter
        self.no_of_jobs = 0
        #flag to check if dag has been outputted or not
        self.isDAGWrittenToDisk = False

        self.extra__init__()	#this must be ahead of connectDB().
        self.connectDB()

    def extra__init__(self):
        """
        placeholder
        """
        pass

    def writeXML(self, out):
        """
        Write the ADAG as XML to a stream.
        Overwrite its parent: ADAG.writeXML().
        check self.isDAGWrittenToDisk first.
        call ADAG.writeXML() and then add my commandline comment.
        """
        if self.isDAGWrittenToDisk:
            sys.stderr.write("Warning: the dag has been written to a file already (writeXML() has been called). No more calling.\n")
        else:
            sys.stderr.write("Writing XML job to %s ..."%(out))
            ADAG.writeXML(self, out)
            out.write('<!-- commandline: %s -->\n'%(self.commandline.replace("--", "~~")))	#2012.9.4 -- is not allowed in xml comment.
            sys.stderr.write(".\n")
            self.isDAGWrittenToDisk = True
    
    def constructOneExecutableObject(self, path=None, name=None, checkPathExecutable=True, version=None, namespace=None,\
                                    noVersion=False):
        """
        check if path is an executable file.
        """
        if not namespace:
            namespace = self.namespace
        if not version:
            version = self.version
        operatingSystem = self.operatingSystem
        architecture = self.architecture
        site_handler = self.site_handler

        if noVersion:
            #removed argument version from Executable()
            executable = Executable(namespace=namespace, name=name,\
                        os=operatingSystem, arch=architecture, installed=True)
        else:
            executable = Executable(namespace=namespace, name=name, version=version,\
                        os=operatingSystem, arch=architecture, installed=True)
        #
        if checkPathExecutable:
            if path.find('file://')==0:
                fs_path = path[6:]
            else:
                fs_path = path
            
            if not (os.path.isfile(fs_path) and os.access(fs_path, os.X_OK)):
                sys.stderr.write("Error from constructOneExecutableObject(): \
        executable %s is not an executable.\n"%(path))
                raise
        executable.addPFN(PFN("file://" + os.path.expanduser(path), site_handler))
        return executable

    def connectDB(self):
        """
        placeholder, to establish db connection
        """
        self.db_main = None

    def insertHomePath(self, inputPath, home_path):
        """
        inputPath could be None
        """
        if inputPath:
            if inputPath.find('%s')!=-1:
                inputPath = inputPath%home_path
        else:
            inputPath = None
        return inputPath

    def registerJars(self):
        """
            register jars to be used in the worflow
        """
        pass

    def registerCustomJars(self):
        """
        """
        pass

    def registerCustomExecutables(self):
        """
        """
        pass


    def registerExecutables(self):
        """
        """
        self.addExecutableFromPath(path="/bin/cp", name='cp', clusterSizeMultipler=1)
        self.addExecutableFromPath(path="/bin/mv", name='mv', clusterSizeMultipler=1)
        self.sortExecutableFile = self.registerOneExecutableAsFile(path="/usr/bin/sort")

    def addExecutables(self, executableClusterSizeMultiplierList=[], defaultClustersSize=None):
        """
            make sure the profile of clusters.size is not added already.
        """
        if defaultClustersSize is None:
            defaultClustersSize = self.clusters_size
        for executableClusterSizeMultiplierTuple in executableClusterSizeMultiplierList:
            executable = executableClusterSizeMultiplierTuple[0]
            if len(executableClusterSizeMultiplierTuple)==1:
                clusterSizeMultipler = 1
            else:
                clusterSizeMultipler = executableClusterSizeMultiplierTuple[1]
            self.addExecutableWClusterSize(executable=executable, \
                                        clusterSizeMultipler=clusterSizeMultipler, defaultClustersSize=defaultClustersSize)
    
    addExecutableAndAssignProperClusterSize = addExecutables

    def addExecutableWClusterSize(self, executable=None, clusterSizeMultipler=1, defaultClustersSize=None):
        """
        clusterSizeMultipler could be any real value >=0. 0 means no clustering, 1=default clustering size.

        i.e.
            self.addExecutableWClusterSize(executable=CompareTwoGWAssociationLocusByPhenotypeVector, clusterSizeMultipler=0)
        """
        executable = self.setOrChangeExecutableClusterSize(executable=executable, \
                                            clusterSizeMultipler=clusterSizeMultipler, defaultClustersSize=defaultClustersSize)
        if not self.hasExecutable(executable):
            self.addExecutable(executable)	#removeExecutable() is its counterpart
            setattr(self, executable.name, executable)
        return executable
    addOneExecutableAndAssignProperClusterSize = addExecutableWClusterSize

    def setOrChangeExecutableClusterSize(self, executable=None, clusterSizeMultipler=1, defaultClustersSize=None):
        """
        it'll remove the clustering profile if the new clusterSize is <1
        """
        if defaultClustersSize is None:
            defaultClustersSize = self.clusters_size
        clusterSize = int(defaultClustersSize*clusterSizeMultipler)
        clusteringProf = Profile(Namespace.PEGASUS, key="clusters.size", value="%s"%clusterSize)
        if executable.hasProfile(clusteringProf):
            executable.removeProfile(clusteringProf)
        if clusterSize>1:
            executable.addProfile(clusteringProf)
        return executable

    def addExecutableFromPath(self, path=None, name=None, clusterSizeMultipler=1, noVersion=False):
        """
        combination of constructOneExecutableObject() & addExecutableWClusterSize()
        """
        if clusterSizeMultipler is None:
            clusterSizeMultipler = 1
        executable = self.constructOneExecutableObject(path=path, name=name, noVersion=noVersion)
        self.addExecutableWClusterSize(executable=executable, clusterSizeMultipler=clusterSizeMultipler)
        return executable

    addOneExecutableFromPathAndAssignProperClusterSize = addExecutableFromPath

    def getExecutableClustersSize(self, executable=None):
        """
        default is None
        """
        return getExecutableClustersSize(executable)

    def getFilesWithProperSuffixFromFolder(self, inputFolder=None, suffix='.h5'):
        """
        """
        sys.stderr.write("Getting files with %s as suffix from %s ..."%(suffix, inputFolder))
        inputFnameLs = []
        counter = 0
        for filename in os.listdir(inputFolder):
            prefix, file_suffix = os.path.splitext(filename)
            counter += 1
            if file_suffix==suffix:
                inputFnameLs.append(os.path.join(inputFolder, filename))
        sys.stderr.write("%s files out of %s total.\n"%(len(inputFnameLs), counter))
        return inputFnameLs

    def getFilesWithSuffixFromFolderRecursive(self, inputFolder=None, suffixSet=set(['.h5']), fakeSuffix='.gz', inputFnameLs=[]):
        """
        similar to getFilesWithProperSuffixFromFolder() but recursively go through all sub-folders
                and it uses utils.getRealPrefixSuffixOfFilenameWithVariableSuffix() to get the suffix.
        """
        sys.stderr.write("Getting files with %s as suffix (%s as fake suffix) from %s ...\n"%(repr(suffixSet), fakeSuffix, inputFolder))
        counter = 0
        for filename in os.listdir(inputFolder):
            inputFname = os.path.join(inputFolder, filename)
            counter += 1
            if os.path.isfile(inputFname):
                prefix, file_suffix = getRealPrefixSuffixOfFilenameWithVariableSuffix(filename, fakeSuffix=fakeSuffix)
                if file_suffix in suffixSet:
                    inputFnameLs.append(inputFname)
            elif os.path.isdir(inputFname):
                self.getFilesWithSuffixFromFolderRecursive(inputFname, suffixSet=suffixSet, fakeSuffix=fakeSuffix, inputFnameLs=inputFnameLs)
        sys.stderr.write("%s files out of %s total.\n"%(len(inputFnameLs), counter))
        #return inputFnameLs

    def registerAllInputFiles(self, inputDir=None,  inputFnameLs=None, input_site_handler=None, \
                        pegasusFolderName='', inputSuffixSet=None, indexFileSuffixSet=set(['.tbi', '.fai']),\
                        **keywords):
        """
        indexFileSuffixSet is used to attach corresponding index files to a input file.
            assuming index file name is original filename + indexFileSuffix.
        """
        if inputFnameLs is None:
            inputFnameLs = []
        if inputDir and os.path.isdir(inputDir):	#2013.04.07
            fnameLs = os.listdir(inputDir)
            for fname in fnameLs:
                inputFname = os.path.realpath(os.path.join(inputDir, fname))
                inputFnameLs.append(inputFname)

        if inputSuffixSet is None:
            inputSuffixSet = self.inputSuffixSet
        sys.stderr.write("Registering %s input files with %s possible sufficies ..."%(len(inputFnameLs), len(inputSuffixSet)))
        returnData = PassingData(jobDataLs = [])
        counter = 0
        for inputFname in inputFnameLs:
            counter += 1
            suffix = getRealPrefixSuffixOfFilenameWithVariableSuffix(inputFname)[1]	#default fakeSuffixSet includes .gz
            if inputSuffixSet is not None and len(inputSuffixSet)>0 and suffix not in inputSuffixSet:
                #skip input whose suffix is not in inputSuffixSet if inputSuffixSet is a non-empty set.
                continue
            if indexFileSuffixSet is not None and len(indexFileSuffixSet)>0 and suffix in indexFileSuffixSet:
                #skip index files, they are affiliates of real input data files.
                continue
            inputFile = File(os.path.join(pegasusFolderName, os.path.basename(inputFname)))
            inputFile.addPFN(PFN("file://" + inputFname, input_site_handler))
            inputFile.abspath = inputFname
            self.addFile(inputFile)
            jobData = PassingData(output=inputFile, job=None, jobLs=[], \
                                file=inputFile, fileLs=[inputFile], indexFileLs=[])
            #find all index files.
            for indexFileSuffix in indexFileSuffixSet:
                indexFilename = '%s%s'%(inputFname, indexFileSuffix)
                if os.path.isfile(indexFilename):
                    indexFile = self.registerOneInputFile(inputFname=indexFilename, \
                                        input_site_handler=input_site_handler, folderName=pegasusFolderName, \
                                        useAbsolutePathAsPegasusFileName=False, checkFileExistence=True)
                    jobData.fileLs.append(indexFile)
                    jobData.indexFileLs.append(indexFile)
            returnData.jobDataLs.append(jobData)
        sys.stderr.write(" %s out of %s files registered.\n"%(len(returnData.jobDataLs), len(inputFnameLs)))
        return returnData

    def registerFilesAsInputToJob(self, job, inputFileList):
        """
        call addJobUse()
        """
        for inputFile in inputFileList:
            self.addJobUse(job=job, file=inputFile, transfer=True, register=True, link=Link.INPUT)
            #job.uses(inputFile, transfer=True, register=True, link=Link.INPUT)

    def registerOneInputFile(self, inputFname=None, input_site_handler=None, folderName="", \
                            useAbsolutePathAsPegasusFileName=False,\
                            pegasusFileName=None, checkFileExistence=True):
        """
        Examples:
            pegasusFile = self.registerOneInputFile(inputFname=path, input_site_handler=site_handler, \
                                            folderName=folderName, useAbsolutePathAsPegasusFileName=useAbsolutePathAsPegasusFileName)
        raise if inputFname is not a file.
        useAbsolutePathAsPegasusFileName:
            This would render the file to be referred as the absolute path on the running computer.
            And pegasus will not seek to symlink or copy/transfer the file.
            set it to True only when you dont want to add the file to the job as INPUT dependency (as it's accessed through abs path).
        make sure the file is not registed with the workflow already
        add abspath attribute to file.
        argument folderName: if given, it will cause the file to be put into a pegasus workflow folder.
        """
        if input_site_handler is None:
            input_site_handler = self.input_site_handler
        if not pegasusFileName:
            if useAbsolutePathAsPegasusFileName:
                pegasusFileName = os.path.abspath(inputFname)	#this will stop symlinking/transferring , and also no need to indicate them as file dependency for jobs.
            else:
                pegasusFileName = os.path.join(folderName, os.path.basename(inputFname))
        pegasusFile = File(pegasusFileName)
        if checkFileExistence and not os.path.isfile(inputFname):	#2013.06.29
            sys.stderr.write("Error from registerOneInputFile(): %s does not exist.\n"%(inputFname))
            raise
        pegasusFile.abspath = os.path.abspath(inputFname)
        pegasusFile.absPath = pegasusFile.abspath
        pegasusFile.addPFN(PFN("file://" + pegasusFile.abspath, input_site_handler))
        if not self.hasFile(pegasusFile):	#2013.1.10
            self.addFile(pegasusFile)
        return pegasusFile

    def registerOneJar(self, name=None, path=None, site_handler=None, workflow=None, folderName="", useAbsolutePathAsPegasusFileName=False):
        """
        useAbsolutePathAsPegasusFileName=True if you do not plan to add a jar file as INPUT dependency for jobs
        """
        if site_handler is None:
            site_handler = self.site_handler	#usually they are same
        if not folderName:
            folderName = "jar"
        pegasusFile = self.registerOneInputFile(inputFname=path, input_site_handler=site_handler, \
                                            folderName=folderName, useAbsolutePathAsPegasusFileName=useAbsolutePathAsPegasusFileName)
        setattr(self, name, pegasusFile)
        return pegasusFile

    def registerOneExecutableAsFile(self, pythonVariableName=None, path=None, site_handler=None, \
                                folderName="", useAbsolutePathAsPegasusFileName=False):
        """
        Examples:
            self.samtoolsExecutableFile = self.registerOneExecutableAsFile(path=self.samtools_path,\
                                                    input_site_handler=self.input_site_handler)
            self.registerOneExecutableAsFile(pythonVariableName="bwaExecutableFile", path=self.bwa_path)

        pythonVariableName is used for access like self.pythonVariableName within python dag generator.
        useAbsolutePathAsPegasusFileName=True if you do not plan to add the file as INPUT dependency for jobs.
        """
        if site_handler is None:
            site_handler = self.site_handler
        if not folderName:
            folderName = "executable"
        if not pythonVariableName:
            pythonVariableName = '%sExecutableFile'%(os.path.basename(path))
        pegasusFile = self.registerOneInputFile(inputFname=path, input_site_handler=site_handler, \
                                            folderName=folderName, \
                                            useAbsolutePathAsPegasusFileName=useAbsolutePathAsPegasusFileName)
        setattr(self, pythonVariableName, pegasusFile)
        return pegasusFile


    def addInputToMergeJob(self, mergeJob=None, inputF=None, inputArgumentOption="",\
                            parentJobLs=None, \
                            extraDependentInputLs=None, **keywords):
        """
        This function adds inputF or parentJobLs[i].output (if inputF is not given) as input to mergeJob.
        inputArgumentOption (like '-i') is added in front of each input file.
        extraDependentInputLs is a list of dependent files to mergeJob.
            They will NOT be added to the commandline of mergeJob.
        i.e.
            self.addInputToMergeJob(mergeJob=mergeDataJob, inputF=input_file])
            self.addInputToMergeJob(mergeJob=gatkUnionJob, parentJobLs=[gatk_job], \
                                            inputArgumentOption="--variant")
        
        """
        if inputF is None and parentJobLs is not None:
            parentJob = parentJobLs[0]
            if hasattr(parentJob, 'output'):
                inputF = parentJob.output
        if inputF:
            isAdded = self.addJobUse(mergeJob, file=inputF, transfer=True, register=True, link=Link.INPUT)
            if isAdded:
                if inputArgumentOption:
                    #add it in front of each input file
                    mergeJob.addArguments(inputArgumentOption)
                mergeJob.addArguments(inputF)

        if extraDependentInputLs:
            for inputFile in extraDependentInputLs:
                if inputFile:
                    isAdded = self.addJobUse(mergeJob, file=inputFile, transfer=True, register=True, link=Link.INPUT)

        if parentJobLs:
            for parentJob in parentJobLs:
                if parentJob:
                    self.addJobDependency(parentJob=parentJob, childJob=mergeJob)


    def addGenericFile2DBJob(self, executable=None, inputFile=None, inputArgumentOption="-i", \
                    inputFileList=None, argumentForEachFileInInputFileList=None,\
                    outputFile=None, outputArgumentOption="-o", \
                    data_dir=None, logFile=None, commit=False,\
                    parentJobLs=None, extraDependentInputLs=None, extraOutputLs=None, transferOutput=False, \
                    extraArguments=None, extraArgumentList=None, job_max_memory=2000,  sshDBTunnel=None, \
                    key2ObjectForJob=None, objectWithDBArguments=None, **keywords):
        """
        Example:
            job = self.addGenericFile2DBJob(executable=executable, inputFile=None, inputArgumentOption="-i", \
                    outputFile=None, outputArgumentOption="-o", inputFileList=None, \
                    data_dir=None, logFile=logFile, commit=commit,\
                    parentJobLs=parentJobLs, extraDependentInputLs=extraDependentInputLs, \
                    extraOutputLs=None, transferOutput=transferOutput, \
                    extraArguments=extraArguments, extraArgumentList=extraArgumentList, \
                    job_max_memory=job_max_memory,  sshDBTunnel=sshDBTunnel, walltime=walltime,\
                    key2ObjectForJob=None, objectWithDBArguments=self, **keywords)

        a generic wrapper for jobs that "inserting" data (from file) into database
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
        #do not pass the inputFileList to addGenericJob() because db arguments need to be added before them.
        job = self.addGenericDBJob(executable=executable, inputFile=inputFile, \
                        inputArgumentOption=inputArgumentOption, \
                        inputFileList=inputFileList, argumentForEachFileInInputFileList=argumentForEachFileInInputFileList,\
                        outputFile=outputFile, \
                        outputArgumentOption=outputArgumentOption, \
                        parentJobLs=parentJobLs, \
                        extraDependentInputLs=extraDependentInputLs, extraOutputLs=extraOutputLs, \
                        transferOutput=transferOutput, extraArguments=extraArguments, extraArgumentList=extraArgumentList,\
                        job_max_memory=job_max_memory, sshDBTunnel=sshDBTunnel, key2ObjectForJob=key2ObjectForJob,\
                        objectWithDBArguments=objectWithDBArguments, **keywords)
        return job

    def addJobUse(self, job=None, file=None, transfer=True, register=True, link=None):
        """
        check whether a file is a use of a job already.
        """
        use = Use(file.name, link=link, register=register, transfer=transfer, optional=None, \
                                namespace=job.namespace,\
                                version=job.version, executable=None)	#, size=None
        if job.hasUse(use):
            return False
        else:
            if link==Link.INPUT:
                if hasattr(job, "inputLs"):
                    job.inputLs.append(file)
            elif link==Link.OUTPUT:
                if hasattr(job, "outputLs"):
                    job.outputLs.append(file)
            job.addUse(use)
            return True

    def addJobDependency(self, parentJob=None, childJob=None):
        """
        make sure parentJob is of instance Job, sometimes, it could be a fake job, like PassingData(output=...).
        check whether the dependency exists already.
        """
        addedOrNot = True
        if isinstance(parentJob, Job):
            dep = Dependency(parent=parentJob, child=childJob)
            if not self.hasDependency(dep):
                self.addDependency(dep)
                addedOrNot = True
            else:
                addedOrNot = False
        else:
            #sys.stderr.write("Warning: parent job %s is not a Job-instance.\n"%(repr(parentJob)))
            addedOrNot = False
        return addedOrNot


    def addGenericJob(self, executable=None, inputFile=None, inputArgumentOption="-i", \
                    outputFile=None, outputArgumentOption="-o", inputFileList=None, argumentForEachFileInInputFileList=None, \
                    parentJob=None, parentJobLs=None, extraDependentInputLs=None, extraOutputLs=None, \
                    frontArgumentList=None, extraArguments=None, extraArgumentList=None, \
                    transferOutput=False, sshDBTunnel=None, \
                    key2ObjectForJob=None, objectWithDBArguments=None, objectWithDBGenomeArguments=None,\
                    no_of_cpus=None, job_max_memory=2000, walltime=180, \
                    max_walltime=None, **keywords):
        """
        A generic job adding function for other functions to use.
        order in commandline:
            executable [frontArgumentList] [DBArguments] [inputArgumentOption] [inputFile] [outputArgumentOption] [outputFile]
                [extraArgumentList] [extraArguments]

        addJobUse() will add file to job.inputLs or job.outputLs pending Link.INPUT or Link.OUTPUT
        added argument objectWithDBGenomeArguments
        added argument max_walltime, maximum walltime for a cluster of jobs.
            argument walltime controls it for single job.
        added argument objectWithDBArguments
        scale walltime according to clusters_size
        argumentForEachFileInInputFileList: to be added in front of each file in inputFileList.
        frontArgumentList: a list of arguments to be put in front of anything else.
        parentJob: similar to parentJobLs, but only one job.
        inputFileList: a list of input files to be added to commandline as the last arguments
            they would also be added as the job's dependent input.
            Difference from extraDependentInputLs: the latter is purely for dependency purpose, not added as input arguments.
                So if files have been put in inputFileList, then they shouldn't be in extraDependentInputLs.
        if transferOutput is None, do not register output files as OUTPUT with transfer flag
        key2ObjectForJob: which is a dictionary with strings as key, to set key:object for each job
        if job.output is not set, set it to the 1st entry of job.outputLs
        job.outputLs: to hold more output files.
        """
        job = Job(namespace=self.namespace, name=executable.name, version=self.version)
        job.outputLs = []	#2012.6.27 to hold more output files
        job.inputLs = []
        if frontArgumentList:	#2013.2.7
            job.addArguments(*frontArgumentList)
        if objectWithDBArguments:	#2013.3.25 moved from addGenericDBJob()
            self.addDBArgumentsToOneJob(job=job, objectWithDBArguments=objectWithDBArguments)
        if objectWithDBGenomeArguments:	#2013.07.31
            self.addDBGenomeArgumentsToOneJob(job=job, objectWithDBArguments=objectWithDBGenomeArguments)

        if inputFile:
            if inputArgumentOption:
                job.addArguments(inputArgumentOption)
            job.addArguments(inputFile)
            isAdded = self.addJobUse(job, file=inputFile, transfer=True, register=True, link=Link.INPUT)
            #job.uses(inputFile, transfer=True, register=True, link=Link.INPUT)
            job.input = inputFile
            #job.inputLs.append(inputFile)
        if outputFile:
            if outputArgumentOption:
                job.addArguments(outputArgumentOption)
            job.addArguments(outputFile)
            if transferOutput is not None:	#2012.8.17
                self.addJobUse(job, file=outputFile, transfer=transferOutput, register=True, link=Link.OUTPUT)
                #job.uses(outputFile, transfer=transferOutput, register=True, link=Link.OUTPUT)
            job.output = outputFile
            #job.outputLs.append(outputFile)
        if extraArgumentList:
            job.addArguments(*extraArgumentList)

        if extraArguments:
            job.addArguments(extraArguments)

        #2013.3.21 scale walltime according to clusters_size
        clusters_size = self.getExecutableClustersSize(executable)
        if clusters_size is not None and clusters_size and walltime is not None:
            clusters_size = int(clusters_size)
            if clusters_size>1:
                if max_walltime is None:
                    max_walltime = self.max_walltime
                walltime = min(walltime*clusters_size, max_walltime)

        setJobProperRequirement(job, job_max_memory=job_max_memory, sshDBTunnel=sshDBTunnel,\
                                    no_of_cpus=no_of_cpus, walltime=walltime)
        self.addJob(job)
        job.parentJobLs = []	#2012.10.18
        if parentJob:	#2012.10.15
            isAdded = self.addJobDependency(parentJob=parentJob, childJob=job)
            if isAdded:
                job.parentJobLs.append(parentJob)
        if parentJobLs:
            for parentJob in parentJobLs:
                if parentJob:
                    isAdded = self.addJobDependency(parentJob=parentJob, childJob=job)
                    if isAdded:
                        job.parentJobLs.append(parentJob)
        if extraDependentInputLs:
            for inputFile in extraDependentInputLs:
                if inputFile:
                    isAdded = self.addJobUse(job, file=inputFile, transfer=True, register=True, link=Link.INPUT)
                    #if isAdded:
                    #	job.inputLs.append(inputFile)
        if extraOutputLs:
            for output in extraOutputLs:
                if output:
                    job.outputLs.append(output)
                    if transferOutput is not None:	#2012.8.17
                        self.addJobUse(job, file=output, transfer=transferOutput, register=True, link=Link.OUTPUT)
                        #job.uses(output, transfer=transferOutput, register=True, link=Link.OUTPUT)
        if key2ObjectForJob:
            for key, objectForJob in key2ObjectForJob.iteritems():
                setattr(job, key, objectForJob)	#key should be a string.

        #add all input files to the last (after db arguments,) otherwise, it'll mask others (cuz these don't have options).
        if inputFileList:
            for inputFile in inputFileList:
                if inputFile:
                    if argumentForEachFileInInputFileList:
                        job.addArguments(argumentForEachFileInInputFileList)
                    job.addArguments(inputFile)
                    isAdded = self.addJobUse(job, file=inputFile, transfer=True, register=True, link=Link.INPUT)
                    #job.uses(inputFile, transfer=True, register=True, link=Link.INPUT)
                    #if isAdded:
                    #	job.inputLs.append(inputFile)
        job.outputList = job.outputLs
        #if job.output is not set, set it to the 1st entry of job.outputLs
        if getattr(job, 'output', None) is None and job.outputLs:
            job.output = job.outputLs[0]
        if getattr(job, 'input', None) is None and job.inputLs:
            job.input = job.inputLs[0]
        self.no_of_jobs += 1
        return job

    def addGenericJavaJob(self, executable=None, jarFile=None, \
                    inputFile=None, inputArgumentOption=None, \
                    inputFileList=None,argumentForEachFileInInputFileList=None,\
                    outputFile=None, outputArgumentOption=None,\
                    frontArgumentList=None, extraArguments=None, extraArgumentList=None, extraOutputLs=None, \
                    extraDependentInputLs=None, \
                    parentJobLs=None, transferOutput=True, job_max_memory=2000,\
                    key2ObjectForJob=None, no_of_cpus=None, walltime=120, sshDBTunnel=None, **keywords):
        """
        a generic function to add Java jobs:
            fastaDictJob = self.addGenericJavaJob(executable=CreateSequenceDictionaryJava, jarFile=CreateSequenceDictionaryJar, \
                    inputFile=refFastaF, inputArgumentOption="REFERENCE=", \
                    inputFileList=None, argumentForEachFileInInputFileList=None,\
                    outputFile=refFastaDictF, outputArgumentOption="OUTPUT=",\
                    parentJobLs=parentJobLs, transferOutput=transferOutput, job_max_memory=job_max_memory,\
                    frontArgumentList=None, extraArguments=None, extraArgumentList=None, extraOutputLs=None, \
                    extraDependentInputLs=None, no_of_cpus=None, walltime=walltime, sshDBTunnel=None, **keywords)
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
        
        memRequirementObject = self.getJVMMemRequirment(job_max_memory=job_max_memory, minMemory=4000)
        job_max_memory = memRequirementObject.memRequirement
        javaMemRequirement = memRequirementObject.memRequirementInStr

        frontArgumentList = [javaMemRequirement, '-jar', jarFile] + frontArgumentList	#put java stuff in front of other fron arguments
        extraDependentInputLs.append(jarFile)
        job = self.addGenericJob(executable=executable, inputFile=inputFile, \
                    inputArgumentOption=inputArgumentOption,  inputFileList=inputFileList,\
                    argumentForEachFileInInputFileList=argumentForEachFileInInputFileList,\
                    outputFile=outputFile, outputArgumentOption=outputArgumentOption, \
                    parentJob=None, parentJobLs=parentJobLs, extraDependentInputLs=extraDependentInputLs, \
                    extraOutputLs=extraOutputLs, \
                    transferOutput=transferOutput, \
                    frontArgumentList=frontArgumentList, extraArguments=extraArguments, \
                    extraArgumentList=extraArgumentList, job_max_memory=job_max_memory,  sshDBTunnel=sshDBTunnel, \
                    key2ObjectForJob=key2ObjectForJob, no_of_cpus=no_of_cpus, walltime=walltime, **keywords)
        return job

    def addGenericPipeCommandOutput2FileJob(self, executable=None, executableFile=None, \
                    outputFile=None, \
                    parentJobLs=None, extraDependentInputLs=None, extraOutputLs=None, transferOutput=False, \
                    extraArguments=None, extraArgumentList=None, sshDBTunnel=None,\
                    job_max_memory=2000, walltime=120, **keywords):
        """
        Examples:
            sortedSNPID2NewCoordinateFile = File(os.path.join(reduceOutputDirJob.output, 'SNPID2NewCoordinates.sorted.tsv'))
            sortSNPID2NewCoordinatesJob = self.addGenericPipeCommandOutput2FileJob(executable=self.pipeCommandOutput2File, \
                    executableFile=self.sortExecutableFile, \
                    outputFile=sortedSNPID2NewCoordinateFile, \
                    parentJobLs=[reduceJob], \
                    extraDependentInputLs=[reduceJob.output], \
                    extraOutputLs=None, transferOutput=False, \
                    extraArguments=None, \
                    extraArgumentList=["-k 3,3 -k4,4n -t$'\t'", reduceJob.output], \
                    sshDBTunnel=None,\
                    job_max_memory=4000, walltime=120)

            extraArgumentList.append(alignment_method.command)	#add mem first
            extraArgumentList.extend(["-a -M", refFastaFile] + fastqFileList)
            alignmentJob = self.addGenericPipeCommandOutput2FileJob(executable=self.BWA_Mem, executableFile=self.bwa, \
                        outputFile=alignmentSamF, \
                        parentJobLs=parentJobLs, extraDependentInputLs=[refFastaFile] + fastqFileList, \
                        extraOutputLs=None, transferOutput=transferOutput, \
                        extraArguments=None, extraArgumentList=extraArgumentList, \
                        sshDBTunnel=None,\
                        job_max_memory=aln_job_max_memory, walltime=aln_job_walltime, no_of_cpus=no_of_aln_threads, \
                        **keywords)

            sortedVCFFile = File(os.path.join(self.liftOverReduceDirJob.output, '%s.sorted.vcf'%(seqTitle)))
            vcfSorterJob = self.addGenericPipeCommandOutput2FileJob(executable=None, executableFile=self.vcfsorterExecutableFile, \
                    outputFile=sortedVCFFile, \
                    parentJobLs=[selectOneChromosomeVCFJob, self.liftOverReduceDirJob], \
                    extraDependentInputLs=[self.newRegisterReferenceData.refPicardFastaDictF, selectOneChromosomeVCFJob.output], \
                    extraOutputLs=None, transferOutput=False, \
                    extraArguments=None, extraArgumentList=[self.newRegisterReferenceData.refPicardFastaDictF, selectOneChromosomeVCFJob.output], \
                    job_max_memory=job_max_memory, walltime=walltime)

        executableFile could be None
        use pipeCommandOutput2File to get output piped into outputF
            no frontArgumentList exposed because the order of initial arguments are fixed.
                ~/pymodule/shell/pipeCommandOutput2File.sh commandPath outputFname [commandArguments]


        """
        if executable is None:
            executable = self.pipeCommandOutput2File
        if extraDependentInputLs is None:
            extraDependentInputLs = []
        frontArgumentList = []
        if executableFile:
            extraDependentInputLs.append(executableFile)
            frontArgumentList.append(executableFile)

        job= self.addGenericJob(executable=executable, \
                    frontArgumentList=frontArgumentList,\
                    inputFile=None, inputArgumentOption=None,\
                    outputFile=outputFile, outputArgumentOption=None,\
                parentJobLs=parentJobLs, extraDependentInputLs=extraDependentInputLs, \
                extraOutputLs=extraOutputLs, extraArguments=extraArguments, \
                transferOutput=transferOutput, \
                extraArgumentList=extraArgumentList, key2ObjectForJob=None, job_max_memory=job_max_memory, \
                sshDBTunnel=sshDBTunnel, walltime=walltime, **keywords)
        return job

    def setJobOutputFileTransferFlag(self, job=None, transferOutput=False, outputLs=None):
        """
        2012.8.17
            assume all output files in job.outputLs
        """
        if outputLs is None and getattr(job, 'outputLs', None):
            outputLs = job.outputLs

        for output in outputLs:
            job.uses(output, transfer=transferOutput, register=True, link=Link.OUTPUT)

    def getJVMMemRequirment(self, job_max_memory=5000, minMemory=2000, permSizeFraction=0,
                        MaxPermSizeUpperBound=35000):
        """
        Java 8 does not support PermSize anymore. set permSizeFraction to 0.
        handle when job_max_memory is None and minMemory is None.
        if a job's virtual memory (1.2X=self.jvmVirtualByPhysicalMemoryRatio, of memory request) exceeds request, it'll abort.
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
            minMemory = 2000
        #permSizeFraction is set to 0 due to newer Java no longer needs it.
        permSizeFraction = 0
        #MaxPermSize_user = int(job_max_memory*permSizeFraction)
        mxMemory_user = int(job_max_memory*(1-permSizeFraction))
        #MaxPermSize= min(MaxPermSizeUpperBound, max(minMemory/2, MaxPermSize_user))
        #PermSize=MaxPermSize*3/4
        mxMemory = max(minMemory, mxMemory_user)
        msMemory = mxMemory*3/4
        #-XX:+UseGCOverheadLimit
            #Use a policy that limits the proportion of the VM's time that is spent in GC before an OutOfMemory error is thrown. (Introduced in 6.)
        #-XX:-UseGCOverheadLimit would disable the policy.
        memRequirementInStr = "-Xms%sm -Xmx%sm"%(msMemory, mxMemory)	# -XX:PermSize=%sm -XX:MaxPermSize=%sm"%\
                    #, PermSize, MaxPermSize)
        
        memRequirement = int(mxMemory*self.jvmVirtualByPhysicalMemoryRatio)
        #if a job's virtual memory (1.2X of memory request) exceeds request, it'll abort.
        return PassingData(memRequirementInStr=memRequirementInStr, memRequirement=memRequirement)

    def scaleJobWalltimeOrMemoryBasedOnInput(self, realInputVolume=10, baseInputVolume=4, baseJobPropertyValue=120, \
                                            minJobPropertyValue=120, maxJobPropertyValue=1440):
        """
        assume it's integer.
        walltime is in minutes.
        """
        walltime = min(max(minJobPropertyValue, float(realInputVolume)/float(baseInputVolume)*baseJobPropertyValue), \
                                    maxJobPropertyValue)	#in minutes
        return PassingData(value=int(walltime))

    def addMkDirJob(self, executable=None, outputDir=None, namespace=None, version=None,\
            parentJobLs=None, extraDependentInputLs=None):
        """
        wrapper around addMkDirJob()
            i.e.
            simulateOutputDirJob = self.addMkDirJob(outputDir=simulateOutputDir)
        """
        from pymodule.pegasus import yh_pegasus
        if namespace is None:
            namespace = self.namespace
        if version is None:
            version = self.version
        if executable is None:
            executable = self.mkdirWrap

        return addMkDirJob(workflow=self, mkdir=executable, outputDir=outputDir, namespace=namespace, \
                            version=version,\
                            parentJobLs=parentJobLs, extraDependentInputLs=extraDependentInputLs)

    def setup_run(self):
        """
        assign all returned data to self, rather than pdata (pdata has become self)
        wrap all standard pre-run() related functions into this function.
            setting up for run(), called by run()
        """
        if self.debug:
            import pdb
            pdb.set_trace()

        if getattr(self, 'db_main', None):
            session = self.db_main.session
            session.begin(subtransactions=True)

            if not self.data_dir:
                self.data_dir = self.db_main.data_dir

            if not self.local_data_dir:
                self.local_data_dir = self.db_main.data_dir

        self.workflow = self
        self.registerJars()
        self.registerCustomJars()
        self.registerExecutables()
        self.registerCustomExecutables()

        return self

    def end_run(self):
        """
        To be called in the end of run()
        """
        # Write the DAX to stdout
        if self.isDAGWrittenToDisk:
            sys.stderr.write("Warning: the dag has been written to a file already (writeXML() has been called). No more calling.\n")
        else:
            outf = open(self.outputFname, 'w')
            self.writeXML(outf)
            self.isDAGWrittenToDisk = True

        if getattr(self, 'db_main', None):	#bugfix
            session = self.db_main.session
            if self.commit:
                session.commit()
            else:
                session.rollback()

if __name__ == '__main__':
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("-i", "--input_file", type=str, required=True,
                    help="the path to the input file.")
    ap.add_argument("-o", "--output_file", type=str, required=True,
                    help="the path to the output file.")
    ap.add_argument("-s", "--source_code_dir", type=str, 
            default=os.path.expanduser('~/src/mygit/'), 
            help="the path to the source code dir. (default: %(default)s)")
    args = ap.parse_args()

    instance = Workflow(po.arguments, **po.long_option2value)
    instance.run()
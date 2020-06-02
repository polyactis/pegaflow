#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import logging
import os
import sys
from . DAX3 import Executable, File, PFN, Profile, Namespace, Link
from . DAX3 import Job, Dependency

version = '0.2.2'
namespace = "pegasus"
pegasus_version = "1.0"
architecture = "x86_64"
operatingSystem = "linux"


def setExecutableClusterSize(workflow, executable, cluster_size=1):
    """
    it will remove the clustering profile if the new cluster_size is <1.
    """
    if cluster_size is not None and cluster_size > 1:
        clusteringProf = Profile(Namespace.PEGASUS, key="clusters.size",
            value=f"{cluster_size}")
        if executable.hasProfile(clusteringProf):
            executable.removeProfile(clusteringProf)
        executable.addProfile(clusteringProf)
    if not workflow.hasExecutable(executable):
        workflow.addExecutable(executable)
        #removeExecutable() is its counterpart
        setattr(workflow, executable.name, executable)
    return executable


def registerExecutable(workflow, path, site_handler,
    executableName=None, cluster_size=1, checkExecutable=True):
    if checkExecutable:
        if path.find('file://') == 0:
            fs_path = path[6:]
        else:
            fs_path = path
        if not (os.path.isfile(fs_path) and os.access(fs_path, os.X_OK)):
            logging.error(f"registerExecutable(): "
                f"executable {path} does not exist or is not an executable.")
            raise
    if executableName is None:
        executableName = os.path.basename(path)
    executable = Executable(namespace=namespace, name=executableName,
        os=operatingSystem, arch=architecture,
        installed=True, version=pegasus_version)
    executable.addPFN(PFN("file://" + os.path.abspath(path), site_handler))
    workflow.addExecutable(executable)
    setExecutableClusterSize(workflow, executable, cluster_size=cluster_size)
    return executable


class PassingData(object):
    """
    a class to hold any data structure
    """
    def __init__(self, **keywords):
        """
        add keyword handling
        """
        for argument_key, argument_value in keywords.items():
            setattr(self, argument_key, argument_value)
    
    def __str__(self):
        """
        a string-formatting function
        """
        return_ls = []
        for attributeName in dir(self):
            if attributeName.find('__')==0:
                continue
            value = getattr(self, attributeName, None)
            return_ls.append("%s = %s"%(attributeName, value))
            
        return ", ".join(return_ls)
    
    def __getitem__(self, key):
        """
        enable it to work like a dictionary
        i.e. pdata.chromosome or pdata['chromosome'] is equivalent if
         attribute 0 is chromosome.
        """
        return self.__getattribute__(key)


def getListOutOfStr(list_in_str=None, data_type=int, separator1=',',
    separator2='-'):
    """
    This function parses a list from a string representation of a list,
        such as '1,3-7,11'=[1,3,4,5,6,7,11].
    If only separator2, '-', is used ,all numbers have to be integers.
    If all are separated by separator1, it could be in non-int data_type.
    strip the strings as much as u can.
    if separator2 is None or nothing or 0, it wont' be used.

    Examples:
        self.chromosomeList = utils.getListOutOfStr('1-5,7,9', data_type=str,
            separator2=None)
    """
    list_to_return = []
    if list_in_str == '' or list_in_str is None:
        return list_to_return
    list_in_str = list_in_str.strip()
    if list_in_str == '' or list_in_str is None:
        return list_to_return
    if type(list_in_str) == int:
        #just one integer, put it in and return immediately
        return [list_in_str]
    index_anchor_ls = list_in_str.split(separator1)
    for index_anchor in index_anchor_ls:
        index_anchor = index_anchor.strip()
        if len(index_anchor) == 0:
            continue
        if separator2:
            start_stop_tup = index_anchor.split(separator2)
        else:
            start_stop_tup = [index_anchor]
        if len(start_stop_tup) == 1:
            list_to_return.append(data_type(start_stop_tup[0]))
        elif len(start_stop_tup) > 1:
            start_stop_tup = map(int, start_stop_tup)
            list_to_return += range(start_stop_tup[0], start_stop_tup[1]+1)
    list_to_return = map(data_type, list_to_return)
    return list_to_return


def getRealPrefixSuffix(path, fakeSuffix='.gz',
    fakeSuffixSet =set(['.gz', '.zip', '.bz2', '.bz'])):
    """
    The purpose of this function is to get the prefix, suffix of a filename
         regardless of whether it has two suffices (gzipped) or one.
    i.e.
        A file name is either sequence_628BWAAXX_4_1.fastq.gz or
            sequence_628BWAAXX_4_1.fastq (without gz).
        This function returns ('sequence_628BWAAXX_4_1', '.fastq')

    "." is considered part of the filename suffix.
    """
    fname_prefix, fname_suffix = os.path.splitext(path)
    if fakeSuffix and fakeSuffix not in fakeSuffixSet:
        fakeSuffixSet.add(fakeSuffix)
    while fname_suffix in fakeSuffixSet:
        fname_prefix, fname_suffix = os.path.splitext(fname_prefix)
    return fname_prefix, fname_suffix


def addMkDirJob(workflow, executable, outputDir, frontArgumentList=None,
    parentJobLs=None,
    extraDependentInputLs=None):
    """
    """
    # Add a mkdir job for any directory.
    job = Job(name=executable.name, namespace=namespace,
        version=pegasus_version)
    if frontArgumentList:
        job.addArguments(*frontArgumentList)
    job.addArguments(outputDir)
    #two attributes for child jobs to get the output directory.
    job.folder = outputDir
    job.output = outputDir
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


def setJobResourceRequirement(job=None, job_max_memory=500, no_of_cpus=1,
    walltime=180, sshDBTunnel=0, db=None, io=None, gpu=None):
    """
    db: integer.
        A custom resource of condor to avoid too many programs
            writing to a database server simultaneously.
        The integer is equal to the number of heavy db connections a job requires.
        Light DB interaction (occasional query) can be regarded as db=0.
        Each condor slave has a limited DB(=6) connection resource.
        Condor needs a custom resource setup, i.e.
            MACHINE_RESOURCE_DB=6
            JOB_DEFAULT_REQUESTDB=0
    io: an integer between 0 and 100.
        A custom resource of condor to avoid too many programs
            writing to the filesystem.
        Each condor slave has a maximum 100 IO resource.
        Condor needs a custom resource setup, i.e.
            MACHINE_RESOURCE_IO=100
            JOB_DEFAULT_REQUESTIO=0
    gpu: integer, the number of GPUs a job requests.
    job_max_memory: integer, unit in MB.
        if job_max_memory is None, then skip setting memory requirement.
        if job_max_memory is "" or 0 or "0", then assign 500 (MB) to it.
    sshDBTunnel:
        =1: this job needs a ssh tunnel to access an external database server.
        =anything else: no need for that.
    walltime: integer, unit in minutes.
        set walltime default to 180 minutes (3 hours).
    """
    condorJobRequirementLs = []
    if job_max_memory == "" or job_max_memory == 0 or job_max_memory == "0":
        job_max_memory = 500
    if job_max_memory:
        job.addProfile(Profile(Namespace.GLOBUS, key="maxmemory",
            value=f"{job_max_memory}"))
       	#for dynamic slots
        job.addProfile(Profile(Namespace.CONDOR, key="request_memory",
            value=f"{job_max_memory}"))
        condorJobRequirementLs.append(f"(memory>={job_max_memory})")
    
    if no_of_cpus:
        job.addProfile(Profile(Namespace.CONDOR, key="request_cpus",
            value=f"{no_of_cpus}"))
    if db:
        job.addProfile(Profile(Namespace.CONDOR, key="request_db",
            value=f"{db}"))
    if io:
        job.addProfile(Profile(Namespace.CONDOR, key="request_io",
            value=f"{io}"))
    if gpu:
        job.addProfile(Profile(Namespace.CONDOR, key="request_gpu",
            value=f"{gpu}"))
    if walltime:
        #scale walltime according to cluster_size
        job.addProfile(Profile(Namespace.GLOBUS, key="maxwalltime",
            value=f"{walltime}"))
        #TimeToLive is in seconds
        condorJobRequirementLs.append(
            f"(Target.TimeToLive>={int(walltime)*60})")
    if sshDBTunnel == 1:
        condorJobRequirementLs.append(f"(sshDBTunnel=={sshDBTunnel})")
    
    #key='requirements' could only be added once for the condor profile
    job.addProfile(Profile(Namespace.CONDOR, key="requirements",
        value=" && ".join(condorJobRequirementLs)))


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

def getExecutableClusterSize(executable=None):
    """
    default is None
    """
    cluster_size = None
    clusteringProf = Profile(Namespace.PEGASUS, key="clusters.size", value="1")
    for profile in executable.profiles:
        #__hash__ only involves namespace + key 
        if clusteringProf.__hash__() == profile.__hash__():
            cluster_size = profile.value
    return cluster_size


def registerOneInputFile(workflow, input_path, site_handler, folderName="",
    useAbsolutePathAsPegasusFileName=False,
    pegasusFileName=None, checkFileExistence=True):
    """
    Register a single input file to pegasus.

    Examples:
        pegasusFile = registerOneInputFile(input_path='/tmp/abc.txt')
        
    useAbsolutePathAsPegasusFileName:
        This would render the file to be referred as the absolute path on
         the running nodes.
        And pegasus will not symlink or copy/transfer the file.
        Set it to True only if you don't want to add the file to the job
            as an INPUT dependency (as it's accessed through abs path).
    folderName: if given, it will cause the file to be put into that folder
         (relative path) within the pegasus workflow running folder.
        This folder needs to be created by a mkdir job.
    Return: pegasusFile.abspath or pegasusFile.absPath is the absolute
        path of the file.
    """
    if not pegasusFileName:
        if useAbsolutePathAsPegasusFileName:
           	#this will stop symlinking/transferring,
            # and also no need to indicate them as file dependency for jobs.
            pegasusFileName = os.path.abspath(input_path)
        else:
            pegasusFileName = os.path.join(folderName, os.path.basename(
                input_path))
    pegasusFile = File(pegasusFileName)
    if checkFileExistence and not os.path.isfile(input_path):
        logging.error(f"From registerOneInputFile(): {input_path}"
            f" does not exist.")
        raise
    pegasusFile.abspath = os.path.abspath(input_path)
    pegasusFile.absPath = pegasusFile.abspath
    pegasusFile.addPFN(PFN("file://" + pegasusFile.abspath, site_handler))
    if not workflow.hasFile(pegasusFile):
        workflow.addFile(pegasusFile)
    return pegasusFile


def registerFilesOfInputDir(workflow, inputDir, input_path_list=None,
    inputSuffixSet=None, site_handler=None, pegasusFolderName='',
    **keywords):
    """
    This function registers all files in inputDir (if present) and
         input_path_list (if not None).
    """
    if input_path_list is None:
        input_path_list = []
    if inputDir and os.path.isdir(inputDir):
        fnameLs = os.listdir(inputDir)
        for fname in fnameLs:
            input_path = os.path.realpath(os.path.join(inputDir, fname))
            input_path_list.append(input_path)

    print(f"Registering {len(input_path_list)} input files with suffix in"
        f" {inputSuffixSet} ... ", flush=True, end='')
    inputFileList = []
    counter = 0
    for input_path in input_path_list:
        counter += 1
        # file.fastq.gz's suffix is .fastq, not .gz.
        suffix = getRealPrefixSuffix(input_path)[1]
        if inputSuffixSet is not None and len(inputSuffixSet)>0 and \
            suffix not in inputSuffixSet:
            #skip input whose suffix is not in inputSuffixSet if inputSuffixSet
            #  is a non-empty set.
            continue
        inputFile = File(os.path.join(pegasusFolderName,
            os.path.basename(input_path)))
        inputFile.addPFN(PFN("file://" + input_path, site_handler))
        inputFile.abspath = input_path
        workflow.addFile(inputFile)
        inputFileList.append(inputFile)
    print(f"{len(inputFileList)} out of {len(input_path_list)} files"
        f" registered. Done.", flush=True)
    return inputFileList


def addJob2workflow(workflow=None, executable=None, argv=None,
    input_file_list=None,
    output_file_transfer_list=None, output_file_notransfer_list=None,
    parent_job_ls=None,
    job_max_memory=None, no_of_cpus=None,
    walltime=None, sshDBTunnel=None, db=None, io=None, gpu=None
    ):
    the_job = Job(namespace=namespace, name=executable.name,
        version=pegasus_version)
    if argv:
        the_job.addArguments(*argv)
    if input_file_list:
        for input_file in input_file_list:
            the_job.uses(input_file, link=Link.INPUT, transfer=True,
                register=True)
    
    if output_file_transfer_list:
        for output_file in output_file_transfer_list:
            the_job.uses(output_file, link=Link.OUTPUT, transfer=True)
    if output_file_notransfer_list:
        for output_file in output_file_notransfer_list:
            the_job.uses(output_file, link=Link.OUTPUT, transfer=False)
    workflow.addJob(the_job)
    if parent_job_ls:
        for parent_job in parent_job_ls:
            if parent_job:
                workflow.addDependency(
                    Dependency(parent=parent_job, child=the_job))
    setJobResourceRequirement(job=the_job, job_max_memory=job_max_memory,
        no_of_cpus=no_of_cpus, walltime=walltime, sshDBTunnel=sshDBTunnel,
        db=db, io=io, gpu=gpu)
    return the_job


class Logger(logging.getLoggerClass()):
    "A custom logger for Pegasus with TRACE level"
    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    TRACE = logging.DEBUG - 1
    NOTSET = logging.NOTSET

    def __init__(self, name, level=0):
        logging.Logger.__init__(self, name, level)

    def trace(self, message, *args, **kwargs):
        "Log a TRACE level message"
        self.log(Logger.TRACE, message, *args, **kwargs)

# Add a TRACE level to logging
logging.addLevelName(Logger.TRACE, "TRACE")

# Use our own logger class, which has trace
logging.setLoggerClass(Logger)

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
from .api import File, Job, Transformation
from .api import Arch, OS
from .api import Workflow as PegaWorkflow

version = '1.0.0'
namespace = "pegasus"
pegasus_version = "1.0"

def setExecutableClusterSize(workflow:PegaWorkflow, executable:Transformation,
    cluster_size=1):
    """
    """
    if cluster_size is not None and cluster_size > 1:
        if cluster_size > 1:
            executable.add_pegasus_profile(clusters_size=cluster_size)
        #workflow.transformation_catalog.add_transformations(executable)
        #setattr(workflow, executable.name, executable)
    return executable


def registerExecutable(workflow:PegaWorkflow, path:str, site_handler:str,
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
    abspath = os.path.abspath(os.path.expanduser(path))
    executable = Transformation(name=executableName, site=site_handler, \
            pfn=abspath,
            is_stageable=True, arch=Arch.X86_64,
            os_type=OS.LINUX, version=pegasus_version)
    executable.abspath = abspath
    workflow.transformation_catalog.add_transformations(executable)
    setattr(workflow, executable.name, executable)
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


def addMkDirJob(workflow:PegaWorkflow, executable:Transformation, outputDir:str,
    frontArgumentList=None,
    parentJobLs=None,
    extraDependentInputLs=None):
    """
    """
    # Add a mkdir job for any directory.
    job = Job(executable)
    #.add_inputs(fa).add_outputs(fb1, fb2)
    if frontArgumentList:
        job.add_args(*frontArgumentList)
        #.add_args("-a", "preprocess", "-T", "3", "-i", fa, "-o", fb1, fb2)\
    job.add_args(outputDir)
    #two attributes for child jobs to get the output directory.
    job.folder = outputDir
    job.output = outputDir
    workflow.add_jobs(job)
    if parentJobLs:
        for parentJob in parentJobLs:
            if parentJob:
                workflow.add_dependency(job, parents=[parentJob])
    if extraDependentInputLs:
        for input in extraDependentInputLs:
            if input is not None:
                job.add_inputs(input)
    if hasattr(workflow, 'no_of_jobs'):
        workflow.no_of_jobs += 1
    return job


def setJobResourceRequirement(job:Job=None, job_max_memory=500, no_of_cpus=1,
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
        job.add_globus_profile(max_memory=f"{job_max_memory}MB")
        job.add_pegasus_profile(memory=f"{job_max_memory}MB")
        job.add_condor_profile(request_memory=f"{job_max_memory}MB")
        condorJobRequirementLs.append(f"(memory>={job_max_memory}MB)")
    
    if no_of_cpus:
        job.add_pegasus_profile(cores=no_of_cpus)
        job.add_condor_profile(request_cpus=f"{no_of_cpus}")
    if db:
        job.add_condor_profile(key="request_db", value=f"{db}")
    if io:
        job.add_condor_profile(key="request_io", value=f"{io}")
    if gpu:
        job.add_pegasus_profile(gpus=gpu)
        job.add_condor_profile(request_gpus=f"{gpu}")
    if walltime:
        job.add_globus_profile(max_wall_time=f"{walltime}")
        #TimeToLive is in seconds
        condorJobRequirementLs.append(
            f"(Target.TimeToLive>={int(walltime)*60})")
    if sshDBTunnel == 1:
        condorJobRequirementLs.append(f"(sshDBTunnel=={sshDBTunnel})")
    
    #key='requirements' could only be added once for the condor profile
    job.add_condor_profile(requirements=" && ".join(condorJobRequirementLs))


def getAbsPathOutOfExecutable(executable:Transformation):
    """
    This function extracts path out of a registered executable.
        The executable is a registered pegasus executable with PFNs.
    """
    transformation_site_0 = executable.sites.values[0]
    pfn = transformation_site_0.pfn
    #pfn = (list(executable.pfns)[0])
    #the url looks like "file:///home/crocea/bin/bwa"
    #return pfn.url[7:]
    return executable.abspath


def getAbsPathOutOfFile(file):
    """
    call getAbsPathOutOfExecutable
    """
    return getAbsPathOutOfExecutable(file)

def getExecutableClusterSize(executable:Transformation=None):
    """
    default is None
    """
    cluster_size = None
    pegasus_prof_dict = executable.profiles.get("pegasus", None)
    if pegasus_prof_dict and "clusters.size" in pegasus_prof_dict:
        cluster_size = pegasus_prof_dict["clusters.size"]
    return cluster_size


def registerOneInputFile(workflow:PegaWorkflow, input_path:str, site_handler:str,
    folderName="",
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
        logging.error(f"From registerOneInputFile(): {input_path} does not exist.")
        raise
    pegasusFile.abspath = os.path.abspath(input_path)
    pegasusFile.absPath = pegasusFile.abspath
    workflow.replica_catalog.add_replica(site_handler, lfn=pegasusFile, pfn=pegasusFile.abspath)
    return pegasusFile


def registerFilesOfInputDir(workflow:PegaWorkflow, inputDir:str, input_path_list=None,
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
    input_file_list = []
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
        input_file = File(os.path.join(pegasusFolderName,
            os.path.basename(input_path)))
        input_file.abspath = os.path.abspath(input_path)
        input_file.absPath = input_file.abspath
        workflow.replica_catalog.add_replica(site_handler, lfn=input_file,
            pfn=input_file.abspath)
        input_file_list.append(input_file)
    print(f"{len(input_file_list)} out of {len(input_path_list)} files"
        f" registered. Done.", flush=True)
    return input_file_list


def addJob2workflow(workflow:PegaWorkflow=None, executable:Transformation=None,
    argv=None, input_file_list=None,
    output_file_transfer_list=None, output_file_notransfer_list=None,
    parent_job_ls=None,
    job_max_memory=None, no_of_cpus=None,
    walltime=None, sshDBTunnel=None, db=None, io=None, gpu=None
    ):
    the_job = Job(executable)
    if argv:
        the_job.add_args(*argv)
    if input_file_list:
        for input_file in input_file_list:
            the_job.add_inputs(input_file)
    
    if output_file_transfer_list:
        for output_file in output_file_transfer_list:
            the_job.add_outputs(output_file, stage_out=True, register_replica=False)
    if output_file_notransfer_list:
        for output_file in output_file_notransfer_list:
            the_job.add_outputs(output_file, stage_out=False, register_replica=False)
    workflow.add_jobs(the_job)
    if parent_job_ls:
        for parent_job in parent_job_ls:
            if parent_job:
                workflow.add_dependency(the_job, parents=[parent_job])
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

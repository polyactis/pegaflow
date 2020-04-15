#!/usr/bin/env python3
"""
A Pegasus example that does not use any class.
"""
import copy
import sys, os
from argparse import ArgumentParser
from pegaflow.DAX3 import File, Link, ADAG, Dependency
from pegaflow import Workflow

src_dir = os.path.dirname(os.path.abspath(__file__))

if __name__ == '__main__':
    ap = ArgumentParser()
    ap.add_argument("-i", "--input_folder", type=str, required=True,
        help="The folder that contains input files.")
    ap.add_argument("--inputSuffixList", type=str, required=True,
        help='Coma-separated list of input file suffices. Used to exclude input files.'
        'If None, no exclusion. The dot is part of the suffix, i.e. .tsv, not tsv.'
        'Common zip suffices (.gz, .bz2, .zip, .bz) will be ignored in obtaining the suffix.')
    ap.add_argument("-o", "--output_file", type=str, required=True,
            help="the path to the output xml file to contain the dag.")
    ap.add_argument("-l", "--site_handler", type=str, required=True,
        help="The name of the computing site where the jobs run and executables are stored. "
        "Check your Pegasus configuration in submit.sh.")
    ap.add_argument("-C", "--cluster_size", type=int, default=1,
        help="Default: %(default)s. "
        "This number decides how many of pegasus jobs should be clustered into one job. "
        "Good if your workflow contains many quick jobs. "
        "It will reduce Pegasus monitor I/O.")
    args = ap.parse_args()
    inputSuffixList = Workflow.getListOutOfStr(list_in_str=args.inputSuffixList, data_type=str, 
            separator1=',', separator2='-')
    inputSuffixSet = set(inputSuffixList)
    wflow = ADAG("pegasus_test")
    input_file_list = Workflow.registerFilesOfInputDir(workflow=wflow, \
        inputDir=args.input_folder,
        inputSuffixSet=inputSuffixSet, site_handler=args.site_handler, \
        checkFileExistence=True)
    # use this shell wrapper
    pipe2File_path = os.path.join(src_dir, '../tools/pipe2File.sh')
    
    pipe2File = Workflow.registerExecutable(wflow, pipe2File_path, \
                cluster_size=args.cluster_size, site_handler=args.site_handler)
    mergeWC = Workflow.registerExecutable(wflow, pipe2File_path, \
                cluster_size=args.cluster_size, site_handler=args.site_handler,
                executableName='mergeWC')
    sleep = Workflow.registerExecutable(wflow, path="/bin/sleep", cluster_size=args.cluster_size,\
        site_handler=args.site_handler)

    mergedOutputFile = File("merged.txt")
    mergeJob= Workflow.addJob2workflow(workflow=wflow, executable=mergeWC,
                    input_file_list=[],
                    output_file_transfer_list=[mergedOutputFile],
                    output_file_notransfer_list=[],
                    argv=[mergedOutputFile, '/bin/cat'])
    wflow.addJob(mergeJob)
    # request 500MB memory, 30 minutes run time (walltime).
    Workflow.setJobResourceRequirement(job=mergeJob, job_max_memory=500, walltime=30)

    for input_file in input_file_list:
        ## wc each input file
        output_file = File(f'{input_file.name}.wc.output.txt')
        wcJob = Workflow.addJob2workflow(workflow=wflow, executable=pipe2File,
                    input_file_list=[input_file],
                    output_file_transfer_list=None,
                    output_file_notransfer_list=[output_file],
                    argv=[output_file, '/bin/cat', input_file])
        Workflow.setJobResourceRequirement(job=wcJob, job_max_memory=200)
        wflow.addJob(wcJob)
        #add wcJob's output as input to mergeJob
        mergeJob.addArguments(output_file)
        mergeJob.uses(output_file, link=Link.INPUT)
        wflow.addDependency(Dependency(parent=wcJob, child=mergeJob))
    # a sleep job to slow down the workflow for 30 seconds
    # sleepJob has no output.
    sleepJob = Workflow.addJob2workflow(workflow=wflow, executable=sleep,
                    input_file_list=[],
                    output_file_transfer_list=None,
                    output_file_notransfer_list=None,
                    argv=['30s'])
    wflow.addJob(sleepJob)
    wflow.addDependency(Dependency(parent=sleepJob, child=mergeJob))
    wflow.writeXML(open(args.output_file, 'w'))

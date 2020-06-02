#!/usr/bin/env python3
"""
A Pegasus example that does not use any class.
"""
import sys, os
from argparse import ArgumentParser
from pegaflow.DAX3 import File, Link, ADAG, Dependency
import pegaflow

src_dir = os.path.dirname(os.path.abspath(__file__))

if __name__ == '__main__':
    ap = ArgumentParser()
    ap.add_argument("-i", "--input_folder", type=str, required=True,
        help="The folder that contains input files.")
    ap.add_argument("--inputSuffixList", type=str, required=True,
        help='Coma-separated list of input file suffices. Used to exclude'
        ' input files.'
        'If None, no exclusion. The dot is part of the suffix, i.e. .tsv,'
        ' not tsv.'
        'Common zip suffices (.gz, .bz2, .zip, .bz) will be ignored in'
        ' obtaining the suffix.')
    ap.add_argument("-o", "--output_file", type=str, required=True,
            help="the path to the output xml file to contain the dag.")
    ap.add_argument("-l", "--site_handler", type=str, required=True,
        help="The name of the computing site where the jobs run and"
        " executables are stored. "
        "Check your Pegasus configuration in submit.sh.")
    ap.add_argument("-C", "--cluster_size", type=int, default=1,
        help="Default: %(default)s. "
        "This number decides how many of pegasus jobs should be clustered"
        " into one job. Good if your workflow contains many quick jobs. "
        "It will reduce Pegasus monitor I/O.")
    args = ap.parse_args()
    inputSuffixList = pegaflow.getListOutOfStr(
        list_in_str=args.inputSuffixList, data_type=str,
        separator1=',', separator2='-')
    inputSuffixSet = set(inputSuffixList)
    wflow = ADAG("pegasus_test")
    input_file_list = pegaflow.registerFilesOfInputDir(wflow,
        args.input_folder, inputSuffixSet=inputSuffixSet,
        pegasusFolderName='input', site_handler=args.site_handler,
        checkFileExistence=True)
    # use this shell wrapper for shell commands that output to stdout
    pipe2File_path = os.path.join(src_dir, '../tools/pipe2File.sh')
    
    pipe2File = pegaflow.registerExecutable(wflow, pipe2File_path,
                args.site_handler, cluster_size=args.cluster_size)
    mergeWC = pegaflow.registerExecutable(wflow, pipe2File_path,
        args.site_handler,
        executableName='mergeWC', cluster_size=args.cluster_size)
    sleep = pegaflow.registerExecutable(wflow, "/bin/sleep",
        args.site_handler,
        cluster_size=args.cluster_size)

    mergedOutputFile = File("merged.txt")
    # request 500MB memory, 30 minutes run time (walltime).
    mergeJob= pegaflow.addJob2workflow(wflow, mergeWC,
        argv=[mergedOutputFile, '/bin/cat'],
        input_file_list=None,
        output_file_transfer_list=[mergedOutputFile],
        output_file_notransfer_list=None,
        job_max_memory=500,
        walltime=30)

    mkdir = pegaflow.registerExecutable(wflow, '/bin/mkdir', args.site_handler)
    outputDir = 'output'
    outputDirJob = pegaflow.addMkDirJob(wflow, mkdir, outputDir)

    ## wc each input file
    for input_file in input_file_list:
        output_file = File(os.path.join(outputDir,
            f'{os.path.basename(input_file.name)}.wc.output.txt'))
        wcJob = pegaflow.addJob2workflow(workflow=wflow, executable=pipe2File,
            argv=[output_file, '/usr/bin/wc', input_file],
            input_file_list=[input_file],
            output_file_transfer_list=None,
            output_file_notransfer_list=[output_file],
            parent_job_ls=[outputDirJob],
            job_max_memory=200,
            )
        #add wcJob's output as input to mergeJob
        mergeJob.addArguments(output_file)
        mergeJob.uses(output_file, link=Link.INPUT)
        wflow.addDependency(Dependency(parent=wcJob, child=mergeJob))
    # a sleep job to slow down the workflow for 30 seconds
    # sleepJob has no output.
    sleepJob = pegaflow.addJob2workflow(workflow=wflow, executable=sleep,
        argv=[30],
        parent_job_ls=[mergeJob])
    wflow.writeXML(open(args.output_file, 'w'))

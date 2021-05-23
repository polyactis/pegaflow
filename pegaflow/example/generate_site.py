#!/usr/bin/env python3

from Pegasus.api import Arch, Directory, FileServer, Grid, Operation, OS, Scheduler, Site, SiteCatalog, SupportedJobs
import os, sys
import time

def create_site_catalog(top_dir: str, dag_file_path: str, add_staging_site=False):
    """

    """
    # create a SiteCatalog object
    sc = SiteCatalog()

    # create a "local" site
    local = Site("local", arch=Arch.X86_64, os_type=OS.LINUX)
    top_dir = os.path.abspath(top_dir)
    t = time.asctime().split()[3].replace(':', '')
    month = time.asctime().split()[1]
    day = time.asctime().split()[2]
    year = time.asctime().split()[-1]
    dag_file_path_ls = os.path.splitext(dag_file_path)[0].split('/');
    n = len(dag_file_path_ls);
    #remove the first folder (usually "dags/") in the dag file path
    output_rel_path = f"{'/'.join(dag_file_path_ls[-(n-1):])}.{year}.{month}.{day}.T{t}"

    scratch_path = os.path.join(top_dir, "scratch")
    output_path = os.path.join(top_dir, output_rel_path)

    # create and add a shared scratch and local storage directories to the site "local"
    local_shared_scratch_dir = Directory(Directory.SHARED_SCRATCH, path=scratch_path)\
        .add_file_servers(FileServer("file://" + scratch_path, Operation.ALL))

    local_local_storage_dir = Directory(Directory.LOCAL_STORAGE, path=output_path)\
        .add_file_servers(FileServer("file://" + output_path, Operation.ALL))

    local.add_directories(local_shared_scratch_dir, local_local_storage_dir)

    # create a "condor" site
    condor = Site("condor", arch=Arch.X86_64, os_type=OS.LINUX)
    condor.add_pegasus_profile(style="condor")\
        .add_pegasus_profile(auxillary_local="true")\
        .add_condor_profile(universe="vanilla")
    
    condor.add_env(HOME=os.path.expanduser('~'))
    
    # create and add job managers to the site "condor"
    """    
    condor.add_grids(
        Grid(Grid.GT5, contact="smarty.isi.edu/jobmanager-pbs", scheduler_type=Scheduler.PBS, 
            job_type=SupportedJobs.AUXILLARY),
        Grid(Grid.GT5, contact="smarty.isi.edu/jobmanager-pbs", scheduler_type=Scheduler.PBS,
            job_type=SupportedJobs.COMPUTE)
    )
    """
    # create and add a shared scratch directory to the site "condor"
    condor.add_directories(local_shared_scratch_dir)
    
    #condor_shared_scratch_dir = Directory(Directory.SHARED_SCRATCH, path=scratch_path)\
    #    .add_file_servers(FileServer("gsiftp://smarty.isi.edu/lustre", Operation.ALL))
    #condor.add_directories(condor_shared_scratch_dir)

    sc.add_sites(
        local,
        condor
    )
    
    if add_staging_site:
        # create a "staging_site" site
        staging_site = Site("staging_site", arch=Arch.X86_64, os_type=OS.LINUX)

        # create and add a shared scratch directory to the site "staging_site"
        staging_site_shared_scratch_dir = Directory(Directory.SHARED_SCRATCH, path="/data")\
            .add_file_servers(
                FileServer("scp://obelix.isi.edu/data", Operation.PUT),
                FileServer("http://obelix.isi.edu/data", Operation.GET)
            )
        staging_site.add_directories(staging_site_shared_scratch_dir)

        # add all the sites to the site catalog object
        sc.add_sites(
            staging_site
        )


    # write the site catalog to the default path "./sites.yml"
    sc.write()


if __name__ == '__main__':
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("-t", "--top_dir", type=str, required=True,
        help="The top directory.")
    ap.add_argument("-i", "--dag_file_path", type=str, required=True,
        help="The path to the dag file.")
    ap.add_argument("-o", "--output_path", type=str, required=False,
        help="The path to the sites.yml file. Default is ./sites.yml.")
    args = ap.parse_args()
    create_site_catalog(args.top_dir, dag_file_path=args.dag_file_path)
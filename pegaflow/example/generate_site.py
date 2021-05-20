#!/usr/bin/env python3

from Pegasus.api import Arch, Directory, FileServer, Grid, Operation, OS, Scheduler, Site, SiteCatalog, SupportedJobs

# create a SiteCatalog object
sc = SiteCatalog()

# create a "local" site
local = Site("local", arch=Arch.X86_64, os_type=OS.LINUX)

# create and add a shared scratch and local storage directories to the site "local"
local_shared_scratch_dir = Directory(Directory.SHARED_SCRATCH, path="/tmp/workflows/scratch")\
    .add_file_servers(FileServer("file:///tmp/workflows/scratch", Operation.ALL))

local_local_storage_dir = Directory(Directory.LOCAL_STORAGE, path="/tmp/workflows/outputs")\
    .add_file_servers(FileServer("file:///tmp/workflows/outputs", Operation.ALL))

local.add_directories(local_shared_scratch_dir, local_local_storage_dir)

# create a "condor" site
condor = Site("condor", arch=Arch.X86_64, os_type=OS.LINUX)

# create and add job managers to the site "condor"
condor.add_grids(
    Grid(Grid.GT5, contact="smarty.isi.edu/jobmanager-pbs", scheduler_type=Scheduler.PBS, 
        job_type=SupportedJobs.AUXILLARY),
    Grid(Grid.GT5, contact="smarty.isi.edu/jobmanager-pbs", scheduler_type=Scheduler.PBS,
        job_type=SupportedJobs.COMPUTE)
)

# create and add a shared scratch directory to the site "condor"
condor_shared_scratch_dir = Directory(Directory.SHARED_SCRATCH, path="/lustre")\
    .add_file_servers(FileServer("gsiftp://smarty.isi.edu/lustre", Operation.ALL))
condor.add_directories(condor_shared_scratch_dir)

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
    local,
    condor,
    staging_site
)

# write the site catalog to the default path "./sites.yml"
sc.write()
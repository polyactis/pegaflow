#!/usr/bin/env python3
"""
a Pegasus 5.0 direct-run example, copied from Pegasus official repo and modified slightly. It does NOT use pegaflow.
"""
import logging

from pathlib import Path

from pegaflow.api import *

logging.basicConfig(level=logging.DEBUG)

# --- Replicas -----------------------------------------------------------------
# create the input file for the whole workflow
with open("f.a", "w") as f:
    f.write("This is sample input to KEG")

fa = File("f.a").add_metadata(creator="ryan")
rc = ReplicaCatalog().add_replica("local", fa, Path(".").resolve() / "f.a")

# --- Transformations ----------------------------------------------------------
preprocess = Transformation(
                "preprocess",
                site="condorpool",
                pfn="/usr/bin/pegasus-keg",
                is_stageable=False,
                arch=Arch.X86_64,
                os_type=OS.LINUX
            )

findrange = Transformation(
                "findrange",
                site="condorpool",
                pfn="/usr/bin/pegasus-keg",
                is_stageable=False,
                arch=Arch.X86_64,
                os_type=OS.LINUX
            )

analyze = Transformation(
                "analyze",
                site="condorpool",
                pfn="/usr/bin/pegasus-keg",
                is_stageable=False,
                arch=Arch.X86_64,
                os_type=OS.LINUX
            )

tc = TransformationCatalog().add_transformations(preprocess, findrange, analyze)

# --- Workflow -----------------------------------------------------------------
'''
                        [f.b1] - (findrange) - [f.c1]
                        /                             \
[f.a] - (preprocess)                               (analyze) - [f.d]
                        \                             /
                        [f.b2] - (findrange) - [f.c2]

'''
wf = Workflow("diamond")

fb1 = File("f.b1")
fb2 = File("f.b2")
job_preprocess = Job(preprocess)\
                        .add_args("-a", "preprocess", "-T", "3", "-i", fa, "-o", fb1, fb2)\
                        .add_inputs(fa)\
                        .add_outputs(fb1, fb2)

fc1 = File("f.c1")
job_findrange_1 = Job(findrange)\
                        .add_args("-a", "findrange", "-T", "3", "-i", fb1, "-o", fc1)\
                        .add_inputs(fb1)\
                        .add_outputs(fc1)

fc2 = File("f.c2")
job_findrange_2 = Job(findrange)\
                        .add_args("-a", "findrange", "-T", "3", "-i", fb2, "-o", fc2)\
                        .add_inputs(fb2)\
                        .add_outputs(fc2)

fd = File("f.d")
job_analyze = Job(analyze)\
                .add_args("-a", "analyze", "-T", "3", "-i", fc1, fc2, "-o", fd)\
                .add_inputs(fc1, fc2)\
                .add_outputs(fd)

wf.add_jobs(job_preprocess, job_findrange_1, job_findrange_2, job_analyze)
wf.add_replica_catalog(rc)
wf.add_transformation_catalog(tc)

try:
    wf.plan(submit=True)\
            .wait()\
            .analyze()\
            .statistics()
except PegasusClientError as e:
    print(e)
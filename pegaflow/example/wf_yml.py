#! /usr/bin/env python3
"""
A Pegasus 5.0 diamond workflow example that outputs the workflow in a yml file.
Copied from Pegasus official repo and modified slightly. It does NOT use pegaflow.
"""
import logging

from pathlib import Path

from pegaflow.api import *

logging.basicConfig(level=logging.DEBUG)

# --- Raw input file -----------------------------------------------------------------

fa = File("f.a").add_metadata(creator="ryan")

# --- Workflow -----------------------------------------------------------------
'''
                        [f.b1] - (findrange) - [f.c1]
                        /                             \
[f.a] - (preprocess)                               (analyze) - [f.d]
                        \                             /
                        [f.b2] - (findrange) - [f.c2]

'''
wf = Workflow("diamond")

wf.add_shell_hook(EventType.START, "/pegasus/libexec/notification/email -t notify@example.com")
wf.add_shell_hook(EventType.END, "/pegasus/libexec/notification/email -t notify@example.com")

fb1 = File("f.b1")
fb2 = File("f.b2")
job_preprocess = Job("preprocess")\
    .add_args("-a", "preprocess", "-T", "3", "-i", fa, "-o", fb1, fb2)\
    .add_inputs(fa)\
    .add_outputs(fb1, fb2)\
    .add_metadata(time=60)\
    .add_shell_hook(EventType.START, "/pegasus/libexec/notification/email -t notify@example.com")\
    .add_shell_hook(EventType.END, "/pegasus/libexec/notification/email -t notify@example.com")


fc1 = File("f.c1")
job_findrange_1 = Job("findrange")\
    .add_args("-a", "findrange", "-T", "3", "-i", fb1, "-o", fc1)\
    .add_inputs(fb1)\
    .add_outputs(fc1)\
    .add_metadata(time=60)\
    .add_shell_hook(EventType.START, "/pegasus/libexec/notification/email -t notify@example.com")\
    .add_shell_hook(EventType.END, "/pegasus/libexec/notification/email -t notify@example.com")

fc2 = File("f.c2")
job_findrange_2 = Job("findrange")\
    .add_args("-a", "findrange", "-T", "3", "-i", fb2, "-o", fc2)\
    .add_inputs(fb2)\
    .add_outputs(fc2)\
    .add_metadata(time=60)\
    .add_shell_hook(EventType.START, "/pegasus/libexec/notification/email -t notify@example.com")\
    .add_shell_hook(EventType.END, "/pegasus/libexec/notification/email -t notify@example.com")

fd = File("f.d").add_metadata(final_output="true")
job_analyze = Job("analyze")\
    .add_args("-a", "analyze", "-T", "3", "-i", fc1, fc2, "-o", fd)\
    .add_inputs(fc1, fc2)\
    .add_outputs(fd)\
    .add_metadata(time=60)\
    .add_shell_hook(EventType.START, "/pegasus/libexec/notification/email -t notify@example.com")\
    .add_shell_hook(EventType.END, "/pegasus/libexec/notification/email -t notify@example.com")

wf.add_jobs(job_preprocess, job_findrange_1, job_findrange_2, job_analyze)
wf.write()
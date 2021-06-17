- [1. Pegasus Workflow Management System Python3 API](#1-pegasus-workflow-management-system-python3-api)
- [2. Prerequisites](#2-prerequisites)
- [3. Installation](#3-installation)
- [4. Examples](#4-examples)

# 1. Pegasus Workflow Management System Python3 API

Pegaflow, https://github.com/polyactis/pegaflow, is an easy-to-use package of the Python3 APIs for Pegasus WMS (http://pegasus.isi.edu/). It is compatible with Pegasus 5.0.0. Pegasus allows a developer to connect dependent computing jobs into a DAG (Directed Acyclic Graph) and run jobs according to the dependency.

[Workflow.py](pegaflow/Workflow.py) is the key difference from the official Pegasus Python APIs. Inheriting [Workflow.py](pegaflow/Workflow.py), users can write Pegasus workflows in an Object-Oriented way. It significantly reduces the amount of coding in writing a Pegasus workflow.

Pegasus jobs do NOT support UNIX pipes while many UNIX programs can only output to stdout. A shell wrapper, [pegaflow/tools/pipe2File.sh](pegaflow/tools/pipe2File.sh), is offered to redirect the output (stdout) of a program to a file. [pegaflow/tools/](pegaflow/tools/) contains a few other useful shell scripts.

- **Workflow.py**
- The monitoring API
- The Stampede database API
- The Pegasus statistics API
- The Pegasus plots API
- Miscellaneous Pegasus utilities
- The Pegasus service, including the ensemble manager and dashboard

Part of this package's source code is copied from https://github.com/pegasus-isi/pegasus, version 5.0.0,

# 2. Prerequisites

Pegasus and HTCondor (Condor) are only required on computers on which you intend to submit and run workflows.

On computers where only DAG yml files are outputted, no need to install Pegasus and Condor.

- Pegasus https://github.com/pegasus-isi/pegasus
- HTCondor https://research.cs.wisc.edu/htcondor/, the underlying job scheduler.
- Linux command bc and gzip are needed if [pegaflow/tools/pipe2File.sh](pegaflow/tools/pipe2File.sh) is to be used.

# 3. Installation

Install pegaflow:

```python
pip3 install --upgrade pegaflow
```

# 4. Examples

Check [pegaflow/example/](pegaflow/example/) for examples.

- [pegaflow/example/WordCountFiles.py](pegaflow/example/WordCountFiles.py) is an example that inherits [Workflow.py](pegaflow/Workflow.py). Users should be familiar with Object-Oriented programming.
- [pegaflow/example/WCFiles_Function.py](pegaflow/example/WCFiles_Function.py) is a procedural-programming example.

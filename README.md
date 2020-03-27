
# Pegasus Workflow Management System Python3 API

This package contains the Python3 APIs for Pegasus WMS.

This package's source code came directly from https://github.com/ahnitz/pegasus-wms-python3, which is based on http://pegasus.isi.edu/'s python APIs, version 4.9.1.

Beside the Python3 support, this package contains a helper class, Workflow.py, for users to inherit. It simplifies the Pegasus workflow writing. Check code in examples/ to start.

* The DAX API (Versions 3) and the helper class Workflow.py
* The monitoring API
* The Stampede database API
* The Pegasus statistics API
* The Pegasus plots API
* Miscellaneous Pegasus utilities
* The Pegasus service, including the ensemble manager and dashboard

# Installation


```python
pip3 install pegapy3
```

If the user intends to use functions beyond the DAX APIs, he/she should install the following Python packages as well.

* "Werkzeug==0.14.1",
* "Flask==0.12.4",
* "Jinja2==2.8.1",
* "SQLAlchemy",
* "Flask-Cache==0.13.1",
* "requests==2.18.4",
* "MarkupSafe==1.0",
* "boto==2.48.0",
* "pam==0.1.4",
* "plex==2.0.0dev",
* "future"
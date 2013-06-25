## This file is part of Invenio.
## Copyright (C) 2012, 2013 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""
BibWorkflow API - functions to run workflows
"""

import os
from pprint import pformat
from invenio.config import CFG_BIBWORKFLOW_WORKER
from invenio.config import CFG_PYLIBDIR, CFG_LOGDIR
from invenio.pluginutils import PluginContainer


USE_TASK_QUEUE = False

if CFG_BIBWORKFLOW_WORKER:
    worker_plugin_path = os.path.join(CFG_PYLIBDIR, 'invenio', 'bibworkflow',
                                      'workers', '*.py')
    workers = PluginContainer(worker_plugin_path, exception_registration=False)
    try:
        WORKER = workers.get_enabled_plugins()[CFG_BIBWORKFLOW_WORKER]
        USE_TASK_QUEUE = True
    except KeyError:
        print 'Could not load Worker'
        ## Let's report about broken plugins
        open(os.path.join(CFG_LOGDIR, 'broken-bibworkflow-workers.log'), 'w').\
            write(pformat(workers.get_broken_plugins()))


def run(wname, data, task_queue=USE_TASK_QUEUE, external_save=None):
    """
    Runs workflow by given name for specified data. Name is uniqe and is the
    same as name of a file containing workflow. Data is a list of objects f.eg
    dict, BibWorkflowObjects, WfeObjects.
    """
    from invenio.bibworkflow_worker_engine import runit

    if task_queue:
        return WORKER().run(wname, data, external_save=external_save)
    else:
        return runit(wname, data, external_save=external_save)


def run_by_wid(wid, data=None, start_point="beginning",
               task_queue=USE_TASK_QUEUE, external_save=None):
    """
    Runs workflow by given workflow id (wid). It can start from beginning,
    prev, next and continue. Data variable can be list of object ids or list of
    objects.
    """
    from invenio.bibworkflow_worker_engine import restartit

    if task_queue:
        return WORKER().restart(wid, data, start_point, external_save=external_save)
    else:
        return restartit(wid, external_save=external_save)


def continue_oid(oid, start_point="beginning", task_queue=USE_TASK_QUEUE, external_save=None):
    """
    Continue workflow asociated with object given by object id (oid). It can start
    from beginning, prev, next and continue.
    """
    from invenio.bibworkflow_worker_engine import continueit

    if task_queue:
        return WORKER().continueit(oid, start_point,
                                   external_save=external_save)
    else:
        return continueit(oid, start_point, external_save=external_save)

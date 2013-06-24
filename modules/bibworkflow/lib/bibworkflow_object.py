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

import os
import tempfile

from invenio.bibworkflow_model import WfeObject
from datetime import datetime
from invenio.sqlalchemyutils import db
from invenio.bibworkflow_utils import dictproperty
from invenio.bibworkflow_config import add_log, \
    CFG_BIBWORKFLOW_OBJECTS_LOGDIR, CFG_OBJECT_VERSION
from invenio.config import CFG_TMPSHAREDDIR
from invenio.errorlib import register_exception


class BibWorkflowObject(object):

    def __init__(self, data=None, workflow_id=None,
                 version=CFG_OBJECT_VERSION.INITIAL, parent_id=None,
                 id=None, extra_data=None, task_counter=[0],
                 extra_object_class=None, data_type=None, uri=None):
        self.extra_object_class = extra_object_class
        self.status = None
        if isinstance(data, WfeObject):
            self.db_obj = data
        else:
            if wfobject_id is not None:
                self.db_obj = WfeObject.query.filter(WfeObject.id == wfobject_id).first()
            else:
                self.db_obj = WfeObject(data=data, workflow_id=workflow_id,
                                        version=version, parent_id=parent_id,
                                        data_type=data_type, 
                                        uri=uri)
                self._create_db_obj()
                self.extra_data['task_counter'] = str(task_counter)
        self.add_log()

    def add_log(self):
        self.log = add_log(os.path.join(CFG_BIBWORKFLOW_OBJECTS_LOGDIR,
                           'object_%s_%s.log' % (self.db_obj.id,
                                                 self.db_obj.workflow_id)),
                           'object.%s' % self.db_obj.id)
        
    def get_data(self, key):
        if key not in self.db_obj.data.keys():
            raise KeyError
        return self.db_obj.data[key]

    def set_data(self, key, value):
        self.db_obj.data[key] = value

    data = dictproperty(fget=get_data, fset=set_data, doc="Sets up property")
    del get_data, set_data

    def get_extra_data(self, key):
        if key not in self.db_obj.extra_data.keys():
            raise KeyError
        return self.db_obj.extra_data[key]

    def set_extra_data(self, key, value):
        self.db_obj.extra_data[key] = value

    extra_data = dictproperty(fget=get_extra_data, fset=set_extra_data,
                              doc="Sets up property")

    del get_extra_data, set_extra_data

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['log']
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        self.add_log()

    def _update_db(self):
        db.session.commit()
        if self.extra_object_class:
            extra_obj = self.extra_object_class(self.db_obj)
            extra_obj.update()

    def _create_db_obj(self):
        db.session.add(self.db_obj)
        db.session.commit()
        if self.extra_object_class:
            extra_obj = self.extra_object_class(self.db_obj)
            extra_obj.save()

    def _create_version_obj(self, workflow_id, version, parent_id):
        obj = WfeObject(data=self.db_obj.data,
                        workflow_id=workflow_id,
                        version=version,
                        parent_id=parent_id,
                        extra_data=self.db_obj.extra_data,
                        status=self.status,
                        data_type=self.db_obj.data_type)
        db.session.add(obj)
        db.session.commit()
        # Run extra save method
        if self.extra_object_class:
            extra_obj = self.extra_object_class(obj)
            extra_obj.save()

        return obj.id

    def save(self, version=None, task_counter=[0], workflow_id=None):
        """
        """
        self.db_obj.extra_data["task_counter"] = task_counter
        self.db_obj.modified = datetime.now()

        if not workflow_id:
            workflow_id = self.db_obj.workflow_id

        if version == CFG_OBJECT_VERSION.HALTED:
            # Processing was interrupted or error happened,
            # we save the current state ("error" version)
            if self.db_obj.parent_id is not None:
                # We are a child, so we update ourselves.
                ### May need to update parent object to change latest_object
                self._update_db()
                return int(self.db_obj.id)
            else:
                # First time this object has an error/interrupt.
                # Add new child from this object. (version error)
                self.add_metadata('latest_object', int(self._create_version_obj(workflow_id,
                                                    CFG_OBJECT_VERSION.HALTED,
                                                    int(self.db_obj.id))))
                self._update_db()

        elif version == CFG_OBJECT_VERSION.FINAL:
            # This means the object was successfully run
            # through the workflow. (finished version)
            # We update or insert the final object
            if self.db_obj.version == CFG_OBJECT_VERSION.FINAL:
                self._update_db()
                return int(self.db_obj.id)
            else:
                if self.db_obj.parent_id is not None:
                    parent_id = self.db_obj.parent_id
                else:
                    parent_id = self.db_obj.id
                self.add_metadata('latest_object', int(self._create_version_obj(workflow_id,
                                                    CFG_OBJECT_VERSION.FINAL,
                                                    parent_id)))
                self._update_db()
        else:
            # version == 0
            # First save of the object (original version)
            self._create_db_obj()
            self.get_log().info('Saved in db')

    def set_log(self, log):
        self.log = log

    def get_log(self):
        return self.log

    def __repr__(self):
        return "<%s(id: %s, data: %s, workflow_id: %s, version: %s, parent_id: %s, extra_data: %s)>" % (
            "BibWorkflowObject",
            str(self.db_obj.id),
            str(self.db_obj.data),
            str(self.db_obj.workflow_id),
            str(self.db_obj.version),
            str(self.db_obj.parent_id),
            str(self.db_obj.extra_data)
        )

    def add_task_result(self, task_name, result):
        self.extra_data["tasks_results"][task_name] = result

    def add_metadata(self, key, value):
        self.extra_data[key] = value

    def changeStatus(self, message):
        self.status = message

    def save_to_file(self, directory=CFG_TMPSHAREDDIR,
                     prefix="bibworkflow_object_data_", suffix=".obj"):
        """
        Saves the contents of self.data['data'] to file.

        Returns path to saved file.

        Warning: Currently assumes non-binary content.
        """
        if "data" in self.db_obj.data:
            tmp_fd, filename = tempfile.mkstemp(dir=directory,
                                                prefix=prefix,
                                                suffix=suffix)
            os.write(tmp_fd, self.db_obj.data['data'])
            os.close(tmp_fd)
        return filename
        
    @staticmethod    
    def determineDataType(data):
        # If data is a dictionary and contains type key,
        # we can directly derive the data_type
        if isinstance(data, dict):
            if data.has_key('type'):
                data_type = data['type']
            else:
                data_type = 'dict'
        else:
            from magic import Magic
            mime_checker = Magic(mime=True)
                
            # If data is not a dictionary, we try to guess MIME type
            # by using magic library
            try:
                data_type = mime_checker.from_buffer(data)
            except:
                register_exception(stream="warning", prefix="BibWorkflowObject.determineDataType: Impossible to resolve data type.")
                data_type = ""
        return data_type
        

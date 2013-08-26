# -*- coding: utf-8 -*-
##
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
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.


from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound
from invenio.bibworkflow_engine import BibWorkflowEngine
from invenio.bibworkflow_model import Workflow, BibWorkflowObject
from invenio.bibworkflow_api import start, \
    resume_objects_in_workflow
from invenio.bibworkflow_config import CFG_WORKFLOW_STATUS
from invenio.bibfield_jsonreader import JsonReader


class DepositionWorkflow(object):
    """ class for running webdeposit workflows using the BibWorkflow engine

        The user_id and workflow must always be defined
        If the workflow has been initialized before,
        the appropriate uuid must be passed as a parameter.
        Otherwise a new workflow will be created

        The workflow functions must have the following structure:

        def function_name(arg1, arg2):
            def fun_name2(obj, eng):
                # do stuff
            return fun_name2
    """

    def __init__(self, engine=None, uuid=None,
                 deposition_type=None, user_id=None):
        """
        param engine: an instance of bibworkflow engine or None.
        type engine: class BibWorkflowEngine

        param uuid: an identifier to load a previous workflow. If not defined it
        will be initialised from the engine or a new workflow will be created.
        type uuid: UUID or str

        param deposition_type: the name of the deposition/workflow. Necessary to
        load the workflow definition.
        type deposition_type: str

        param user_id: the user identifier that owns the workflow.
        type user_id: str

        """

        self.obj = {}
        self.set_user_id(user_id)
        self.set_deposition_type(deposition_type)
        self.set_uuid(uuid)
        self.set_engine(engine)
        self.current_step = 0
        self.steps_num = len(self.workflow)
        self.obj['steps_num'] = self.steps_num

    def set_uuid(self, uuid=None):
        """ Sets the uuid.
        If a uuid is defined, a previously started workflow is being resumed.
        If it's None, a new workflow is being created and the uuid will be
        generated from the bibworkflow engine.
        """

        self.uuid = uuid

    def get_uuid(self):
        return self.uuid

    def set_engine(self, engine=None):
        """ Initializes the BibWorkflow engine """
        if engine is None:
            engine = BibWorkflowEngine(name=self.deposition_type,
                                       uuid=self.get_uuid(),
                                       id_user=self.get_user_id(),
                                       module_name="webdeposit")
        self.eng = engine
        self.set_uuid(self.eng.uuid)
        self.eng.save()

    def set_deposition_type(self, deposition_type=None):
        if deposition_type is not None:
            self.obj['deposition_type'] = deposition_type

    def get_deposition_type(self):
        return self.obj['deposition_type']

    deposition_type = property(get_deposition_type, set_deposition_type)

    @property
    def workflow(self):
        return self.eng.workflow_definition.workflow

    def set_user_id(self, user_id=None):
        if user_id is not None:
            self.user_id = user_id
        else:
            from invenio.webuser_flask import current_user
            self.user_id = current_user.get_id()

        self.obj['user_id'] = self.user_id

    def get_user_id(self):
        return self.user_id

    def get_status(self):
        """ Returns the status of the workflow
            (check CFG_WORKFLOW_STATUS from bibworkflow_engine)
        """
        status = \
            Workflow.query. \
            filter(Workflow.uuid == self.get_uuid()).\
            one().status

        return status

    def get_data(self, key):
        try:
            return Workflow.get_extra_data(user_id=self.user_id, uuid=self.uuid,
                                           key=key)
        except (NoResultFound, KeyError):
            pass

        bib_obj = BibWorkflowObject.query.\
            filter(BibWorkflowObject.id_workflow == self.uuid,
                   BibWorkflowObject.id_parent != None).\
            order_by(desc(BibWorkflowObject.modified)).first()
        data = bib_obj.get_data()
        if key in data:
            return data[key]

        return None

    def has_completed(self):
        """Checks if current engine has completed."""
        return self.eng.has_completed()

    def get_output(self, form=None, form_validation=False):
        """ Returns a representation of the current state of the workflow
            (a dict with the variables to fill the jinja template)
        """
        from invenio.webdeposit_utils import get_form, \
            draft_field_get_all

        user_id = self.user_id
        uuid = self.get_uuid()

        if form is None:
            form = get_form(
                user_id, uuid, validate_draft=not form_validation
            )

        drafts = draft_field_get_all(user_id, self.deposition_type)

        if form_validation:
            form.validate()

        # Get the template for this form
        template = form.get_template()

        return dict(template_name_or_list=template,
                    workflow=self,
                    deposition_type=self.deposition_type,
                    form=form,
                    drafts=drafts,
                    uuid=uuid)

    def run(self):
        """ Runs or resumes the workflow """

        current_workflow = self.get_workflow_from_db()
        if current_workflow and \
           current_workflow.status != CFG_WORKFLOW_STATUS.NEW:
            # Resume workflow if there are object to resume
            for workflow in resume_objects_in_workflow(
                id_workflow=self.uuid,
                start_point="restart_task"
            ):
                # There should only be one object
                self.eng = workflow
                break
        else:
            # Start workflow from beginning
            self.eng = start(workflow_name=self.deposition_type,
                             data=[self.obj],
                             uuid=self.get_uuid())
        self.bib_obj = self.eng.getObjects().next()[1]

    def get_workflow_from_db(self):
        return Workflow.get(Workflow.uuid == self.get_uuid()).first()

    def cook_json(self):
        user_id = self.obj['user_id']
        uuid = self.get_uuid()

        from invenio.webdeposit_utils import get_form

        json_reader = JsonReader()
        for step in range(self.steps_num):
            try:
                form = get_form(user_id, uuid, step)
                json_reader = form.cook_json(json_reader)
            except:
                # some steps don't have any form ...
                pass

        return json_reader

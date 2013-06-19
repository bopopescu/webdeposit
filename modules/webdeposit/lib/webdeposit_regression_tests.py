# -*- coding: utf-8 -*-
##
## This file is part of Invenio.
## Copyright (C) 2013 CERN.
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

from invenio.testutils import make_test_suite, run_test_suite, InvenioTestCase


class TestWebDepositUtils(InvenioTestCase):

    def clear_tables(self):
        from invenio.bibworkflow_model import Workflow, WfeObject
        from invenio.webdeposit_model import WebDepositDraft
        from invenio.sqlalchemyutils import db

        Workflow.query.delete()
        WfeObject.query.delete()
        WebDepositDraft.query.delete()
        db.session.commit()

    def setUp(self):
        from invenio.sqlalchemyutils import db

        self.clear_tables()
        # db.session.execute("TRUNCATE schTASK")
        # db.session.commit()
        super(TestWebDepositUtils, self).setUp()

    def tearDown(self):
        self.clear_tables()
        super(TestWebDepositUtils, self).tearDown()

    def test_workflow_creation(self):
        from invenio.webdeposit_load_deposition_types import \
            deposition_metadata
        from invenio.bibworkflow_model import Workflow
        from invenio.webdeposit_workflow import DepositionWorkflow
        from invenio.webdeposit_utils import get_latest_or_new_workflow, \
            get_workflow, delete_workflow
        from invenio.sqlalchemyutils import db
        from invenio.webuser_flask import login_user

        login_user(1)

        number_of_dep_types = len(deposition_metadata)
        # Test for every deposition type
        for deposition_type in deposition_metadata.keys():
            # New workflow is created
            workflow = get_latest_or_new_workflow(deposition_type, user_id=1)
            assert workflow is not None

            # The just created workflow is retrieved as latest
            workflow2 = get_latest_or_new_workflow(deposition_type, user_id=1)
            assert workflow2 is not None
            assert str(workflow2.uuid) == str(workflow.uuid)

            # and also retrieved with its uuid
            workflow = get_workflow(deposition_type, workflow.uuid)
            assert workflow is not None

        # Test get_workflow function with random arguments
        workflow = get_workflow('deposition_type_that_doesnt_exist',
                                'some_uuid')
        assert workflow is None

        deposition_type = deposition_metadata.keys()[-1]
        workflow = get_workflow(deposition_type,
                                'some_uuid_that_doesnt_exist')
        assert workflow is None

        # Create workflow without using webdeposit_utils
        wf = deposition_metadata[deposition_type]["workflow"]
        workflow = DepositionWorkflow(deposition_type=deposition_type,
                                      workflow=wf, user_id=1)

        # Test that the retrieved workflow is the same and not None
        workflow2 = get_workflow(deposition_type, workflow.get_uuid())
        assert workflow2 is not None
        assert workflow2.get_uuid() == workflow.get_uuid()

        # Check the number of created workflows
        workflows = db.session.query(Workflow).all()
        assert len(workflows) == number_of_dep_types + 1

        uuid = workflow.get_uuid()
        delete_workflow(1, uuid)
        workflow = get_workflow(deposition_type, uuid)
        assert workflow is None

    def test_form_functions(self):
        from invenio.webdeposit_load_deposition_types import \
            deposition_metadata
        from invenio.webdeposit_load_forms import forms
        from invenio.webdeposit_model import WebDepositDraft
        from invenio.webdeposit_workflow import DepositionWorkflow
        from invenio.webdeposit_utils import get_current_form, get_form, \
            get_form_status, CFG_DRAFT_STATUS
        from invenio.sqlalchemyutils import db
        from invenio.webdeposit_workflow_utils import render_form, \
            wait_for_submission
        from invenio.cache import cache

        for metadata in deposition_metadata.values():
            for wf_function in metadata['workflow']:
                if 'render_form' == wf_function.func_name:
                    break

        from invenio.webuser_flask import login_user
        login_user(1)

        wf = [render_form(forms.values()[0]),
              wait_for_submission()]
        deposition_workflow = DepositionWorkflow(deposition_type='TestWorkflow',
                                                 workflow=wf, user_id=1)

        uuid = deposition_workflow.get_uuid()
        cache.delete_many("1:current_deposition_type", "1:current_uuid")
        cache.add("1:current_deposition_type", 'TestWorkflow')
        cache.add("1:current_uuid", uuid)

        # Run the workflow to insert a form to the db
        deposition_workflow.run()

        # There is only one form in the db
        drafts = db.session.query(WebDepositDraft)
        assert len(drafts.all()) == 1

        # Test that guest user doesn't have access to the form
        uuid, form = get_current_form(0, deposition_type='TestWorkflow',
                                      uuid=uuid)
        assert form is None

        # Test that the current form has the right type
        uuid, form = get_current_form(1, deposition_type='TestWorkflow',
                                      uuid=deposition_workflow.get_uuid())
        assert isinstance(form, forms.values()[0])
        assert str(uuid) == str(deposition_workflow.get_uuid())

        # Test that form is returned with get_form function
        form = get_form(1, deposition_workflow.get_uuid())
        assert form is not None

        form = get_form(1, deposition_workflow.get_uuid(), step=0)
        assert form is not None

        # Second step doesn't have a form
        form = get_form(1, deposition_workflow.get_uuid(), step=1)
        assert form is None

        form_status = get_form_status(1, deposition_workflow.get_uuid())
        assert form_status == CFG_DRAFT_STATUS['unfinished']

        form_status = get_form_status(1, deposition_workflow.get_uuid(),
                                      step=2)
        assert form_status is None

        db.session.query(WebDepositDraft).\
            update({'status': CFG_DRAFT_STATUS['finished']})

        form_status = get_form_status(1, deposition_workflow.get_uuid())
        assert form_status == CFG_DRAFT_STATUS['finished']

    def test_field_functions(self):
        from datetime import datetime
        from invenio.sqlalchemyutils import db
        from invenio.webdeposit_workflow import DepositionWorkflow
        from invenio.webdeposit_model import WebDepositDraft
        from invenio.webdeposit_workflow_utils import render_form
        from invenio.webdeposit_utils import draft_field_get
        from invenio.webdeposit_deposition_forms.article_form import ArticleForm
        from invenio.cache import cache

        wf = [render_form(ArticleForm)]
        user_id = 1

        workflow = DepositionWorkflow(workflow=wf,
                                      deposition_type='TestWorkflow',
                                      user_id=user_id)

        cache.delete_many("1:current_deposition_type", "1:current_uuid")
        cache.add("1:current_deposition_type", 'TestWorkflow')
        cache.add("1:current_uuid", workflow.get_uuid())

        workflow.run()  # Insert a form
        uuid = workflow.get_uuid()

        # Test for a field that's not there
        value = draft_field_get(user_id, uuid, 'field_that_doesnt_exist')
        assert value is None

        # Test for a field that hasn't been inserted in db yet
        value = draft_field_get(user_id, uuid, 'publisher')
        assert value is None

        values = {'publisher': 'Test Publishers Association'}

        db.session.query(WebDepositDraft).\
            filter(WebDepositDraft.uuid == uuid,
                   WebDepositDraft.step == 0).\
            update({"form_values": values,
                    "timestamp": datetime.now()})

    def test_record_creation(self):
        import os
        from wtforms import TextField, TextAreaField
        from sqlalchemy import func
        from invenio.sqlalchemyutils import db
        from invenio.webdeposit_load_deposition_types import \
            deposition_metadata
        from invenio.bibworkflow_config import CFG_WORKFLOW_STATUS
        from invenio.webdeposit_model import WebDepositDraft
        from invenio.bibsched_model import SchTASK
        from invenio.webdeposit_utils import get_current_form, \
            create_workflow, set_form_status, CFG_DRAFT_STATUS
        from invenio.webuser_flask import login_user
        from invenio.webdeposit_workflow_utils import \
            create_record_from_marc
        from invenio.search_engine import record_exists
        from invenio.cache import cache
        from invenio.config import CFG_PREFIX
        from invenio.bibfield import get_record

        login_user(1)
        for deposition_type in deposition_metadata.keys():

            deposition = create_workflow(deposition_type, 1)
            assert deposition is not None

            # Check if deposition creates a record
            create_rec = create_record_from_marc()
            function_exists = False
            for workflow_function in deposition.workflow:
                if create_rec.func_code == workflow_function .func_code:
                    function_exists = True
            if not function_exists:
                # if a record is not created,
                #continue with the next deposition
                continue

            uuid = deposition.get_uuid()

            cache.delete_many("1:current_deposition_type", "1:current_uuid")
            cache.add("1:current_deposition_type", deposition_type)
            cache.add("1:current_uuid", uuid)

            # Run the workflow
            deposition.run()
            # Create form's json based on the field name
            form = get_current_form(1, deposition_type, uuid)[1]
            webdeposit_json = {}
            value_inserted = False
            for field in form:
                if isinstance(field, TextField) or \
                   isinstance(field, TextAreaField):
                    webdeposit_json[field.name] = "test value"
                    value_inserted = True
            webdeposit_draft = \
                WebDepositDraft(uuid=uuid,
                                form_type=form.__class__.__name__,
                                form_values=webdeposit_json,
                                step=0,  # dummy step
                                status=CFG_DRAFT_STATUS['finished'],
                                timestamp=func.current_timestamp())
            db.session.add(webdeposit_draft)
            db.session.commit()

            workflow_status = CFG_WORKFLOW_STATUS.RUNNING
            while workflow_status != CFG_WORKFLOW_STATUS.FINISHED:
                # Continue workflow
                deposition.run()
                set_form_status(1, uuid, CFG_WORKFLOW_STATUS.FINISHED)
                workflow_status = deposition.get_status()

            # Workflow is finished. Test if record is created
            recid = deposition.get_data('recid')
            assert recid is not None
            # Test that record id exists
            assert record_exists(recid) == 1

            # Test that the task exists
            task_id = deposition.get_data('task_id')
            assert task_id is not None

            bibtask = SchTASK.query.filter(SchTASK.id == task_id).first()
            assert bibtask is not None

            # Run bibupload, bibindex, webcoll manually
            cmd = "%s/bin/bibupload %s" % (CFG_PREFIX, task_id)
            assert not os.system(cmd)

            if value_inserted:
                # Test if record contains the inserted value
                rec = get_record(recid)
                assert "test value" in rec.legacy_export_as_marc()


TEST_SUITE = make_test_suite(TestWebDepositUtils)

if __name__ == "__main__":
    run_test_suite(TEST_SUITE)

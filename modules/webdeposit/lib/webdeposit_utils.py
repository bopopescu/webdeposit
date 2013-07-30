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

""" WebDeposit Utils
Set of utilities to be used by blueprint, forms and fields.

It contains functions to start a workflow, retrieve it and edit its data.
The basic entities are the forms and fields which are stored in json.
(forms are referred as drafts before they haven't been submitted yet.)

The file field is handled separately and all the files are attached in the json
as a list in the 'files' key.

Some functions contain the keyword `preingest`. This refers to the json that is
stored in the 'pop_obj' key, which is used to store data before running the
workflow. This is being used e.g. in the wedbeposit api where the workflow is
being run without a user submitting the forms, so this json is being used to
preinsert data into the webdeposit workflow.
"""


import os
import shutil
from flask import request
from glob import iglob
from werkzeug.utils import secure_filename
from datetime import datetime
from wtforms import FormField
from sqlalchemy.orm.exc import NoResultFound
from uuid import uuid1 as new_uuid
from urllib2 import urlopen, URLError

from invenio.cache import cache
from invenio.sqlalchemyutils import db
from invenio.webdeposit_model import WebDepositDraft
from invenio.bibworkflow_model import Workflow
from invenio.bibworkflow_config import CFG_WORKFLOW_STATUS
from invenio.webdeposit_load_forms import forms
from invenio.webuser_flask import current_user
from invenio.webdeposit_load_deposition_types import deposition_metadata
from invenio.webdeposit_workflow import DepositionWorkflow
from invenio.config import CFG_WEBDEPOSIT_UPLOAD_FOLDER


CFG_DRAFT_STATUS = {
    'unfinished': 0,
    'finished': 1
}


""" Setters/Getters for bibworklflow """


def draft_getter(step=None):
    """Returns a json with the current form values.
    If step is None, the latest draft is returned."""
    def draft_getter_func(json):
        if step is None:
            return json['drafts'][max(json['drafts'])]
        else:
            try:
                return json['drafts'][step]
            except KeyError:
                pass

            try:
                return json['drafts'][unicode(step)]
            except KeyError:
                pass
            raise NoResultFound
    return draft_getter_func


def draft_setter(step=None, key=None, value=None, field_setter=False):
    """Alters a draft's specified value.
    If the field_setter is true, it uses the key value to update
    the dictionary `form_values`"""
    def draft_setter_func(json):
        if step is None:
            draft = json['drafts'][max(json['drafts'])]
        else:
            draft = json['drafts'][step]

        if field_setter:
            draft['form_values'][key] = value
        else:
            draft[key] = value

        draft['timestamp'] = str(datetime.now())
    return draft_setter_func


def add_draft(draft):
    """ Adds a form draft. """
    def setter(json):
        step = draft.pop('step')
        if not 'drafts' in json:
            json['drafts'] = {}
        if not step in json['drafts'] and \
           not unicode(step) in json['drafts']:
            json['drafts'][step] = draft
    return setter


def draft_field_list_setter(field_name, value):
    def setter(json):
        draft = json['drafts'][max(json['drafts'])]
        values = draft['form_values']
        try:
            if isinstance(values[field_name], list):
                values[field_name].append(value)
            else:
                new_values_list = [values[field_name]]
                new_values_list.append(value)
                values[field_name] = new_values_list
        except KeyError:
            values[field_name] = [value]

        draft['timestamp'] = str(datetime.now())

    return setter

""" Workflow functions  """

def get_latest_or_new_workflow(deposition_type, user_id=None):
    """ Creates new workflow or returns a new one """

    user_id = user_id or current_user.get_id()
    wf = deposition_metadata[deposition_type]["workflow"]

    # get latest draft in order to get workflow's uuid
    try:
        latest_workflow = Workflow.get_most_recent(
            Workflow.user_id == user_id,
            Workflow.name == deposition_type,
            Workflow.module_name == 'webdeposit',
            Workflow.status != CFG_WORKFLOW_STATUS.FINISHED)
    except NoResultFound:
        # We didn't find other workflows
        # Let's create a new one
        return DepositionWorkflow(deposition_type=deposition_type,
                                  workflow=wf)

    # Create a new workflow
    # based on the latest draft's uuid
    uuid = latest_workflow .uuid
    return DepositionWorkflow(deposition_type=deposition_type,
                              workflow=wf, uuid=uuid)


def get_workflow(deposition_type, uuid):
    """ Returns a workflow instance with uuid=uuid or None """
    try:
        wf = deposition_metadata[deposition_type]["workflow"]
    except KeyError:
        # deposition type not found
        return None
    # Check if uuid exists first
    try:
        Workflow.get(uuid=uuid).one()
    except NoResultFound:
        return None
    return DepositionWorkflow(uuid=uuid,
                              deposition_type=deposition_type,
                              workflow=wf)


def create_workflow(deposition_type, user_id=None):
    """ Creates a new workflow and returns it """
    try:
        wf = deposition_metadata[deposition_type]["workflow"]
    except KeyError:
        # deposition type not found
        return None

    return DepositionWorkflow(deposition_type=deposition_type,
                              workflow=wf, user_id=user_id)


def delete_workflow(user_id, uuid):
    """ Deletes all workflow related data
        (workflow and drafts)
    """

    Workflow.delete(uuid=uuid)


def get_current_form(user_id, deposition_type=None, uuid=None):
    """Returns the latest draft(wtform object) of the deposition_type
    or the form with the specific uuid.
    if it doesn't exist, creates a new one
    """

    if user_id is None:
        return None

    try:
        if uuid is not None:
            # get the draft with the max step, the latest
            try:
                webdeposit_draft = \
                    Workflow.get_extra_data(user_id=user_id,
                                            uuid=uuid,
                                            getter=draft_getter())
            except ValueError:
                # No drafts found
                raise NoResultFound
        else:
            raise NoResultFound
    except NoResultFound:
        # No Form draft was found
        return None, None

    form = forms[webdeposit_draft['form_type']]()
    draft_data = webdeposit_draft['form_values']

    for field_name in form.data.keys():
        if isinstance(form._fields[field_name], FormField) \
                and field_name in draft_data:
            subfield_names = \
                form._fields[field_name]. \
                form._fields.keys()
            #upperfield_name, subfield_name = field_name.split('-')
            for subfield_name in subfield_names:
                if subfield_name in draft_data[field_name]:
                    form._fields[field_name].\
                        form._fields[subfield_name]. \
                        process_data(draft_data[field_name][subfield_name])
        elif field_name in draft_data:
            form[field_name].process_data(draft_data[field_name])

    return uuid, form


def get_form(user_id, uuid, step=None):
    """ Returns the current state of the workflow in a form
        or a previous state (step)
    """

    #FIXME: merge with get_current_form

    try:
        webdeposit_draft = \
            Workflow.get_extra_data(user_id=user_id,
                                    uuid=uuid,
                                    getter=draft_getter(step))
    except (ValueError, NoResultFound):
        # No drafts found
        return None

    form = forms[webdeposit_draft['form_type']]()

    draft_data = webdeposit_draft['form_values']

    for field_name in form.data.keys():
        if isinstance(form._fields[field_name], FormField) \
                and field_name in draft_data:
            subfield_names = \
                form._fields[field_name].\
                form.fields.keys()
            #upperfield_name, subfield_name = field_name.split('-')
            for subfield_name in subfield_names:
                if subfield_name in draft_data[field_name]:
                    form._fields[field_name].\
                        form._fields[subfield_name].\
                        process_data(draft_data[field_name][subfield_name])
        elif field_name in draft_data:
            form[field_name].process_data(draft_data[field_name])

    if 'files' in draft_data:
        # FIXME: sql alchemy(0.8.0) returns the value from the
        #        column form_values with keys and values in unicode.
        #        This creates problem when the dict is rendered
        #        in the page to be used by javascript functions. There must
        #        be a more elegant way than decoding the dict from unicode.

        draft_data['files'] = decode_dict_from_unicode(draft_data['files'])
        for file_metadata in draft_data['files']:
            # Replace the path with the unique filename
            if isinstance(file_metadata, basestring):
                import json
                file_metadata = json.loads(file_metadata)
            filepath = file_metadata['file'].split('/')
            unique_filename = filepath[-1]
            file_metadata['unique_filename'] = unique_filename
        form.__setattr__('files', draft_data['files'])
    else:
        form.__setattr__('files', {})
    return form


def get_form_status(user_id, uuid, step=None):
    try:
        webdeposit_draft = \
            Workflow.get_extra_data(user_id=user_id,
                                    uuid=uuid,
                                    getter=draft_getter(step))
    except ValueError:
        # No drafts found
        raise NoResultFound
    except NoResultFound:
        return None

    return webdeposit_draft['status']


def set_form_status(user_id, uuid, status, step=None):
    try:
        Workflow.set_extra_data(user_id=user_id,
                                uuid=uuid,
                                setter=draft_setter(step, 'status', status))
    except ValueError:
        # No drafts found
        raise NoResultFound
    except NoResultFound:
        return None


def get_last_step(steps):
    if type(steps[-1]) is list:
        return get_last_step[-1]
    else:
        return steps[-1]


def get_current_step(uuid):
    webdep_workflow = Workflow.get(Workflow.uuid == uuid).one()
    steps = webdep_workflow.task_counter

    return get_last_step(steps)


""" Draft Functions (or instances of forms)
"""


def draft_field_get(user_id, uuid, field_name, subfield_name=None):
    """ Returns the value of a field
        or, in case of error, None
    """

    values = \
        Workflow.get_extra_data(user_id=user_id, uuid=uuid,
                                getter=draft_getter())['form_values']

    try:
        if subfield_name is not None:
            return values[field_name][subfield_name]
        return values[field_name]
    except KeyError:
        return None


def draft_field_error_check(user_id, uuid, field_name, value):
    """ Retrieves the form based on the uuid
        and returns a json string evaluating the field's value
    """

    form = get_form(user_id, uuid=uuid)

    subfield_name = None
    if '-' in field_name:  # check if its subfield
        field_name, subfield_name = field_name.split('-')

        form = form._fields[field_name].form
        field_name = subfield_name

    form._fields[field_name].process_data(value)
    return form._fields[field_name].pre_validate(form)


def draft_field_set(user_id, uuid, field_name, value):
    """ Alters the value of a field """

    Workflow.set_extra_data(user_id=user_id, uuid=uuid,
                            setter=draft_setter(key=field_name, value=value,
                                                field_setter=True))


def draft_field_list_add(user_id, uuid, field_name, value,
                         subfield=None):
    """Adds value to field
    Used for fields that contain multiple values
    e.g.1: { field_name : value1 } OR
           { field_name : [value1] }
           -->
           { field_name : [value1, value2] }
    e.g.2  { }
           -->
           { field_name : [value] }
    e.g.3  { }
           -->
           { field_name : {key : value} }
    """

    Workflow.set_extra_data(user_id=user_id, uuid=uuid,
                            setter=draft_field_list_setter(field_name, value))
    return


def preingest_form_data(user_id, form_data, uuid=None,
                        append=False, cached_data=False):
    """Used to insert form data to the workflow before running it
    Creates an identical json structure to the draft json.
    If cached_data is enabled, the data will be used by the next workflow
    initiated by the user.

    @param user_id: the user id

    @param uuid: the id of the workflow

    @param form_data: a json with field_name -> value structure

    @param append: set to True if you want to append the values to the existing
                   ones

    @param cached_data: set to True if you want to cache the data.
    """
    def preingest_data(form_data):
        def preingest(json):
            if 'pop_obj' not in json:
                json['pop_obj'] = {}
            for field, value in form_data.items():
                if append:
                    try:
                        if isinstance(json['pop_obj'][field], list):
                            json['pop_obj'][field].append(value)
                        else:
                            new_values_list = [json['pop_obj'][field]]
                            new_values_list.append(value)
                            json['pop_obj'][field] = new_values_list
                    except KeyError:
                        json['pop_obj'][field] = [value]
                else:
                    json['pop_obj'][field] = value
        return preingest

    if cached_data:
        cache.set(str(user_id) + ':cached_form_data', form_data)
    else:
        Workflow.set_extra_data(user_id=user_id, uuid=uuid,
                                setter=preingest_data(form_data))


def get_preingested_form_data(user_id, uuid=None, key=None, cached_data=False):
    def get_preingested_data(key):
        def getter(json):
            if 'pop_obj' in json:
                if key is None:
                    return json['pop_obj']
                else:
                    return json['pop_obj'][key]
            else:
                return {}
        return getter

    if cached_data:
        return cache.get(str(user_id) + ':cached_form_data')
    return Workflow.get_extra_data(user_id, uuid=uuid,
                                   getter=get_preingested_data(key))


def get_all_drafts(user_id):
    """ Returns a dictionary with deposition types and their """
    return dict(
        db.session.
        query(Workflow.name,
              db.func.count(Workflow.uuid)).
        filter(Workflow.status != CFG_WORKFLOW_STATUS.FINISHED,
               Workflow.user_id == 1).
        group_by(Workflow.name).
        all())

    drafts = dict(
        db.session.query(Workflow.name,
                         db.func.count(
                         db.func.distinct(WebDepositDraft.uuid))).
        join(WebDepositDraft.workflow).
        filter(db.and_(Workflow.user_id == user_id,
                       Workflow.status != CFG_WORKFLOW_STATUS.FINISHED)).
        group_by(Workflow.name).all())

    return drafts


def get_draft(user_id, uuid, field_name=None):
    """ Returns draft values in a field_name => field_value dictionary
        or if field_name is defined, returns the associated value
    """

    draft = Workflow.get(user_id=user_id, uuid=uuid)

    form_values = draft['form_values']

    if field_name is None:
        return form_values
    else:
        try:
            return form_values[field_name]
        except KeyError:  # field_name doesn't exist
            return form_values  # return whole row


def draft_field_get_all(user_id, deposition_type):
    """ Returns a list with values of the field_names specified
        containing all the latest drafts
        of deposition of type=deposition_type
    """

    ## Select drafts with max step workflow.
    workflows = Workflow.get(Workflow.status != CFG_WORKFLOW_STATUS.FINISHED,
                             Workflow.user_id == user_id,
                             Workflow.name == deposition_type,
                             Workflow.module_name == 'webdeposit').all()

    drafts = []
    get_max_draft = draft_getter()

    class Draft(object):
        def __init__(self, dictionary, workflow):
            for k, v in dictionary.items():
                setattr(self, k, v)
            setattr(self, 'workflow', workflow)
            setattr(self, 'uuid', workflow.uuid)

    for workflow in workflows:
        max_draft = get_max_draft(workflow.extra_data)
        drafts.append(Draft(max_draft, workflow))

    return drafts


def create_user_file_system(user_id, deposition_type, uuid):
    # Check if webdeposit folder exists
    if not os.path.exists(CFG_WEBDEPOSIT_UPLOAD_FOLDER):
        os.makedirs(CFG_WEBDEPOSIT_UPLOAD_FOLDER)

    # Create user filesystem
    # user/deposition_type/uuid/files
    CFG_USER_WEBDEPOSIT_FOLDER = os.path.join(CFG_WEBDEPOSIT_UPLOAD_FOLDER,
                                              "user_" + str(user_id))
    if not os.path.exists(CFG_USER_WEBDEPOSIT_FOLDER):
        os.makedirs(CFG_USER_WEBDEPOSIT_FOLDER)

    CFG_USER_WEBDEPOSIT_FOLDER = os.path.join(CFG_USER_WEBDEPOSIT_FOLDER,
                                              deposition_type)
    if not os.path.exists(CFG_USER_WEBDEPOSIT_FOLDER):
        os.makedirs(CFG_USER_WEBDEPOSIT_FOLDER)

    CFG_USER_WEBDEPOSIT_FOLDER = os.path.join(CFG_USER_WEBDEPOSIT_FOLDER,
                                              uuid)
    if not os.path.exists(CFG_USER_WEBDEPOSIT_FOLDER):
        os.makedirs(CFG_USER_WEBDEPOSIT_FOLDER)

    return CFG_USER_WEBDEPOSIT_FOLDER


def decode_dict_from_unicode(unicode_input):
    if isinstance(unicode_input, dict):
        return dict((decode_dict_from_unicode(key),
                     decode_dict_from_unicode(value))
                    for key, value in unicode_input.iteritems())
    elif isinstance(unicode_input, list):
        return [decode_dict_from_unicode(element) for element in unicode_input]
    elif isinstance(unicode_input, unicode):
        return unicode_input.encode('utf-8')
    else:
        return unicode_input


def url_upload(user_id, deposition_type, uuid, url, name=None, size=None):

    try:
        data = urlopen(url).read()
    except URLError:
        return "Error"

    CFG_USER_WEBDEPOSIT_FOLDER = create_user_file_system(user_id,
                                                         deposition_type,
                                                         uuid)
    unique_filename = str(new_uuid()) + name
    file_path = os.path.join(CFG_USER_WEBDEPOSIT_FOLDER,
                             unique_filename)
    f = open(file_path, 'wb')
    f.write(data)

    if size is None:
        size = os.path.getsize(file_path)
    if name is None:
        name = url.split('/')[-1]
    file_metadata = dict(name=name, file=file_path, size=size)
    draft_field_list_add(current_user.get_id(), uuid,
                         "files", file_metadata)

    return unique_filename


def deposit_files(user_id, deposition_type, uuid, preingest=False):
    """Attach files to a workflow
    Upload a single file or a file in chunks.
    Function must be called within a blueprint function that handles file
    uploading.

    Request post parameters:
        chunks: number of chunks
        chunk: current chunk number
        name: name of the file

    @param user_id: the user id

    @param deposition_type: the deposition the files will be attached

    @param uuid: the id of the deposition

    @param preingest: set to True if you want to store the file metadata in the
                      workflow before running the workflow, i.e. to bind the
                      files to the workflow and not in the last form draft.

    @return: the path of the uploaded file
    """
    if request.method == 'POST':
        try:
            chunks = request.form['chunks']
            chunk = request.form['chunk']
        except KeyError:
            chunks = None
            pass
        name = request.form['name']
        current_chunk = request.files['file']

        try:
            filename = secure_filename(name) + "_" + chunk
        except UnboundLocalError:
            filename = secure_filename(name)

        CFG_USER_WEBDEPOSIT_FOLDER = create_user_file_system(user_id,
                                                             deposition_type,
                                                             uuid)

        # Save the chunk
        current_chunk.save(os.path.join(CFG_USER_WEBDEPOSIT_FOLDER, filename))

        unique_filename = ""

        if chunks is None:  # file is a single chunk
            unique_filename = str(new_uuid()) + filename
            old_path = os.path.join(CFG_USER_WEBDEPOSIT_FOLDER, filename)
            file_path = os.path.join(CFG_USER_WEBDEPOSIT_FOLDER,
                                     unique_filename)
            os.rename(old_path, file_path)  # Rename the chunk
            size = os.path.getsize(file_path)
            file_metadata = dict(name=name, file=file_path, size=size)
            if preingest:
                preingest_form_data(user_id, uuid, {'files': file_metadata})
            else:
                draft_field_list_add(user_id, uuid,
                                     "files", file_metadata)
        elif int(chunk) == int(chunks) - 1:
            '''All chunks have been uploaded!
                start merging the chunks'''
            filename = secure_filename(name)
            chunk_files = []
            for chunk_file in iglob(os.path.join(CFG_USER_WEBDEPOSIT_FOLDER,
                                                 filename + '_*')):
                chunk_files.append(chunk_file)

            # Sort files in numerical order
            chunk_files.sort(key=lambda x: int(x.split("_")[-1]))

            unique_filename = str(new_uuid()) + filename
            file_path = os.path.join(CFG_USER_WEBDEPOSIT_FOLDER,
                                     unique_filename)
            destination = open(file_path, 'wb')
            for chunk in chunk_files:
                shutil.copyfileobj(open(chunk, 'rb'), destination)
                os.remove(chunk)
            destination.close()
            size = os.path.getsize(file_path)
            file_metadata = dict(name=name, file=file_path, size=size)
            if preingest:
                preingest_form_data(user_id, uuid, {'files': file_metadata})
            else:
                draft_field_list_add(user_id, uuid,
                                     "files", file_metadata)
    return unique_filename


def delete_file(user_id, uuid, preingest=False):
    if request.method == 'POST':
        files = draft_field_get(user_id, uuid, "files")
        result = "File Not Found"
        filename = request.form['filename']
        if preingest:
            files = get_preingested_form_data(user_id, uuid, 'files')
        else:
            files = draft_field_get(user_id, uuid, "files")

        for i, f in enumerate(files):
            if filename == f['file'].split('/')[-1]:
                # get the unique name from the path
                os.remove(f['file'])
                del files[i]
                result = str(files) + "              "
                if preingest:
                    preingest_form_data(user_id, uuid, files)
                else:
                    draft_field_set(current_user.get_id(), uuid,
                                    "files", files)
                result = "File " + f['name'] + " Deleted"
                break
    return result

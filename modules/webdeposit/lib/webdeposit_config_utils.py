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

from werkzeug.utils import import_string
from invenio.cache import cache
from invenio.webuser_flask import current_user
from invenio.webdeposit_cook_json_utils import cook_to_recjson
from invenio.bibworkflow_model import Workflow
from invenio.webinterface_handler_flask_utils import _


class WebDepositConfiguration(object):
    """ Webdeposit configuration class
        Returns configuration for fields based on runtime variables
        or, if not defined, based on the parameters

        @param deposition_type: initialize the class for a deposition type

        @param form_name: initialize the class for a form
            used when a form is defined to load validators and widgets

        @param field_type: initialize the class for a field
            used in the field pre_validate and autocomplete methods
            to load and call them on runtime
    """

    def __init__(self, deposition_type=None, form_type=None, field_type=None):
        self.config = import_string('invenio.webdeposit_config:config')
        self.deposition_type = deposition_type
        self.form_type = form_type
        self.field_type = field_type
        self._runtime_vars_init()

    def _runtime_vars_init(self):
        """ Initializes user_id, deposition type, uuid and form_type
        """
        from invenio.webdeposit_utils import draft_getter

        self.user_id = current_user.get_id()

        if self.deposition_type is None:

            self.runtime_deposition_type = \
                cache.get(str(self.user_id) +
                          ":current_deposition_type")
        else:
            self.runtime_deposition_type = None

            #  The uuid is always defined on runtime
        self.uuid = cache.get(str(self.user_id) + ":current_uuid")

        if self.uuid is not None and self.form_type is None:
            draft = Workflow.get_extra_data(user_id=self.user_id,
                                            uuid=self.uuid,
                                            getter=draft_getter())
            self.runtime_form_type = draft['form_type']
        else:
            self.runtime_form_type = None

    #FIXME: Make the deposition_type, form_type and field_type an attribute
    def get_deposition_type(self):
        return self.runtime_deposition_type or self.deposition_type

    def get_form_type(self):
        return self.runtime_form_type or self.form_type

    def get_field_type(self):
        return self.field_type

    def _parse_config(self, config_key, deposition_type=None, form_type=None,
                      field_type=None):
        if deposition_type in self.config:
            deposition_config = self.config[deposition_type]
            if form_type is None and config_key in deposition_config:
                return deposition_config[config_key]

            if form_type in deposition_config:
                form_config = deposition_config[form_type]
                if field_type is None and config_key in form_config:
                    return form_config[config_key]

                if field_type in form_config['fields']:
                    field_config = form_config['fields'][field_type]
                    if config_key in field_config:
                        if config_key in field_config:
                            return field_config[config_key]

        return None

    def get_form_title(self, form_type=None):
        """ Returns the title of the form

            @param form_type: the type of the form.
                to use this function it must be defined here
                or at the class construction
        """

        deposition_type = self.get_deposition_type()
        form_type = self.get_form_type()

        title = self._parse_config('title',
                                   deposition_type=deposition_type,
                                   form_type=form_type)
        if title is not None:
            return _(title)
        else:
            return None

    def get_label(self, field_type=None):
        """ Returns the label of the field

            @param field_type: the type of the field.
                to use this function it must be defined here
                or at the class construction
        """

        deposition_type = self.get_deposition_type()
        form_type = self.get_form_type()
        field_type = field_type or self.get_field_type()

        label = self._parse_config('label',
                                   deposition_type=deposition_type,
                                   form_type=form_type,
                                   field_type=field_type)

        if label is None:
            return None
        else:
            return _(label)

    def get_widget(self, field_type=None):
        """ Returns the widget of the field

            @param field_type: the type of the field.
                to use this function it must be defined here
                or at the class construction
        """

        deposition_type = self.get_deposition_type()
        form_type = self.get_form_type()
        field_type = field_type or self.get_field_type()

        widget = self._parse_config('widget',
                                    deposition_type=deposition_type,
                                    form_type=form_type,
                                    field_type=field_type)

        if widget is None:
            return None
        else:
            return import_string(widget)

    def get_autocomplete_function(self):
        """ Returns an autocomplete function of the field
        """
        deposition_type = self.get_deposition_type()
        form_type = self.get_form_type()
        field_type = self.get_field_type()

        autocomplete = self._parse_config('autocomplete',
                                          deposition_type=deposition_type,
                                          form_type=form_type,
                                          field_type=field_type)

        if autocomplete is None:
            return None
        else:
            return import_string(autocomplete)

    def get_validators(self, field_type=None):
        """ Returns validators function based of the field
        """
        deposition_type = self.get_deposition_type()
        form_type = self.get_form_type()
        field_type = field_type or self.get_field_type()

        vals = self._parse_config('validators',
                                  deposition_type=deposition_type,
                                  form_type=form_type,
                                  field_type=field_type)

        validators = []
        if vals is None:
            return []
        else:
            for validator in vals:
                validators.append(import_string(validator))

            return validators

    def get_recjson_key(self, field_type=None):
        deposition_type = self.get_deposition_type()
        form_type = self.get_form_type()
        field_type = field_type or self.get_field_type()

        return self._parse_config('recjson_key',
                                  deposition_type=deposition_type,
                                  form_type=form_type,
                                  field_type=field_type)

    def get_cook_json_function(self, field_type=None):
        recjson_key = self.get_recjson_key(field_type)
        if recjson_key is not None:
            return cook_to_recjson(recjson_key)

    def get_template(self, form_type=None):
        deposition_type = self.get_deposition_type()
        form_type = self.get_form_type() or form_type

        template = self._parse_config('template',
                                      deposition_type=deposition_type,
                                      form_type=form_type)

        if template is None:
            return None
        else:
            return template

    def get_files_cook_function(self, form_type=None):
        deposition_type = self.get_deposition_type()
        form_type = self.get_form_type() or form_type

        file_cook = self._parse_config('file_cook',
                                       deposition_type=deposition_type,
                                       form_type=form_type)

        if file_cook is None:
            return None
        else:
            return import_string(file_cook)

    def get_collection(self, deposition_type=None):
        deposition_type = deposition_type or self.get_deposition_type()

        return self._parse_config('collection',
                                  deposition_type=deposition_type)

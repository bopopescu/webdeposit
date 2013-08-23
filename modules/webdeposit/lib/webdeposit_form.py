# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2013 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA

from invenio.wtforms_utils import InvenioForm as Form
from invenio.webdeposit_cook_json_utils import cook_files, uncook_files

CFG_GROUPS_META = {
    'classes': None,
    'indication': None,
    'description': None
}
"""
Default group metadata.
"""

CFG_FIELD_FLAGS = [
    'hidden',
    'disabled'
]
"""
List of WTForm field flags to be saved in draft.

See more about WTForm field flags on:
http://wtforms.simplecodes.com/docs/1.0.4/fields.html#wtforms.fields.Field.flags
"""


def filter_flags(field):
    """
    Return a list of flags (from CFG_FIELD_FLAGS) set on a field.
    """
    return filter(lambda flag: getattr(field.flags, flag), CFG_FIELD_FLAGS)

"""
Form customization

you can customize the following for the form

_title: str, the title to be rendered on top of the form
_subtitle: str/html. explanatory text to be shown under the title.
_drafting: bool, show or hide the drafts at the right of the form

"""


class WebDepositForm(Form):

    """ Generic WebDeposit Form class """

    def __init__(self, *args, **kwargs):
        super(WebDepositForm, self).__init__(*args, **kwargs)
        self.groups_meta = {}
        if hasattr(self, 'groups'):
            for idx, group in enumerate(self.groups):
                group_name = group[0]
                fields = group[1]
                for field in fields:
                    setattr(self[field], 'group', group_name)

                self.groups_meta[group_name] = CFG_GROUPS_META.copy()
                if len(group) == 3:  # If group has metadata
                    self.groups_meta[group_name].update(group[2])

        if not hasattr(self, 'template'):
            self.template = 'webdeposit_add.html'

        if not hasattr(self, '_drafting'):
            self._drafting = True

        self.type = self.__class__.__name__

    def reset_field_data(self, exclude=[]):
        """
        Reset the fields.data value to that of field.object_data.

        Useful after initializing a form with both formdata and draftdata where
        the formdata is missing field values (usually because we are saving a
        single field).

        @param exclude: List of field names to exclude.
        """
        for field in self._fields.values():
            field.reset_field_data(exclude=exclude)

    def cook_json(self, json_reader):
        for field in self._fields.values():
            try:
                json_reader = field.cook_json(json_reader)
            except AttributeError:
                # Some fields (eg. SubmitField) don't have a cook json function
                pass

        json_reader = cook_files(json_reader, self.files)

        return json_reader

    def uncook_json(self, json_reader, webdeposit_json, recid=None):
        for field in self._fields.values():
            if hasattr(field, 'uncook_json'):
                # WTFields are not mapped with rec json
                webdeposit_json = field.uncook_json(json_reader,
                                                    webdeposit_json)

        webdeposit_json = uncook_files(webdeposit_json, recid=recid,
                                       json_reader=json_reader)
        return webdeposit_json

    def get_groups(self):
        """
        Get a list of the (group metadata, list of fields)-tuples

        The last element of the list has no group metadata (i.e. None),
        and contains the list of fields not assigned to any group.
        """
        fields_included = set()
        field_groups = []

        if hasattr(self, 'groups'):
            for group in self.groups:
                group_obj = {
                    'name': group[0],
                    'meta': CFG_GROUPS_META.copy(),
                }

                fields = []
                for field_name in group[1]:
                    fields.append(self[field_name])
                    fields_included.add(field_name)

                if len(group) == 3:
                    group_obj['meta'].update(group[2])

                field_groups.append((group_obj, fields))

        # Append missing fields not defined in groups
        rest_fields = []
        for field in self:
            if field.name not in fields_included:
                rest_fields.append(field)
        if rest_fields:
            field_groups.append((None, rest_fields))

        return field_groups

    def get_template(self):
        """
        Get template to render this form.
        Define a data member `template` to customize which template to use.

        By default, it will render the template `webdeposit_add.html`

        """
        return [self.template]

    def post_process(self, form=None, formfields=[], submit=False):
        """
        Run form post-processing by calling `post_process` on each field,
        passing any extra `Form.post_process_<fieldname>` processors to the
        field.

        If ``formfields'' are specified, only the given fields' processors will
        be run (which may touch all fields of the form).

        The post processing allows the form to alter other fields in the form,
        via e.g. contacting external services (e.g a DOI field could retrieve
        title, authors from CrossRef/DataCite).
        """
        if form is None:
            form = self

        for name, field, in self._fields.items():
            inline = getattr(
                self, 'post_process_%s' % name, None)
            if inline is not None:
                extra = [inline]
            else:
                extra = []
            field.post_process(form, formfields=formfields,
                               extra_processors=extra, submit=submit)

    def autocomplete(self, name, term, limit=50, _form=None):
        """
        Auto complete a form field.

        Example::

            form = FormClass()
            form.autocomplete('related_identifiers-1-scheme','do')

        Implementation notes:
        The form will first try a fast lookup by field name in the form, and
        delegate the auto-completion to the field. This will work for all but
        field enclosures (FieldList and FormField). If the first lookup fails,
        each field enclosure is checked if they can auto-complete the term,
        which usually involves parsing the field name and generating a
        stub-field (see further details in wtforms_field module).

        @param name: Name of field (e.g. title or related_identifiers-1-scheme).
        @param term: Term to return auto-complete results for
        @param limit: Maximum number of results to return
        @return: None in case field could not be found, otherwise a (possibly
            empty) list of results.
        """
        if name in self._fields:
            res = self._fields[name].perform_autocomplete(
                _form or self,
                name,
                term,
                limit=limit,
            )
            if res is not None:
                return res[:limit]
        else:
            for f in self._fields.values():
                # Only check field enclosures which cannot be found with above
                # method.
                if name.startswith(f.name):
                    res = f.perform_autocomplete(
                        _form or self,
                        name,
                        term,
                        limit=limit,
                    )
                    if res is not None:
                        return res[:limit]
        return None

    def get_flags(self, filter_func=filter_flags):
        """
        Return dictionary of fields and their set flags
        """
        flags = {}

        for f in self._fields.values():
            if hasattr(f, 'get_flags'):
                flags.update(f.get_flags(filter_func=filter_func))
            else:
                flags.update({f.name: filter_func(f)})

        return flags

    def set_flags(self, flags):
        """
        Set flags on fields

        @param flags: Dictionary of fields and their set flags (same structure
                      as returned by get_flags).
        """
        for f in self._fields.values():
            f.set_flags(flags)

    @property
    def json_data(self):
        """
        Return form data in a format suitable for the standard JSON encoder, by
        calling Field.json_data() on each field if it exists, otherwise is uses
        the value of Field.data.
        """
        return dict(
            (name, f.json_data if getattr(f, 'json_data', None) else f.data)
            for name, f in self._fields.items()
        )

    @property
    def messages(self):
        """
        Return a dictionary of form messages.
        """
        _messages = {}

        for f in self._fields.values():
            _messages.update(f.messages)

        return dict([
            (
                fname,
                msgs if msgs.get('state', '') or msgs.get('messages', '') else {}
            ) for fname, msgs in _messages.items()
        ])

        return _messages

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

from wtforms.widgets import html_params, HTMLString
from invenio.jinja2utils import render_template_to_string

def date_widget(field, **kwargs):
    field_id = kwargs.pop('id', field.id)
    html = [u'<input class="datepicker" %s type="text">'
            % html_params(id=field_id, name=field_id, value=field.data or '')]
    field_class = kwargs.pop('class', '') or kwargs.pop('class_', '')
    kwargs['class'] = u'datepicker %s' % field_class
    kwargs['class'] = u'date %s' % field_class
    return HTMLString(u''.join(html))


def plupload_widget(field, **kwargs):
    field_id = kwargs.pop('id', field.id)
    kwargs['class'] = u'plupload'

    return HTMLString(
        render_template_to_string(
            "webdeposit_widget_plupload.html",
            field=field,
            field_id=field_id,
        )
    )


def bootstrap_submit(field, **kwargs):
    html = u'<input %s >' % html_params(style="float:right; width: 250px;",
                                        id="submitButton",
                                        class_="btn btn-primary btn-large",
                                        name="submitButton",
                                        type="submit",
                                        value=field.label.text,)
    html = [u'<div style="float:right;" >' + html + u'</div>']
    return HTMLString(u''.join(html))


def ckeditor_widget(field, **kwargs):
    field.ckeditor = True
    field_id = kwargs.pop('id', field.id)
    html = [u'<textarea %s >'
            % html_params(id=field_id, name=field_id, value=field.data or '')]
    html.append('%s</textarea>' % field.data or '')
    return HTMLString(u''.join(html))


def dropbox_widget(field, **kwargs):
    field_id = kwargs.pop('id', field.id)
    html = [u'<input type="dropbox-chooser"\
            name="fileurl"\
            style="visibility: hidden;"\
            data-link-type="direct"\
            id="db-chooser"/></br> \
        <div class="pluploader" %s > \
            <table id="file-table" class="table table-striped table-bordered" style="display:none;">\
                <thead>\
                    <tr>\
                    <th>Filename</th>\
                    <th>Size</th>\
                    <th>Status</th>\
                    <td></td>\
                    </tr>\
                </thead>\
                <tbody id="filelist">\
                </tbody>\
            </table>\
            <a class="btn btn-success disabled" id="uploadfiles"> \
                <i class="icon-upload icon-white"></i> Start upload</a>\
            <a class="btn btn-danger" id="stopupload" style="display:none;">\
                <i class="icon-stop icon-white"></i> Cancel upload</a>\
            <span id="upload_speed" class="pull-right"></span>\
            <div id="upload-errors"></div>\
        </div>' % html_params(id=field_id)]
    return HTMLString(u''.join(html))

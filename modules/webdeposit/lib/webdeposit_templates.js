var tpl_webdeposit_status_saved = Hogan.compile('Saved <i class="icon-ok"></i>');
var tpl_webdeposit_status_saved_with_errors = Hogan.compile('<span class="text-warning">Saved, but with errors <i class="icon-warning-sign"></i></span>');
var tpl_webdeposit_status_saving = Hogan.compile('Saving <img src="/css/images/ajax-loader.gif" />');
var tpl_webdeposit_status_error = Hogan.compile('<span class="text-error">Not saved due to server error. Please try to reload your browser <i class="icon-warning-sign"></i></span>');
var tpl_field_message = Hogan.compile('{{#messages}}<div>{{{.}}}</div>{{/messages}}');
var tpl_required_field_message = Hogan.compile('{{{label}}} is required.');
var tpl_flash_message = Hogan.compile('<div class="alert alert-{{state}}"><a class="close" data-dismiss="alert" href="#"">&times;</a>{{{message}}}</div>');
var tpl_message_success = Hogan.compile('Successfully saved.');
var tpl_message_errors = Hogan.compile('The form was saved, but there were errors. Please see below.');
var tpl_message_server_error = Hogan.compile('The form could not be saved, due to a communication problem with the server. Please try to reload your browser <i class="icon-warning-sign"></i>');
var tpl_loader = Hogan.compile('<img src="/img/loading.gif" />');
var tpl_loader_success = Hogan.compile('<span class="text-success"> <i class="icon-ok"></i></span>');
var tpl_loader_failed = Hogan.compile('<span class="muted"> <i class="icon-warning-sign"></i></span>');
var tpl_file_entry = Hogan.compile('<tr id="{{id}}" class="hide">' +
    '<td id="{{id}}_link">{{#download_url}}<a href="{{download_url}}">{{filename}}</a>{{/download_url}}{{^download_url}}{{filename}}{{/download_url}}</td>' +
    '<td>{{filesize}}</td>' +
    '<td width="30%"><div class="progress{{#striped}} progress-striped{{/striped}} active"><div class="bar" style="width: {{progress}}%;"></div></div></td>' +
    '<td>{{#removeable}}<a id={{id}}_rm" class="rmlink" rel="tooltip" title="Delete file"><i class="icon-trash"></i></a>{{/removeable}}&nbsp;<a id="{{id_sort}}" class="sortlink" rel="tooltip" title="Re-order files"><i class="icon-align-justify"></i></a></td>' +
    '</tr>');
var tpl_file_link = Hogan.compile('<a href="{{download_url}}">{{filename}}</a>');

/*
 * This file is part of CDS Invenio.
 * Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007, 2008 2009 CERN.
 *
 * CDS Invenio is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * CDS Invenio is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with CDS Invenio; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
 */

/*
 * This is the BibEdit Javascript for all functionality directly related to the
 * left hand side menu, including event handlers for the controls.
 */

/*
 * Global variables
 */

// Interval (in ms) between menu repositioning.
var gCHECK_SCROLL_INTERVAL = 250;

// Display status messages for how long (in ms).
var gSTATUS_RESET_TIMEOUT = 1000;

// Color of new field form.
var gNEW_ADD_FIELD_FORM_COLOR = 'lightblue';
// Duration (in ms) for the color fading of new field form.
var gNEW_ADD_FIELD_FORM_COLOR_FADE_DURATION = 2000;


function initMenu(){
  /*
   * Initialize menu.
   */
  // Make sure the menu is in it's initial state.
  deactivateMenu();
  $('#txtSelectRecord').attr('value', '');
  // Submit get request on enter.
  $('#txtSelectRecord').bind('keypress', function(event){
    if (event.keyCode == 13){
      $('#btnGetRecord').click();
      event.preventDefault();
    }
  });
  // Set the status.
  $('#cellIndicator').html(img('/img/circle_green'));
  $('#cellStatus').text('Ready');
  // Bind button event handlers.
  $('#btnGetRecord').bind('click', onGetRecordClick);
  $('#btnSubmit').bind('click', onSubmitClick);
  $('#btnCancel').bind('click', onCancelClick);
  $('#btnDeleteRecord').bind('click', onDeleteRecordClick);
  $('#lnkMARCTags').bind('click', onMARCTagsClick);
  $('#lnkHumanTags').bind('click', onHumanTagsClick);
  $('#btnAddField').bind('click', onAddFieldClick);
  $('#btnSortFields').bind('click', function(){
    updateStatus('updating');
    $('#bibEditContent').empty();
    displayRecord();
    updateStatus('ready');
  });
  $('#btnDeleteSelected').bind('click', onDeleteSelectedClick);
  // Focus on record selection box.
  $('#txtSelectRecord').focus();
  // Initialize menu positioning (poll for scrolling).
  setInterval(positionMenu, gCHECK_SCROLL_INTERVAL);
}

function positionMenu(){
  /*
   * Dynamically position menu based on vertical scroll distance.
   */
  var newYscroll = $(document).scrollTop();
  // Only care if there has been some major scrolling.
  if (Math.abs(newYscroll - positionMenu.yScroll) > 10){
    // If scroll distance is less then 200px, position menu in sufficient
    // distance from header.
    if (newYscroll < 200)
      $('#bibEditMenu').animate({
	'top': 220 - newYscroll}, 'fast');
    // If scroll distance has crossed 200px, fix menu 50px from top.
    else if (positionMenu.yScroll < 200 && newYscroll > 200)
      $('#bibEditMenu').animate({
	'top': 50}, 'fast');
    positionMenu.yScroll = newYscroll;
  }
}
// Last Y-scroll value
positionMenu.yScroll = 0;

function deactivateMenu(){
  /*
   * Deactivate menu.
   */
  $('#lnkMARCTags').removeAttr('href');
  $('#lnkMARCTags').unbind('click');
  $('#lnkHumanTags').removeAttr('href');
  $('#lnkHumanTags').unbind('click');
  $('#btnSubmit').attr('disabled', 'disabled');
  $('#btnCancel').attr('disabled', 'disabled');
  $('#btnAddField').attr('disabled', 'disabled');
  $('#btnSortFields').attr('disabled', 'disabled');
  $('#btnDeleteSelected').attr('disabled', 'disabled');
  $('#btnDeleteRecord').attr('disabled', 'disabled');
}

function updateStatus(statusType, reporttext){
  /*
   * Update status (in the bottom of the menu).
   */
  var image, text;
  switch (statusType){
    case 'ready':
      image = img('/img/circle_green.png');
      text = 'Ready';
      break;
    case 'updating':
      image = img('/img/indicator.gif');
      text = 'Updating...';
      break;
    // Generic report. Resets to 'Ready' after timeout.
    case 'report':
      image = img('/img/circle_green.png');
      text = reporttext;
      clearTimeout(updateStatus.statusResetTimerID);
      updateStatus.statusResetTimerID = setTimeout('updateStatus("ready")',
				  gSTATUS_RESET_TIMEOUT);
      break;
    default:
      image = '';
      text = '';
  }
  $('#cellIndicator').html(image);
  $('#cellStatus').html(text);
}

function onGetRecordClick(){
  /*
   * Handle 'Get' button (get record).
   */
  var recID = $('#txtSelectRecord').attr('value');
  if (gRecID == recID && gState == 'Edit')
    // We are already editing this record.
    return;
  else{
    updateStatus('updating');
    cleanUpDisplay();
    gRecID = recID;
    $('.headline').text('BibEdit: Record #' + gRecID);
    changeAndSerializeHash({state: 'edit', recid: recID});
    createReq({recID: gRecID, requestType: 'getRecord'}, onGetRecordSuccess);
  }
}

function onGetRecordSuccess(json){
  /*
   * Handle successfull 'getRecord' request.
   */
  gPageDirty = false;
  if (json['resultCode'] != 0){
    // Not that successfull requests...
    deactivateMenu();
    displayMessage(json['resultText']);
    gState = 'RecordError';
    updateStatus('ready');
  }
  else{
    // Display record.
    gRecord = json['record'];
    gTagFormat = json['tagFormat'];
    $('.headline').html(
      'BibEdit: Record #' + gRecID +
	'<a href="' + gHistoryURL + '?recid=' + gRecID +
	'" style="margin-left: 5px; font-size: 0.5em; color: #36c;">' +
	'(view history)' +
	'</a>');
    resetNewFieldNumber();
    displayRecord();
    // Activate all disabled buttons.
    $('button[disabled]').removeAttr('disabled');
    if (gTagFormat == 'MARC'){
      $('#lnkHumanTags').bind('click', onHumanTagsClick);
      $('#lnkHumanTags').attr('href', 'human');
    }
    else{
      $('#lnkMARCTags').bind('click', onMARCTagsClick);
      $('#lnkMARCTags').attr('href', 'marc');
    }
    updateStatus('report', json['resultText']);
  }
}

function onSubmitClick(){
  /*
   * Handle 'Submit' button (submit record).
   */
  var recID = gRecID;
  updateStatus('updating');
  cleanUpDisplay();
  $('#txtSelectRecord').attr('value', '');
  $('#txtSelectRecord').focus();
  changeAndSerializeHash({state: 'submit',
			  recid: recID});
  createReq({recID: recID, requestType: 'submit'}, function(json){
    updateStatus('report', json['resultText']);
    displayMessage('Confirm: Submitted');
  });
}

function onCancelClick(){
  /*
   * Handle 'Cancel' button (cancel editing).
   */
  var recID = gRecID;
  updateStatus('updating');
  cleanUpDisplay();
  $('#txtSelectRecord').attr('value', '');
  $('#txtSelectRecord').focus();
  changeAndSerializeHash({state: 'cancel',
			  recid: recID});
  createReq({recID: recID, requestType: 'cancel'}, function(json){
    updateStatus('report', json['resultText']);
  });
}

function onDeleteRecordClick(){
  /*
   * Handle 'Delete record' button.
   */
  var recID = gRecID;
  updateStatus('updating');
  cleanUpDisplay();
  $('#txtSelectRecord').attr('value', '');
  $('#txtSelectRecord').focus();
  changeAndSerializeHash({state: 'deleteRecord',
			  recid: recID});
  createReq({recID: recID, requestType: 'deleteRecord'}, function(json){
    displayMessage('Confirm: Deleted');
    updateStatus('report', json['resultText']);
  });
}

function onMARCTagsClick(event){
  /*
   * Handle 'MARC' link (MARC tags).
   */
  $('#lnkMARCTags').unbind('click');
  $('#lnkMARCTags').removeAttr('href');
  createReq({recID: gRecID, requestType: 'changeTagFormat', tagFormat: 'MARC'});
  gTagFormat = 'MARC';
  updateTags();
  $('#lnkHumanTags').bind('click', onHumanTagsClick);
  $('#lnkHumanTags').attr('href', 'human');
  event.preventDefault();
}

function onHumanTagsClick(event){
  /*
   * Handle 'Human' link (Human tags).
   */
  $('#lnkHumanTags').unbind('click');
  $('#lnkHumanTags').removeAttr('href');
  createReq({recID: gRecID, requestType: 'changeTagFormat',
	     tagFormat: 'human'});
  gTagFormat = 'human';
  updateTags();
  $('#lnkMARCTags').bind('click', onMARCTagsClick);
  $('#lnkMARCTags').attr('href', 'marc');
  event.preventDefault();
}

function updateTags(){
  /*
   * Check and update all tags (also subfield codes) against the currently
   * selected tag format.
   */
  $('.bibEditCellFieldTag').each(function(){
    var currentTag = $(this).text();
    var tmpArray = this.id.split('_');
    var tag = tmpArray[1], fieldNumber = tmpArray[2];
    var newTag = getFieldTag(getMARC(tag, fieldNumber));
    if (newTag != currentTag)
      $(this).text(newTag);
  });
  $('.bibEditCellSubfieldTag').each(function(){
    var currentTag = $(this).text();
    var tmpArray = this.id.split('_');
    var tag = tmpArray[1], fieldNumber = tmpArray[2],
      subfieldIndex = tmpArray[3];
    var newTag = getSubfieldTag(getMARC(tag, fieldNumber, subfieldIndex));
    if (newTag != currentTag)
      $(this).text(newTag);
  });
}

function onAddFieldClick(){
  /*
   * Handle 'Add field' button.
   */
  // Create form and scroll close to the top of the table.
  $(document).scrollTop(0);
  var fieldTmpNo = onAddFieldClick.addFieldFreeTmpNo++;
  $('#bibEditColFieldTag').css('width', '80px');
  $('#bibEditTable tbody').eq(3).after(createAddFieldRowGroup(fieldTmpNo));

  // Bind event handlers.
  $('#chkAddFieldControlfield_' + fieldTmpNo).bind('click',
    onAddFieldControlfieldClick);
  $('#btnAddFieldAddSubfield_' + fieldTmpNo).bind('click', function(){
    var hdnFreeSubfieldTmpNo = $('#hdnAddFieldFreeSubfieldTmpNo_' + fieldTmpNo);
    var subfieldTmpNo = parseInt($(hdnFreeSubfieldTmpNo).attr('value'));
    $(hdnFreeSubfieldTmpNo).attr('value', subfieldTmpNo+1);
    var addFieldRows = $('#rowGroupAddField_' + fieldTmpNo + ' tr');
    $(addFieldRows).eq(addFieldRows.length-1).before(createAddFieldRow(
      fieldTmpNo, subfieldTmpNo));
    $('#txtAddFieldSubfieldCode_' + fieldTmpNo + '_' + subfieldTmpNo).bind(
      'keyup', onAddFieldChange);
    $('#btnAddFieldRemove_' + fieldTmpNo + '_' + subfieldTmpNo).bind('click',
      function(){
	$('#rowAddField_' + this.id.slice(this.id.indexOf('_')+1)).remove();
      });
  });
  $('#txtAddFieldTag_' + fieldTmpNo).bind('keyup', onAddFieldChange);
  $('#txtAddFieldInd1_' + fieldTmpNo).bind('keyup', onAddFieldChange);
  $('#txtAddFieldInd2_' + fieldTmpNo).bind('keyup', onAddFieldChange);
  $('#txtAddFieldSubfieldCode_' + fieldTmpNo + '_0').bind('keyup',
							  onAddFieldChange);
  $('#btnAddFieldSave_' + fieldTmpNo).bind('click', onAddFieldSave);
  $('#btnAddFieldCancel_' + fieldTmpNo).bind('click', function(){
    $('#rowGroupAddField_' + fieldTmpNo).remove();
    if (!$('#bibEditTable > [id^=rowGroupAddField]').length)
      $('#bibEditColFieldTag').css('width', '48px');
    reColorFields();
  });
  $('#btnAddFieldClear_' + fieldTmpNo).bind('click', function(){
    $('#rowGroupAddField_' + fieldTmpNo + ' input[type="text"]').attr(
      'value', '').removeClass('bibEditInputError');
    $('#txtAddFieldTag_' + fieldTmpNo).focus();
  });

  reColorFields();
  $('#txtAddFieldTag_' + fieldTmpNo).focus();
  // Color the new form for a short period.
  var rowGroup = $('#rowGroupAddField_' + fieldTmpNo);
  $(rowGroup).effect('highlight', {color: gNEW_ADD_FIELD_FORM_COLOR},
		     gNEW_ADD_FIELD_FORM_COLOR_FADE_DURATION);
}
// Incrementing temporary field numbers.
onAddFieldClick.addFieldFreeTmpNo = 100000;

function onAddFieldControlfieldClick(){
  /*
   * Handle 'Controlfield' checkbox in add field form.
   */
  var fieldTmpNo = this.id.split('_')[1];

  // Remove any extra rows.
  var addFieldRows = $('#rowGroupAddField_' + fieldTmpNo + ' tr');
  $(addFieldRows).slice(2, addFieldRows.length-1).remove();

  // Clear all fields.
  var addFieldTextInput = $('#rowGroupAddField_' + fieldTmpNo +
			    ' input[type=text]');
  $(addFieldTextInput).attr('value', '').removeClass('bibEditInputError');
  $('#hdnAddFieldFreeSubfieldTmpNo_' + fieldTmpNo).attr('value', 1);

  // Toggle hidden fields.
  var elems = $('#txtAddFieldInd1_' + fieldTmpNo + ', #txtAddFieldInd2_' + fieldTmpNo +
    ', #txtAddFieldSubfieldCode_' + fieldTmpNo + '_0,' +
    '#btnAddFieldAddSubfield_' + fieldTmpNo);
  $(elems).each(function(){
    $(this).toggleClass('bibEditHidden');
  });

  $('#txtAddFieldTag_' + fieldTmpNo).focus();
}

function onAddFieldChange(){
  /*
   * Validate MARC and add or remove error class.
   */
  if (this.value.length == this.maxLength){
    var fieldTmpNo = this.id.split('_')[1];
    var fieldType;
    if (this.id.indexOf('Tag') != -1)
      fieldType = ($('#chkAddFieldControlfield_' + fieldTmpNo).attr('checked')
		  ) ? 'ControlTag' : 'Tag';
    else if (this.id.indexOf('Ind') != -1)
      fieldType = 'Indicator';
    else
      fieldType = 'SubfieldCode';

    var valid = (fieldType == 'Indicator' && (this.value == '_'
					      || this.value == ' '))
                 || validMARC(fieldType, this.value);
    if (!valid && !$(this).hasClass('bibEditInputError'))
      $(this).addClass('bibEditInputError');
    else if (valid && $(this).hasClass('bibEditInputError'))
      $(this).removeClass('bibEditInputError');
  }
  else if ($(this).hasClass('bibEditInputError'))
    $(this).removeClass('bibEditInputError');
}

function onAddFieldSave(event){
  /*
   * Handle 'Save' button in add field form.
   */
  updateStatus('updating');
  var fieldTmpNo = this.id.split('_')[1];
  var controlfield = $('#chkAddFieldControlfield_' + fieldTmpNo).attr(
		       'checked');
  var tag = $('#txtAddFieldTag_' + fieldTmpNo).attr('value');
  var value = $('#txtAddFieldValue_' + fieldTmpNo + '_0').attr('value');
  var subfields = [], ind1 = ' ', ind2 = ' ';

  if (controlfield){
    // Controlfield. Validate and prepare to update.
    if (fieldIsProtected(tag)){
      displayAlert('alert', 'errorAddProtectedField', true, tag);
      return;
    }
    if (!validMARC('ControlTag', tag) || value == ''){
      displayAlert('alert', 'errorCriticalInput', true     );
      return;
    }
    var field = [[], ' ', ' ', value, gNewFieldNumber];
    var newRowGroup = createControlField(tag, field);
  }
  else{
    // Regular field. Validate and prepare to update.
    ind1 = $('#txtAddFieldInd1_' + fieldTmpNo).attr('value');
    ind1 = (ind1 == '' || ind1 == ' ') ? '_' : ind1;
    ind2 = $('#txtAddFieldInd2_' + fieldTmpNo).attr('value');
    ind2 = (ind2 == '' || ind2 == ' ') ? '_' : ind2;
    var MARC = tag + ind1 + ind2;
    if (fieldIsProtected(MARC)){
      displayAlert('alert', 'errorAddProtectedField', true, MARC);
      return;
    }
    var validInd1 = (ind1 == '_' || validMARC('Indicator', ind1));
    var validInd2 = (ind2 == '_' || validMARC('Indicator', ind2));
    if (!validMARC('Tag', tag)
	|| !(ind1 == '_' || validMARC('Indicator', ind1))
	|| !(ind2 == '_' || validMARC('Indicator', ind2))){
      displayAlert('alert', 'errorCriticalInput', true     );
      return;
    }
    // Collect valid subfields in an array.
    var invalidOrEmptySubfields = false;
    $('#rowGroupAddField_' + fieldTmpNo + ' .bibEditTxtSubfieldCode'
      ).each(function(){
        var subfieldTmpNo = this.id.slice(this.id.lastIndexOf('_')+1);
        var txtValue = $('#txtAddFieldValue_' + fieldTmpNo + '_' +
	  subfieldTmpNo);
        var value = $(txtValue).attr('value');
        if (!$(this).hasClass('bibEditInputError')
	  && this.value != ''
	  && !$(txtValue).hasClass('bibEditInputError')
	  && value != '')
            subfields.push([this.value, value]);
        else
          invalidOrEmptySubfields = true;
      });

    if (invalidOrEmptySubfields){
      if (subfields.length < 1){
	// No valid subfields.
	displayAlert('alert', 'errorCriticalInput', true     );
	return;
      }
      else if (!displayAlert('confirm', 'warningInvalidOrEmptyInput')){
	updateStatus('ready');
	return;
      }
    }
    var field = [subfields, ind1, ind2, '', gNewFieldNumber];
    var newRowGroup = createField(tag, field);
  }

  gPageDirty = true;
  // Create AJAX request.
  var data = {
    recID: gRecID,
    requestType: 'addField',
    controlfield: controlfield,
    tag: tag,
    ind1: ind1,
    ind2: ind2,
    subfields: subfields,
    value: value
  };
  createReq(data, function(json){
    updateStatus('report', json['resultText']);
  });

  // Continue local updating.
  var record = gRecord;
  var fields = gRecord[tag];
  // New field?
  if (!fields)
    gRecord[tag] = [field];
  else{
    fields.push(field);
    fields.sort(cmpFields);
  }
  var rowGroupAddField = $('#rowGroupAddField_' + fieldTmpNo);
  var coloredRowGroup = $(rowGroupAddField).hasClass('bibEditFieldColored');
  $(rowGroupAddField).replaceWith(newRowGroup);
  if (coloredRowGroup)
    $('#rowGroup_' + tag + '_' + gNewFieldNumber).addClass(
      'bibEditFieldColored');
  if (!$('#bibEditTable > [id^=rowGroupAddField]').length)
      $('#bibEditColFieldTag').css('width', '48px');

  // Color the new form for a short period.
  var rowGroup = $('#rowGroup_' + tag + '_' + gNewFieldNumber);
  $(rowGroup).effect('highlight', {color: gNEW_FIELDS_COLOR},
		     gNEW_FIELDS_COLOR_FADE_DURATION);

  gNewFieldNumber++;
}

function onDeleteSelectedClick(){
  /*
   * Handle 'Delete selected' button.
   */
  updateStatus('updating');
  var toDelete = {};
  // Collect and remove all marked fields.
  var checkedFieldBoxes = $('input[class="bibEditBoxField"]:checked');
  var deleteFields = false;
  if (checkedFieldBoxes.length > 0)
    deleteFields = true;
  $(checkedFieldBoxes).each(function(){
    var tmpArray = this.id.split('_');
    var tag = tmpArray[1], fieldNumber = tmpArray[2];
    if (!toDelete[tag]){
      toDelete[tag] = {};
    }
    toDelete[tag][fieldNumber] = [];
  });
  // Collect subfields to be deleted in a datastructure.
  var checkedSubfieldBoxes = $('input[class="bibEditBoxSubfield"]:checked');
  $(checkedSubfieldBoxes).each(function(){
    var tmpArray = this.id.split('_');
    var tag = tmpArray[1], fieldNumber = tmpArray[2],
      subfieldIndex = tmpArray[3];
    if (!toDelete[tag]){
      toDelete[tag] = {};
      toDelete[tag][fieldNumber] = [subfieldIndex];
    }
    else{
      if (!toDelete[tag][fieldNumber])
	toDelete[tag][fieldNumber] = [subfieldIndex];
      else if (toDelete[tag][fieldNumber].length == 0)
	// Entire field scheduled for the deletion.
	return;
      else
	toDelete[tag][fieldNumber].push(subfieldIndex);
    }
  });

  // Assert that no protected fields are scheduled for deletion.
  var protectedField = containsProtectedField(toDelete);
  if (protectedField){
    displayAlert('alert', 'errorDeleteProtectedField', true, protectedField);
    return;
  }

  gPageDirty = true;
  // Create AJAX request.
  var data = {
    recID: gRecID,
    requestType: 'deleteSelected',
    toDelete: toDelete
  };
  createReq(data, function(json){
    updateStatus('report', json['resultText']);
  });

  /* Continue local updating.
  Parse datastructure and delete accordingly in record, then redraw
  fields that had subfields deleted. */
  var fieldNumbersToDelete, subfieldIndexesToDelete, field, subfields,
    subfieldIndex;
  for (var tag in toDelete){
    fieldNumbersToDelete = toDelete[tag];
    for (var fieldNumber in fieldNumbersToDelete){
      var fieldID = tag + '_' + fieldNumber;
      subfieldIndexesToDelete = fieldNumbersToDelete[fieldNumber];
      if (subfieldIndexesToDelete.length == 0){
	deleteFieldFromTag(tag, fieldNumber);
	$('#rowGroup_' + tag + '_' + fieldNumber).remove();
      }
      else{
	subfieldIndexesToDelete.sort();
	field = getFieldFromTag(tag, fieldNumber);
	subfields = field[0];
	for (var j=subfieldIndexesToDelete.length-1; j>=0; j--)
	  subfields.splice(subfieldIndexesToDelete[j], 1);
	var rowGroup = $('#rowGroup_' + fieldID);
	if (!deleteFields){
	  // Color subfield after updating.
	  var coloredRowGroup = $(rowGroup).hasClass('bibEditFieldColored');
	  $(rowGroup).replaceWith(createField(tag, field));
	  if (coloredRowGroup)
	    $('#rowGroup_' + fieldID).addClass( 'bibEditFieldColored');
	}
	else
	  $(rowGroup).replaceWith(createField(tag, field));
      }
    }
  }
  if (deleteFields)
    // If entire fields has been deleted, recolor the full table.
    reColorFields();
  resetNewFieldNumber();
}
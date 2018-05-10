/*
   Copyright 2018 CNIT - Consorzio Nazionale Interuniversitario per le Telecomunicazioni

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an  BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/


function showOperationDetails(url_info) {
    var dialog = bootbox.dialog({
        message: '<div class="text-center"><i class="fa fa-spin fa-spinner"></i> Loading...</div>',
        closeButton: true
    });
    $.ajax({
        url: url_info,
        type: 'GET',
        dataType: "json",
        contentType: "application/json;charset=utf-8",
        success: function (result) {
            editorJSON.setValue(JSON.stringify(result, null, "\t"));
            editorJSON.setOption("autoRefresh", true);
            dialog.modal('hide');
            $('#modal_show_operation').modal('show');
        },
        error: function (result) {
            dialog.modal('hide');
            bootbox.alert("An error occurred while retrieving the information for the NS");
        }
    });
}

var editorJSON;

$(document).ready(function () {
    var json_editor_settings = {
        mode: "javascript",
        showCursorWhenSelecting: true,
        autofocus: true,
        lineNumbers: true,
        lineWrapping: true,
        foldGutter: true,
        gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter"],
        autoCloseBrackets: true,
        matchBrackets: true,
        extraKeys: {
            "F11": function (cm) {
                cm.setOption("fullScreen", !cm.getOption("fullScreen"));
            },
            "Esc": function (cm) {
                if (cm.getOption("fullScreen")) cm.setOption("fullScreen", false);
            },
            "Ctrl-Q": function (cm) {
                cm.foldCode(cm.getCursor());
            }
        },
        theme: "neat",
        keyMap: "sublime"
    };
    var myJsonTextArea = document.getElementById("operation_view_json");
    editorJSON = CodeMirror(function (elt) {
        myJsonTextArea.parentNode.replaceChild(elt, myJsonTextArea);
    }, json_editor_settings);


});
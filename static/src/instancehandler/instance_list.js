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

function performAction(url) {
    $("#formActionNS").attr("action", url);
    $('#modal_instance_new_action').modal('show');
}

function deleteNs(url) {
    bootbox.confirm("Are you sure want to delete?", function (result) {
        if (result) {
            location.href = url
        }
    })
}

var addFormGroup = function (event) {
    event.preventDefault();

    var $formGroup = $(this).closest('.form-group');
    var $formGroupClone = $formGroup.clone();

    $(this)
        .toggleClass('btn-success btn-add btn-danger btn-remove')
        .html('–');

    $formGroupClone.find('input').val('');
    $formGroupClone.insertAfter($formGroup);

};

var removeFormGroup = function (event) {
    event.preventDefault();
    var $formGroup = $(this).closest('.form-group');
    $formGroup.remove();
};

function showInstanceDetails(url_info) {
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
            $('#modal_show_instance').modal('show');
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
    var myJsonTextArea = document.getElementById("instance_view_json");
    editorJSON = CodeMirror(function (elt) {
        myJsonTextArea.parentNode.replaceChild(elt, myJsonTextArea);
    }, json_editor_settings);


    $(document).on('click', '.btn-add', addFormGroup);
    $(document).on('click', '.btn-remove', removeFormGroup);

    $("#formActionNS").submit(function (event) {
        event.preventDefault(); //prevent default action
        var post_url = $(this).attr("action"); //get form action url
        var request_method = $(this).attr("method"); //get form GET/POST method
        var form_data = new FormData(this); //Encode form elements for submission
        console.log(post_url);
        $.ajax({
            url: post_url,
            type: request_method,
            data: form_data,
            headers: {
                "Accept": 'application/json'
            },
            contentType: false,
            processData: false
        }).done(function (response,textStatus, jqXHR) {
            $('#modal_instance_new_action').modal('hide');
            bootbox.alert({
                    title: "Action",
                    message: "Action received."
                });
        }).fail(function(result){
            var data  = result.responseJSON;
            var title = "Error " + (data.code ? data.code: 'unknown');
                var message = data.detail ? data.detail: 'No detail available.';
                bootbox.alert({
                    title: title,
                    message: message
                });
        });
    });

});
function deleteSDN(project_id, sdn_uuid) {
    bootbox.confirm("Are you sure want to delete?", function (result) {
        if (result) {
            location.href = '/projects/' + project_id + '/sdn/' + sdn_uuid + '/delete'
        }
    })
}

function showSDN(project_id, sdn_uuid) {
    var dialog = bootbox.dialog({
        message: '<div class="text-center"><i class="fa fa-spin fa-spinner"></i> Loading...</div>',
        closeButton: true
    });

    $.ajax({
        url: '/projects/' + project_id + '/sdn/' + sdn_uuid ,
        //url: '/sdn/' + sdn_uuid,
        type: 'GET',
        dataType: "json",
        contentType: "application/json;charset=utf-8",
        success: function (result) {
            //$('#modal_show_vim_body').empty();
            var sdn = result.sdn;
            if (sdn) {
                $('#modal_show_sdn_body').find('span').text('-');
                for (var k in sdn) {
                    $('#' + k).text(sdn[k])
                }
                if (sdn['_admin']) {
                    for (var i in sdn['_admin']) {
                        if (i === 'modified' || i === 'created') {
                            //$('#' + i).text(new Date(sdn['_admin'][i]* 1000).toUTCString());
                            $('#' + i).text(moment(sdn['_admin'][i] * 1000).format('DD/MM/YY hh:mm:ss'));
                        }
                        else if (i === 'deployed') {
                            $('#' + i).text(JSON.stringify(sdn['_admin'][i]))
                        }
                        else
                            $('#' + i).text(sdn['_admin'][i])
                    }
                }
                dialog.modal('hide');
                $('#modal_show_sdn').modal('show');
            }
            else {
                dialog.modal('hide');
                bootbox.alert("An error occurred while retrieving the SDN controller info.");
            }

        },
        error: function (result) {
            dialog.modal('hide');
            bootbox.alert("An error occurred while retrieving the SDN controller info.");
        }
    });

}
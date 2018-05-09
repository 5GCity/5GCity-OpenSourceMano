 function deletePackage(project_id, descriptor_type, package_id) {
            bootbox.confirm("Are you sure want to delete?", function (result) {
                if (result) {
                    location.href = '/projects/' + project_id + '/descriptors/' + descriptor_type + '/' + package_id + '/delete'
                }
            })
        }



        function openPackageContentList(project_id, type, pkg_id) {
            var dialog = bootbox.dialog({
                message: '<div class="text-center"><i class="fa fa-spin fa-spinner"></i> Loading...</div>',
                closeButton: true
            });
            $.ajax({
                url: '/projects/' + project_id + '/descriptors/' + type + '/' + pkg_id + '/action/get_package_files_list',
                type: 'GET',
                dataType: "json",
                contentType: "application/json;charset=utf-8",
                success: function (result) {
                    //$('#modal_show_vim_body').empty();
                    dialog.modal('hide');
                    build_file_list("Files in " + pkg_id, result.files);
                },
                error: function (result) {
                    dialog.modal('hide');
                    bootbox.alert("An error occurred while retrieving the package content.");
                }
            });
        }


        function build_file_list(title, list) {
            $('#files_list_tbody').find('tr:gt(0)').remove();
            $('#files_list_tbody_title').text(title)
            for (var i in list) {
                var template = '<tr><td>-</td><td>' + list[i] + '</td><td><button type="button" class="btn btn-default" onclick="" disabled><i class="fa fa-folder-open"></i></button></td></tr>'
                $('#files_list_tbody').append(template)
            }
            $('#modal_files_list').modal('show');
        }
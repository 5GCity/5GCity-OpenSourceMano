var dropZone = document.getElementById('drop-zone');
dropZone.ondrop = function (e) {
    e.preventDefault();
    this.className = 'upload-drop-zone';
    create(e.dataTransfer.files, true);
};

dropZone.ondragover = function () {
    this.className = 'upload-drop-zone drop';
    return false;
};

dropZone.ondragleave = function () {
    this.className = 'upload-drop-zone';
    return false;
};


function create(fs, dropzone) {
    var id = $('.nav-tabs .active').attr('id');
    if (dropzone) id = 'file_li';
    var type, text;
    var data = new FormData();
    switch (id) {

        case 'file_li':
            type = 'file';

            var files = dropzone ? fs : document.getElementById('js-upload-files').files;
            if (!files || !files.length) {
                files = document.getElementById('drop-zone').files;
                if (!files || !files.length) {
                    alert("Select a file");
                    return
                }
            }
            console.log(files[0])
            var patt1 = /\.([0-9a-z]+)(?:[\?#]|$)/i;
            console.log(files[0].name.match(patt1));
            var extension = files[0].name.substr(files[0].name.lastIndexOf('.') + 1);
            console.log(extension);
            if (!(extension == 'gz' )) {
                alert("The file must be .tar.gz");
                return
            }

            data.append('file', files[0]);
            break;
    }
    data.append('csrfmiddlewaretoken', csrf_token);
    data.append('type', type);
    data.append('text', text);
    data.append('id', '{{descriptor_id}}');
    console.log(text);
    $.ajax({
        url: "new",
        type: 'POST',
        data: data,
        cache: false,
        contentType: false,
        processData: false,
        success: function (result) {
            console.log(result);

            window.location.href = descr_list_url

        },
        error: function (result) {
            showAlert(result);
        }
    });
}
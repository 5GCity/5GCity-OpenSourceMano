function generateUID() {
    return ("0000" + (Math.random() * Math.pow(36, 4) << 0).toString(36)).slice(-4)
}

function openProject(pId) {
    window.location.href = '/projects/' + pId;
}


function openDescriptorView(project_id, descriptor_type, descriptor_id) {
    console.log("openDescriptorView", project_id, descriptor_type, descriptor_id);
    window.location.href = '/projects/' + project_id + '/descriptors/' + descriptor_type + '/' + descriptor_id;

}


function openEditorEvent(e, id) {
    openEditor(id);
}

function nodeDragStart(event) {
    event.dataTransfer.setData("Text", event.target.id);
}

function savePositions(el) {
    graph_editor.savePositions();
}

function buildPalette(args) {
    $("#paletteContainer").empty();
    var type_property = graph_editor.getTypeProperty();
    if (args.length > 0) {
        args.forEach(function (category) {

            var category_id = "category_" + category.category_name.replace(/[\s.*+?^${}()\/|[\]\\]/g, "_");//.replace(/\s/g, '');
            var content_id = "palette-content-" + category.category_name.replace(/[\s.*+?^${}()\/|[\]\\]/g, "_");//.replace(/\s/g, '');

            $("#paletteContainer").append('<div id="' + category_id + '" class="palette-category" ><div class="palette-header" onClick="handlePaletteCat(this);" category_id="' + category_id + '"> ' +
                '<i class="fa fa-chevron-down "></i>' +
                '<span>  ' + category.category_name + '</span>' +
                '</div>' +
                '<div id="' + content_id + '" class="palette-content">' +

                '</div>' +
                '</div>');
            category.types.forEach(function (type) {
                console.log(graph_editor.get_name_from_d3_symbol(d3.symbolCircle))
                var type_id = type.id.replace(/[\s.*+?^${}()|[\]\\]/g, "_");
                var palette_node_icon;
                if (type_property[type.id] && type_property[type.id].image && type_property[type.id].image != '') {
                    palette_node_icon = '<div class="palette-node-icon" style="background-image: url(' + (type_property[type.id].image || "") + ')"></div>';
                }
                else if (type_property[type.id] && type_property[type.id].shape) {
                    palette_node_icon = buildHtmlShape({
                        shape: type_property[type.id].shape,
                        color: type_property[type.id].color
                    });

                }
                else {//#1F77B4
                    palette_node_icon = '<div class="palette-node-icon"> <div class="palette-node-square" style="background:#1F77B4;"></div></div>';
                }

                var html_to_append = '<div class="palette-node ui-draggable" draggable="true" type-name="' + type.id + '" id="' + type_id + '" ondragstart="nodeDragStart(event)">' +
                    '<div class="palette-node-label">' + type.name + '</div>' +
                    '<div class="palette-node-icon-container">' +
                    palette_node_icon +
                    '</div>' +
                    '</div>'
                $("#" + content_id).append(html_to_append);
            });

        });
    }
    togglePaletteSpinner(true);


}

function handlePaletteCat(item) {
    console.log("handlePaletteContainer")
    var category_id = $(item).attr("category_id")
    $('#' + category_id).toggleClass("palette-close");

}

function togglePaletteSpinner(addOrRemove) {
    $('#palette').toggleClass("palette-status-hidden", addOrRemove);
}

function showAlert(msg) {
    // modal_alert_text
    var alert_msg = ""
    if (typeof msg == "string")
        alert_msg = msg
    else
        alert_msg = JSON.stringify(msg)
    $('#modal_alert_text').text(alert_msg);
    $('#modal_alert').modal('show');
}

function getUrlParameter(par_name) {
    var results = new RegExp('[\?&]' + par_name + '=([^&#]*)').exec(window.location.href);
    if (results == null) {
        return null;
    } else {
        return results[1] || 0;
    }
}

function buildHtmlShape(args) {
    var mySymbol = args.shape;
    switch (mySymbol) {
        case d3.symbolCircle:
            return '<div class="palette-node-icon"> <div class="palette-node-circle" style="background:' + args.color + ';"></div></div>';
            break;
        case d3.symbolSquare:
            return '<div class="palette-node-icon"> <div class="palette-node-square" style="background:' + args.color + ';"></div></div>';
            break;
        case d3.symbolDiamond:
            return '<div class="palette-node-icon" style="background-color:' + args.color + '"></div>';
            ;
            break;
        case d3.symbolTriangle:
            return '<div class="palette-node-icon"> <div class="palette-node-triangle" style="border-color: transparent transparent ' + args.color + ' transparent;"></div></div>';
            break;
        case d3.symbolStar:
            return '<div class="palette-node-icon" style="background-color:' + args.color + '"></div>';
            ;
            break;
        case d3.symbolCross:
            return '<div class="palette-node-icon" style="background-color:' + args.color + '"></div>';
            ;
            break;
        default:
            // if the string is not recognized
            return "unknown";
        //return d3.symbolCircleUnknown;
    }


}

if (!String.format) {
    String.format = function (format) {
        var args = Array.prototype.slice.call(arguments, 1);
        return format.replace(/{(\d+)}/g, function (match, number) {
            return typeof args[number] != 'undefined' ?
                args[number] :
                match;
        });
    };
}
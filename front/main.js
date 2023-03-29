let debug = true;

let gridapps_server = "http://192.168.1.2:8888/"; // оставляйте "/" в конце URL!
let ipcamera_server = "http://192.168.1.201:80/videostream.cgi?user=admin&amp;pwd=888888";


function getProtocolFromURL(URL) {return URL.split("//").shift();}

if( !(window.location.protocol == getProtocolFromURL(gridapps_server) == getProtocolFromURL(ipcamera_server)) ) {
    console.warn("warning: mismatched protocols");
}

let missedTrain = true;

// console.warn("parent:")
// console.warn(`window.SharedArrayBuffer: ${window.SharedArrayBuffer}`);
// console.warn(`isSecureContext: ${isSecureContext}`);
// console.warn(`crossOriginIsolated: ${crossOriginIsolated}`);

window.addEventListener('message', msg => {
    if(debug) {
        const { origin, source, target, data } = msg;
        console.warn("parent: new message:");
        console.warn(`parent: origin: ${origin}`);
        if(data.event == "init-done") {
            console.warn(`parent: data: ${JSON.stringify(data.event)}`);
        } else {
            console.warn(`parent: data: ${JSON.stringify(data)}`);
        }
    }
});

// $("body").prepend(`
//     <div style="display: flex;">
//         <img src="${ipcamera_server}" style="width: 640px; height: 360px;" width="640" vspace="0" hspace="0" height="360">
//         <img src="/mjpeg" style="width: 600px; height: 480px;">    
//     </div>
// `);

async function uploadFile() {
    filename = fileupload.files[0].name;
    extension = filename.split('.').pop();
    if(extension != "gcode") return;

    let formData = new FormData();
    formData.append("file", fileupload.files[0]);
    formData.append("target", $("#printerselect").val())
    await fetch(`${window.location.origin}/upload`, {
        method: "POST",
        body: formData
    });
}

$("#submit").click(() => {
    uploadFile();
});

function openSlicer() {
    $("body").prepend(`
        <div id="fullscreen" style="position: absolute; width: 100vw; height: 100vh;">
            <iframe allow="cross-origin-isolated" style="width:100%; height:100%;" id="kiri" src="${gridapps_server + "kiri/"}"></iframe>
        </div>
    `);
    api = kiri.frame;
    try {
        api.setFrame("kiri", "*");
        $("#kiri").on("load", () => {
            if(debug) console.log("parent: onload");
            api.on("init-done", () => {
                missedTrain = false;
                if(debug) console.log("parent: caught init-done");
                attachSlicerHandlers();
            });
            setTimeout(() => {
                // TODO: add slicer loaded check in case it
                // takes longer than 5 seconds to load
                if(missedTrain) {
                    if(debug) console.log("parent: init-done fired before subscription");
                    attachSlicerHandlers();
                }
            }, 5000);
        });
    } catch(error) {
        console.log("Error opening slicer (is grid-apps server running?)");
    }
}

$("#slicer").click(() => {
    openSlicer();
});

function attachSlicerHandlers() {
    api.on("loaded", () => {
        api.alert("Слайсер загружен успешно.", 2);
    });
    api.on("slice.end", () => {
        api.prepare();
    });
    api.on('preview.end', () => {
        // true sends export.done event
        // instead of opening export window inside slicer
        api.export(true); 
    });
    api.on('export.done', (data) => {
        api.alert("Модель успешно преобразована в gcode.", 5);
        api.alert("Теперь вы можете закрыть окно слайсера.", 5);
        console.log(data);
    });
}

async function printerSelector() {
    resp = await (await fetch(`${window.location.origin}/devices`)).json();
    for (let [key, value] of Object.entries(resp)) {
        $("#printerselect").append(`<option value="${key}">${value.name} on ${key}</option>`);
    }
}

$(document).ready(() => {
    printerSelector();
});
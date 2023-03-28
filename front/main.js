// console.warn("parent:")
// console.warn(`window.SharedArrayBuffer: ${window.SharedArrayBuffer}`);
// console.warn(`isSecureContext: ${isSecureContext}`);
// console.warn(`crossOriginIsolated: ${crossOriginIsolated}`);

let missedTrain = true;

// window.addEventListener('message', msg => {
//     const { origin, source, target, data } = msg;
//     console.warn("parent: new message:");
//     console.warn(`parent: origin: ${origin}`);
//     if(data.event == "init-done") {
//         console.warn(`parent: data: ${JSON.stringify(data.event)}`);
//     } else {
//         console.warn(`parent: data: ${JSON.stringify(data)}`);
//     }
// });

async function handleFile() {
    let formData = new FormData();           
    formData.append("file", fileupload.files[0]);
    formData.append("target", $("#printerselect").val())
    fetch(`${window.location.origin}/upload`, {
        method: "POST",
        body: formData
    }).then((response) => response.json())
    .then((responseJson) => {
        if (responseJson.uploaded) {
            filename = fileupload.files[0].name;
            extension = filename.split('.').pop();
            fullpath = window.location.href + "file/" + filename;

            if (extension == "stl" || extension == "obj") {
                console.log(`opening slicer with file ${fullpath}`);
                $("body").prepend('<div id="fullscreen" style="position: absolute; width: 100vw; height: 100vh;"><iframe allow="cross-origin-isolated" style="width:100%; height:100%;" id="kiri" src="https://192.168.1.2:8888/kiri/"></iframe></div>');
                api = kiri.frame;
                api.setFrame("kiri", "*");
                $("#kiri").on("load", () => {
                    console.log("parent: onload");
                    api.on("init-done", () => {
                        missedTrain = false;
                        console.log("parent: caught init-done");
                        initializeSlicer();
                    });
                    setTimeout(() => {
                        if(missedTrain) {
                            console.log("parent: init-done fired before subscription");
                            initializeSlicer();
                        }
                    }, 5000);
                });
            }
        } else if(responseJson.error) {
            console.log(responseJson.error);
        };
    });
}

function initializeSlicer() {
    api.alert("Загружаю 3D модель...", 2);
    api.clear();
    api.load(fullpath);
    api.on("loaded", () => {
        api.alert("Модель загружена успешно.", 2);
        api.alert("Для подготовки модели к печати измените настройки и нажмите кнопку Slice в меню Start слева.", 10);
    });
    api.on("slice.end", () => {
        api.prepare();
    });
    api.on('preview.end', () => {
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

$("#submit").click(() => {
    handleFile();
});
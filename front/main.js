async function uploadFile() {
    let formData = new FormData();           
    formData.append("file", fileupload.files[0]);
    formData.append("target", $("#printerselect").val())
    resp = await fetch(`${window.location.origin}/upload`, {
      method: "POST",
      body: formData
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
    uploadFile();
});
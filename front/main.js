async function uploadFile() {
    let formData = new FormData();           
    formData.append("file", fileupload.files[0]);
    formData.append("target", "/dev/ttyUSB0")
    resp = await fetch(`${window.location.origin}/upload`, {
      method: "POST",
      body: formData
    });    
}

$(document).ready(() => {
    let video = Cookies.get("p1video");
    if(video != undefined) {
        $("#p1camera").html(`<img src="${video}" style="width: 640px; height: 360px;" width="640" vspace="0" hspace="0" height="360">`);
    }
});

$("#spoiler").click(function(){
    $("#settings").slideToggle("slow");
});

$("#submit").click(() => {uploadFile();});

$("#apply").click(() => {
    Cookies.set("p1video", $("#p1video").val());
    $("#p1camera").html(`<img src="${$("#p1video").val()}" style="width: 640px; height: 360px;" width="640" vspace="0" hspace="0" height="360">`);
});
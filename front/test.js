let basedir = "/"
let fileExplorer = $("#fx")
let currdir = basedir
const re = /\/(?:.(?!\/))+$/
let resp;
$(".load").click(() => {
    $(".wrapper").fadeIn("slow");
    setTimeout(() => {
        $(".wrapper").fadeOut("slow");
    }, 2000);
});

async function uploadFile() {
    let formData = new FormData();           
    formData.append("file", fileupload.files[0]);
    resp = await fetch('http://127.0.0.1:5000/upload', {
      method: "POST", 
      body: formData
    });    
}

$("#submit").click(() => {uploadFile();});

$("#files").click(async () => {
    composeFileExplorer(await getFiles(), basedir);
});

async function getFiles() {
    let jsonResponse = await (await fetch("http://127.0.0.1:5000/files")).json();
    console.log(jsonResponse);
    return jsonResponse;
}

function attachHandlers(element) {
    if (element.attr("directory") !== undefined) {
        element.dblclick(async () => {
            if(currdir == "/") {
                currdir += element.attr("name");
            } else {
                currdir += "/" + element.attr("name");
            }
            composeFileExplorer(await getFiles(), currdir);
        });
    }
    element.click(() => {
        $("#fx > tr").each(function() {$(this).removeClass("highlighted");});
        element.addClass("highlighted");
    });
}

function composeFileExplorer(files, dir) {
    console.log(files);
    fileExplorer.empty()
    if(dir != "/") {
        fileExplorer.append(`<tr class="noselect" directory name="back"><td>..</td></tr>`);
        $('[name="back"]').dblclick(async () => {
            currdir = currdir.replace(re, "");
            if(currdir == "") {currdir = "/"}
            composeFileExplorer(await getFiles(), currdir);
        });
    }
    console.log("~~~~~DIRS:~~~~~");
    for (let dirs of files[dir][0]) {
        fileExplorer.append(`<tr class="noselect" directory name="${dirs}"><td>${dirs}</td></tr>`);
        // $(`[name="${dir}"]`).dblclick(() => {console.log(`opened "${dir}" directory`)});
        // $(`[name="${dir}"]`).click(() => {
        //     console.log(`selected ${dir}`);
        //     $("#fx > tr").each(function() {$(this).removeClass("highlighted")})
        //     $(`[name="${dir}"]`).addClass("highlighted");
        // });
        attachHandlers($(`[name="${dirs}"]`));
        console.log(`${dirs}`);
    }
    console.log("~~~~~FILES:~~~~~");
    for (let file of files[dir][1]) {
        fileExplorer.append(`<tr class="noselect" file name=${file}><td>${file}</td></tr>`);
        attachHandlers($(`[name="${file}"]`));
        console.log(`${file}`)
    }
}
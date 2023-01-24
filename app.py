from flask import Flask, send_from_directory, request
import os
from werkzeug.utils import secure_filename

path = "C:\\Users\\Chucky\\flask\\venv\\code\\gcodes"
front = "C:\\Users\\Chucky\\flask\\venv\\code\\front"
app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = path

@app.route("/files")
def return_files():
    output = {}
    for dir in os.walk(path):
        # output[dir[0].replace("\\", r"\ "[0])] = [dir[1], dir[2]]
        a = dir[0].replace("\\", "/")
        a = a.replace(path.replace("\\", "/"), "")
        a = "/" if a == "" else a
        output[a] = [dir[1], dir[2]]
    return output
    # return list(walk(path))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'gcode'}

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST' and 'file' in request.files and request.files['file'].filename is not "":
        # if 'file' not in request.files:
        #     print('No file part')
        file = request.files['file']
        # if file.filename == '':
        #     print('No selected file')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return {"uploaded" : filename}

@app.route("/print")
def print():
    pass

@app.route("/")
def frontend():
    return send_from_directory(front, "test.html")

@app.route('/<path:path>')
def send_report(path):
    return send_from_directory(front, path)
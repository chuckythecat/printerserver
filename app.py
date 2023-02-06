from flask import Flask, send_from_directory, request
import os
from werkzeug.utils import secure_filename

# path = "C:\\Users\\Chucky\\flask\\venv\\printerserver\\gcodes"
# front = "C:\\Users\\Chucky\\flask\\venv\\printerserver\\front"

path = "/home/pi/printerserver/upload"
front = "/home/pi/printerserver/front"

slice_extensions = {'stl', 'obj'}
print_extensions = {'gcode'}

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = path

def check_extension(filename):
    extension = '.' in filename and filename.rsplit('.', 1)[1].lower()
    if extension in slice_extensions:
        return 1
    elif extension in print_extensions:
        return 2
    return False

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

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST' and 'file' in request.files and request.files['file'].filename != "":
        # if 'file' not in request.files:
        #     print('No file part')
        file = request.files['file']
        # if file.filename == '':
        #     print('No selected file')
        if file:
            filename = secure_filename(file.filename)
            if check_extension(file.filename) == 1:
                print(f'Received {filename}, needs slicing before printing')
            elif check_extension(file.filename) == 2:
                print(f'Received {filename}, sending to {request.form.get("target")}')
                # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            elif check_extension(file.filename) == False:
                print(f'File {filename} extension is invalid')
                return {"error" : "Only .stl, .obj and .gcode files are allowed"}
        return {"uploaded" : filename}

@app.route("/")
def frontend():
    return send_from_directory(front, "index.html")

@app.route('/<path:path>')
def send_report(path):
    return send_from_directory(front, path)

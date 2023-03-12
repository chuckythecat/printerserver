from flask import Flask, send_from_directory, request, Response
import os
from werkzeug.utils import secure_filename
from printrun.printcore import printcore
from printrun import gcoder
import time
import json
import cv2
from sys import platform
if platform == "win32": exit(0)

timeout = 60

# path = "C:\\Users\\Chucky\\flask\\venv\\printerserver\\gcodes"
# front = "C:\\Users\\Chucky\\flask\\venv\\printerserver\\front"

path = "/home/pi/printerserver/upload"
front = "/home/pi/printerserver/front"

slice_extensions = {'stl', 'obj'}
print_extensions = {'gcode'}

config = json.loads(open("config1.json").read())
printers = {}
gcodes = {}

for device in os.listdir("/dev"):
    if "ttyUSB" in device and type(device) is str:
        printers["/dev/" + device] = {"name": "Unknown", "configured": False, "printcore": printcore("/dev/" + device, 115200)}

print(f"Found {len(printers.keys())} USB serial devices")


class MyHandler():
  def __init__(self, printer, cfg):
    self.printer = printer
    self.device = printer["printcore"].port
    self.cfg = cfg
    printer["printcore"].send_now("M115")

  def on_send(self, sent, b):
    self.last = sent

  def on_disconnect(self):
    pass

  def on_printsend(a, b):
    pass
  
  def on_start(a, b):
    print("started print")

  def on_end(a):
    print("ended print")

  def on_preprintsend(a, b, c, d):
    pass

  def on_recv(self, recieved):
    if not "ok" in recieved:
      print(f'{self.device}: "{recieved}"')
      if "M115" in self.last:
        detected = False
        for name, fwline in self.cfg.items():
          if fwline in recieved:
            print(f"Recognized {name} on {self.device}")
            self.printer["configured"] = True
            self.printer["name"] = name
            detected = True
            break
        if detected is False:
          print(f"{self.device} is present but not recognized. Please add device in config.json file.")
          print(f'M115: "{recieved}"')

notonline = []
allonline = False
timer = 0
while not allonline:
  allonline = True
  notonline = [] # technically this list should be empty after "if" condition below anyway, but just in case
  for printer in printers:
    if not printers[printer]["printcore"].online:
      allonline = False
      notonline.append(printer)

  if not allonline:
    offlines = ""
    timer += 5
    if timeout - timer <= 0:
      print(f"Printer(s) not responding for more than {timeout} seconds, proceeding without them")
      print(notonline)
      for offline in notonline:
        del printers[offline]
      break
    for offline in notonline.copy():
      offlines += offline
      notonline.remove(offline)
      if len(notonline) != 0:
        offlines += ", "
    print("Waiting for: " + offlines)
    time.sleep(5)

for printer in printers:
  printers[printer]["printcore"].addEventHandler(MyHandler(printers[printer], config))

cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cam.set(cv2.CAP_PROP_FPS, 15)

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = path

def check_extension(filename):
    extension = '.' in filename and filename.rsplit('.', 1)[1].lower()
    if extension in slice_extensions:
        return 1
    elif extension in print_extensions:
        return 2
    return False

def gather_img():
    while True:
        time.sleep(0.1)
        _, img = cam.read()
        _, frame = cv2.imencode('.jpg', img)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')

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

@app.route("/devices")
def report_printers():
    response = {}
    for printer, values in printers.copy().items():
        tempval = {}
        for key, value in values.items():
            if key != "printcore":
                tempval[key] = value
        response[printer] = tempval
    return response

@app.route("/mjpeg")
def mjpeg():
    return Response(gather_img(), mimetype='multipart/x-mixed-replace; boundary=frame')

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
                print(f"Received {filename}")
                filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filename)
                # gcode = [i.strip() for i in open(filename)]
                # gcode = gcoder.LightGCode(gcode)
                printer = request.form.get("target")
                gcodes[printer] = [i.strip() for i in open(filename)]
                gcodes[printer] = gcoder.LightGCode(gcodes[printer])
                print(f'Sending to {request.form.get("target")}')
                printers[printer]["printcore"].startprint(gcodes[printer])
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

app.run(host='0.0.0.0', port=80, threaded=True)

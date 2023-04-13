from flask import Flask, make_response, send_from_directory, request, Response
from flask_cors import cross_origin
import os
from werkzeug.utils import secure_filename
from printrun.printcore import printcore
from printrun import gcoder
import time
import json
import cv2
from sys import platform
if platform == "win32":
    print("Windows не поддерживается")
    exit(0)

if os.geteuid() != 0:
    print("Для запуска сервера нужны привилегии администратора. Запустите сервер при помощи команды sudo")
    exit(0)

debug = False # показывать все полученные от устройств сообщения
save_files = True # сохранение файлов (для тестирования)
send_files = True # отправка файлов на принтер (для тестирования)

timeout = 60

# models = "C:\\Users\\Chucky\\flask\\venv\\printerserver\\gcodes"
# front = "C:\\Users\\Chucky\\flask\\venv\\printerserver\\front"

cwd = os.getcwd()
models = cwd + "/upload"
front = cwd + "/front"

config = json.loads(open("config.json").read())
printers = {}
gcodes = {}

for device in os.listdir("/dev"):
    if "ttyUSB" in device or "ttyACM" in device and type(device) is str:
        printers["/dev/" + device] = {"name": "Unknown", "configured": False, "printcore": printcore("/dev/" + device, 115200)}

print(f"Найдено {len(printers.keys())} USB устройств с последовательным портом")


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
    print("Начал печатать")

  def on_end(a):
    print("Печать закончена")

  def on_preprintsend(a, b, c, d):
    pass
  
  def on_error(self, err):
    print("Ошибка!")

  def on_temp(self):
    pass

  def on_online(self):
    pass

  def on_recv(self, recieved):
    if not "ok" in recieved:
      if debug: print(f'{self.device}: "{recieved}"')
      if "M115" in self.last and not "Cap" in recieved:
        detected = False
        for name, fwline in self.cfg.items():
          if fwline in recieved:
            print(f"Опознан {name} на {self.device}")
            self.printer["configured"] = True
            self.printer["name"] = name
            detected = True
            break
        if detected is False:
          print(f"{self.device} найден но не опознан. Пожалуйста добавьте информацию об устройстве в конфигурационный файл config.json")
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
      print(f"Устройство(а) не отвечают больше {timeout} секунд, запускаю сервер без них")
      print(notonline)
      for offline in notonline:
        del printers[offline]
      break
    for offline in notonline.copy():
      offlines += offline
      notonline.remove(offline)
      if len(notonline) != 0:
        offlines += ", "
    print("Ожидание устройств(а): " + offlines)
    time.sleep(5)

for printer in printers:
  printers[printer]["printcore"].addEventHandler(MyHandler(printers[printer], config))

cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cam.set(cv2.CAP_PROP_FPS, 15)

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = models

def return_extension(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower()

def gather_img():
    while True:
        time.sleep(0.1)
        _, img = cam.read()
        _, frame = cv2.imencode('.jpg', img)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')

@app.route("/files")
def return_files():
    output = {}
    for dir in os.walk(models):
        # output[dir[0].replace("\\", r"\ "[0])] = [dir[1], dir[2]]
        a = dir[0].replace("\\", "/")
        a = a.replace(models.replace("\\", "/"), "")
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

# TODO: mjpeg repeater from IP camera:
# /mjpeg?camera=1 - USB camera
# /mjpeg?camera=2 - repeater from IP camera to frontend
@app.route("/mjpeg")
def mjpeg():
    return Response(gather_img(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST' and 'file' in request.files and request.files['file'].filename != "":
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)

            print(f"Получен файл {filename}")
            
            filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            extension = return_extension(file.filename)
            
            if extension == "gcode":
                printer = request.form.get("target")

                if printer in printers:
                    if save_files: file.save(filename)

                    gcodes[printer] = [i.strip() for i in open(filename)]
                    gcodes[printer] = gcoder.LightGCode(gcodes[printer])
                    
                    print(f'Отправляю на {printer}')
                    if send_files: printers[printer]["printcore"].startprint(gcodes[printer])
                else:
                   print(f"Файла устройства {printer} не существует")
                   return {"error" : "Файла устройства не существует"}
            elif extension == "obj" or extension == "stl":
                print(f'Модели должны быть сконвертированы перед загрузкой')
                return {"error" : "Сконвертируйте модель в gcode с помощью слайсера перед загрузкой"}
            else:
                print(f'Расширение файла не подходит')
                return {"error" : "Разрешены только файлы gcode"}
        return {"uploaded" : file.filename}

@app.route("/")
def frontend():
    resp = make_response(send_from_directory(front, "index.html"))
    resp.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
    resp.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    # resp.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
    return resp

# @app.route('/file/<path:path>', methods=['GET', 'OPTIONS'])
# def send_model(path):
#     print(request.headers)
#     if request.method == "OPTIONS": # CORS preflight
#         resp = make_response()
#         try:
#             resp.headers.add("Access-Control-Allow-Origin", request.headers['Origin'])
#             resp.headers.add('Access-Control-Allow-Headers', request.headers['Access-Control-Request-Headers'])
#             resp.headers.add('Access-Control-Allow-Methods', request.headers['Access-Control-Request-Method'])
#             resp.headers.add('Access-Control-Allow-Credentials', "true")
#         except KeyError:
#             pass
#     elif request.method == "GET": # The actual request following the preflight
#         try:
#             resp = make_response(send_from_directory(models, path))
#             resp.headers.add("Access-Control-Allow-Origin", request.headers['Origin'])
#             resp.headers.add('Access-Control-Allow-Credentials', "true")
#         except KeyError:
#             pass
#     return resp

@app.route('/<path:path>')
def send_front(path):
    resp = make_response(send_from_directory(front, path))
    resp.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
    return resp

# workaround: /code/frame.js on grid-apps server tries
# to load /src/main/gapp.js and /src/kiri-run/frame.js
# from this server instead of grid-apps server for some reason
@app.route("/src/main/gapp.js")
def main_gapp():
   return send_from_directory(front, "gapp.js")

@app.route("/src/kiri-run/frame.js")
def kiri_run_frame():
   return send_from_directory(front, "frame.js")

# app.run(host='0.0.0.0', port=1111, threaded=True, ssl_context=('cert.pem', 'key.pem'))

# http
app.run(host='0.0.0.0', port=80, threaded=True)
# https
# app.run(host='0.0.0.0', port=443, threaded=True, ssl_context=('cert.pem', 'key.pem'))

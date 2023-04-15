from flask import Flask, make_response, send_from_directory, request, Response
from flask_cors import cross_origin
import os
import signal
import subprocess as subpr
from werkzeug.utils import secure_filename
from printrun.printcore import printcore
from printrun.eventhandler import PrinterEventHandler
from printrun import gcoder
import logging
import time
import json
import cv2
from sys import platform
if platform == "win32":
	print("Windows не поддерживается")
	exit(0)

if os.geteuid() != 0:
	print("Для запуска сервера нужны привилегии администратора. \
				Запустите сервер при помощи команды sudo")
	exit(0)

# True - https, False - http
secure = True

# Записывать видео с камеры, даже когда устройство не занимается работой
alwaysrecord = False

# Имя конфигурационного файла
configfile = "config.json"

# TODO: start new log every day
# Настройки ведения журнала
logfile = "printerserver.log" # Имя файла журнала
dateformat = "%d-%m-%Y_%H:%M:%S" # Формат даты сообщений в журнале
# (также влияет на формат даты файлов видеофиксации)
loglevel = logging.INFO # Минимальный уровень важности сообщений
# Возможные значения: DEBUG, INFO, WARNING, ERROR, CRITICAL
# Все сообщения с уровнем важности правее
# от выставленного также попадают в журнал
# Например: Если выставлен уровень INFO, все сообщения уровня
# WARNING, ERROR и CRITICAL также будут записываться в журнал

debug = False # показывать все полученные от устройств сообщения
save_files = True # сохранение файлов (для тестирования)
send_files = True # отправка файлов на принтер (для тестирования)

timeout = 60

# models = "C:\\Users\\Chucky\\flask\\venv\\printerserver\\gcodes"
# front = "C:\\Users\\Chucky\\flask\\venv\\printerserver\\front"

log = logging.getLogger(__name__)
log.propagate = False
log.setLevel(loglevel)
loghandler = logging.FileHandler(filename = logfile, encoding = 'utf-8')
logformatter = logging.Formatter(fmt = '%(asctime)s %(levelname)-8s %(message)s',
																	datefmt = dateformat)
loghandler.setFormatter(logformatter)
log.addHandler(loghandler)

log.info("Начало работы сервера")

cwd = os.getcwd()
models = cwd + "/upload"
front = cwd + "/front"

try:
	config = json.loads(open(configfile).read())
except:
	err = f"Конфигурационный файл {configfile} не может быть загружен!"
	print(err)
	log.critical(err)
	exit(0)

printers = {}
gcodes = {}

class DeviceHandler(PrinterEventHandler):
	def __init__(self, printer, cfg):
		self.printer = printer
		self.devicepath = printer["printcore"].port
		self.devicename = self.devicepath.replace("/dev/", "")
		self.cfg = cfg
		self.name = "Unknown"
		self.last = None
		self.fatalerror = False
		self.ffmpeg = None
		log.debug(f"Обработчик событий для устройства {self.devicepath} был успешно добавлен")

	def on_send(self, command, gline):
		self.last = command
		log.debug(f'Команда "{command}" послана устройству "{self.devicepath}"')

	def on_online(self):
		log.info(f"{self.devicepath} онлайн")
		self.printer["printcore"].send_now("M115")

	def on_start(self, resume):
		if(resume): 
			print("Печать возобновлена")
			log.info(f"Устройство {self.devicepath} возобновило печать")
		else: 
			print("Начал печатать")
			log.info(f"Устройство {self.devicepath} начало печать")
			if(self.printer["configured"] and self.printer["camera"] != "None"):
				camtype = self.cfg[self.name]["CamType"]
				if(camtype == "Network"): device = self.printer["camera"]
				# ffmpeg can't record from /dev/video directly if camera is being
				# streamed to frontend
				elif(camtype == "USB"): device = ("https" if secure else "http") + "://localhost" + self.printer["camera"]
				# TODO: different devices can take same devicename between server reboots
				# recordings from different devices' cameras can end up in same directory
				ffmpeg = f'ffmpeg -i {device} -loglevel error -framerate 1 -strftime 1 "{cwd}/{self.devicename}/{dateformat}.jpg"'
				print(device)
				print(ffmpeg)
				# TODO: output stderr to subpr.PIPE and log ffmpeg errors to logger
				self.ffmpeg = subpr.Popen(ffmpeg, shell=True, preexec_fn=os.setsid, stdout=subpr.DEVNULL)


	def on_end(self):
		print("Печать закончена")
		log.info(f"Устройство {self.devicepath} закончило печать")
		if(self.ffmpeg):
			os.killpg(os.getpgid(self.ffmpeg.pid), signal.SIGTERM)
			self.ffmpeg = None
	
	def on_error(self, error):
		# if("M999" in error): 
		# 	self.fatalerror = True
		# 	print(f"Критическая ошибка! Устройство {self.devicepath} не может продолжить работу!")
		#	log.critical(f"Устройство {self.devicepath} не может продолжить работу ввиду критической ошибки!")
		#	log.critical(error)
		print(f"Ошибка устройства {self.devicepath}: {error}")
		log.error(f"{self.devicepath}: {error}")

	def on_recv(self, recieved):
		if not "ok" in recieved:
			# if debug: print(f'{self.devicepath}: "{recieved}"')
			log.debug(f'{self.devicepath}: "{recieved}"')
			if not self.fatalerror and "FIRMWARE_NAME:" in recieved and not "Cap" in recieved:
				detected = False
				for name, settings in self.cfg.items():
					if settings["UUID"] in recieved:
						found = f"Опознан {name} на {self.devicepath}"
						print(found)
						log.info(found)
						self.printer["configured"] = True
						self.printer["name"] = name
						self.name = name
						if(not "CamType" in settings): self.cfg[name]["CamType"] = "None"
						if(settings["CamType"] == "None"):
							self.printer["camera"] = "None"
						elif(settings["CamType"] == "USB"):
							self.printer["camera"] = "/video?device=" + self.devicename
							self.cameradevice = settings["CamPath"]
							self.printer["cam"] = cv2.VideoCapture(int(self.cameradevice.split("video")[1]))
							self.printer["cam"].set(cv2.CAP_PROP_FRAME_WIDTH, int(settings["CamWidth"]))
							self.printer["cam"].set(cv2.CAP_PROP_FRAME_HEIGHT, int(settings["CamHeight"]))
							self.printer["cam"].set(cv2.CAP_PROP_FPS, int(settings["CamFPS"]))
						elif(settings["CamType"] == "Network"):
							self.printer["camera"] = settings["CamPath"]
						detected = True
						break
				if detected is False:
					log.error(f"{self.devicepath} найден но не сконфигурирован в файле {configfile}")
					print(f"{self.devicepath} найден но не опознан. \
					Пожалуйста добавьте информацию об устройстве в конфигурационный файл config.json")
					print(f'M115: "{recieved}"')

for device in os.listdir("/dev"):
	if "ttyUSB" in device or "ttyACM" in device:
		fulldevice = "/dev/" + device
		core = printcore(fulldevice, 115200)
		printers[fulldevice] = {"name": "Unknown", "configured": False, "printcore": core}
		core.addEventHandler(DeviceHandler(printers[fulldevice], config))


print(f"Найдено {len(printers.keys())} USB устройств с последовательным портом")


# TODO: rewrite waiting for device logic
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

# for printer in printers:
#   printers[printer]["printcore"].addEventHandler(DeviceHandler(printers[printer], config))

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = models

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
			if key != "printcore" and key != "cam":
				tempval[key] = value
		response[printer] = tempval
	return response

# TODO: mjpeg repeater from IP camera
def gather_img(cam):
	while True:
		time.sleep(0.1)
		_, img = cam.read()
		_, frame = cv2.imencode('.jpg', img)
		yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')

@app.route("/video")
def mjpeg():
	camera = printers["/dev/" + request.args.get("device")]["cam"]
	return Response(gather_img(camera), mimetype = 'multipart/x-mixed-replace; boundary=frame')

def return_extension(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower()

@app.route('/upload', methods = ['GET', 'POST'])
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
					log.info(f"Файл {filename} отправлен на {printer}")
					if send_files: printers[printer]["printcore"].startprint(gcodes[printer])
				else:
					print(f"Файла устройства {printer} не существует")
					log.error(f"Получен файл {filename}, но устройства {printer}")
					return {"error" : "Файла устройства не существует"}
			elif extension == "obj" or extension == "stl":
					print(f'Модели должны быть сконвертированы перед загрузкой')
					log.error(f"Получен ненарезанный файл 3D модели {filename}")
					return {"error" : "Сконвертируйте модель в gcode с помощью слайсера перед загрузкой"}
			else:
					print(f'Расширение файла не подходит')
					log.error(f"Получен файл {filename} недопустимого расширения")
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

if(secure): app.run(host = '0.0.0.0', port = 443, threaded = True, ssl_context = ('cert.pem', 'key.pem'))
else: app.run(host = '0.0.0.0', port = 80, threaded = True)

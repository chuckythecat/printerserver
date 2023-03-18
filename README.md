# printerserver
Протестировано на Raspberry Pi 3 Model B+, Raspbian 11 bullseye, ядро Linux 5.15.84-v7+
# Зависимости:
### Python:
Flask (протестировано на версии 2.2.2):
https://flask.palletsprojects.com/en/2.2.x/installation/

### JavaScript:
jQuery (протестировано на версии 3.6.3):
https://jquery.com/download/

~~JavaScript Cookie (протестировано на версии 3.0.1):~~
~~https://github.com/js-cookie/js-cookie/~~
пока не используется

# Конфигурация:
В файл `config.json` вносятся данные об устройстве в формате:
```json
{
    "название устройства": "ответ устройства на команду M115 (если устройство имеет читаемое название или UUID то всю строку вставлять не обязательно)",
    ...
}
```

например:
```json
{
    "EasyThreed Nano": "UUID:00000000-0000-0000-0000-000000000000",
    "Blue": "FIRMWARE_NAME:Marlin V1; Sprinter/grbl mashup for gen6 FIRMWARE_URL:http://www.mendel-parts.com PROTOCOL_VERSION:1.0 MACHINE_TYPE:Mendel EXTRUDER_COUNT:1"
}
```
(3D принтер EasyThreed Nano имеет сконфигурированный в прошивке UUID, поэтому всю строку ответа на [M115](https://marlinfw.org/docs/gcode/M115.html) не обязательно вставлять в конфигурационный файл)

Если устройство использует прошивку [Marlin](https://marlinfw.org/) (проверить это можно командой [M115](https://marlinfw.org/docs/gcode/M115.html), устройство должно ответить "FIRMWARE_NAME:имя прошивки"), и у вас есть исходный код прошивки для вашего устройства, то название и UUID устройства можно изменить в конфигурационном файле `Configuration.h`: https://marlinfw.org/docs/configuration/configuration.html#custom-machine-name
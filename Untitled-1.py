# C:.
# gcodes
# │   benchy.gcode
# │   keyboard.gcode
# ├───1
# │   │   1.gcode
# │   └───2
# │       │   2.gcode
# │       └───3
# │               3.gcode
# └───keyboard
#         case.gcode
#         plate.gcode

out = {"gcodes":[
        "benchy.gcode",
        "keyboard.gcode",
        {"1":["1.gcode",
                {"2": ["2.gcode", 
                        {"3":["3.gcode", {}]
                        }]
                }]
        }]
}

a = [
    ('C:\\Users\\Chucky\\flask\\venv\\gcodes', ['1', 'keyboard'], ['benchy.gcode', 'keyboard.gcode']),
    ('C:\\Users\\Chucky\\flask\\venv\\gcodes\\1', ['2'], ['1.gcode']),
    ('C:\\Users\\Chucky\\flask\\venv\\gcodes\\1\\2', ['3'], ['2.gcode']),
    ('C:\\Users\\Chucky\\flask\\venv\\gcodes\\1\\2\\3', [], ['3.gcode']),
    ('C:\\Users\\Chucky\\flask\\venv\\gcodes\\keyboard', [], ['case.gcode', 'plate.gcode'])
    ]

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, TextBox
import serial
from time import sleep
import json

ser = serial.Serial('/dev/cu.usbserial-142210', 115200)
sleep(2)

fig, ax = plt.subplots()
plt.subplots_adjust(bottom=0.2)

plt.xlabel("travel, mm")
plt.ylabel("weight, g")
plt.grid(color='green', linestyle='--', linewidth=0.5)

down_plt, = plt.plot([0, 4], [10, 110], lw=1)
up_plt, = plt.plot([0, 4], [0, 100], lw=1)
pressed_plt, = plt.plot(2, 60, '.', color='blue')
release_plt, = plt.plot(2, 50, '.', color='red')

STEPS_PER_MM = 640.0


def up(event):
    ser.write(b'm-3200')
    print(ser.readline())


def down(event):
    ser.write(b'm3200')
    print(ser.readline())


def tare(event):
    ser.write(b't')
    print(ser.readline())


def get_close(event):
    ser.write(b'z')
    print(ser.readline())


class Index:
    ind = 0
    export_data = {'x': 1}

    def save(self, event):
        print('saving')
        plt.savefig('results/' + name_box.text + '.png', dpi=300, format='png')
        with open('results/' + name_box.text + '.json', 'w+') as f:
            f.write(json.dumps(self.export_data))

    def measure(self, event):
        ser.write(b't')
        print(ser.readline())
        ser.write(b'z')
        print(ser.readline())
        ser.write(b't')
        print(ser.readline())
        ser.write(b'p')
        down_data_x, down_data_y, up_data_x, up_data_y = [], [], [], []
        press_point, release_point = (0, 0), (0, 0)
        while True:
            c = ser.readline()
            print(c)
            if chr(c[0]) == 'p':  # plot
                break
            values = c[1:].split(b':')
            x = int(values[0]) / STEPS_PER_MM
            y = float(values[1])
            if chr(c[0]) == 'P':  # pressed
                press_point = (x, y)
                print('press_point', press_point)
                continue
            if chr(c[0]) == 'R':  # released
                release_point = (x, y)
                print('release_point', release_point)
                continue
            if y > 1:
                if chr(c[0]) == 'd':
                    down_data_x.append(x)
                    down_data_y.append(y)
                if chr(c[0]) == 'u':
                    up_data_x.append(x)
                    up_data_y.append(y)

            down_plt.set_xdata(down_data_x)
            down_plt.set_ydata(down_data_y)
            up_plt.set_xdata(up_data_x)
            up_plt.set_ydata(up_data_y)
            fig.canvas.draw()

        down_plt.set_xdata(down_data_x)
        down_plt.set_ydata(down_data_y)
        up_plt.set_xdata(up_data_x)
        up_plt.set_ydata(up_data_y)
        pressed_plt.set_xdata(press_point[0])
        pressed_plt.set_ydata(press_point[1])
        release_plt.set_xdata(release_point[0])
        release_plt.set_ydata(release_point[1])
        plt.annotate(str(press_point[0]) + 'mm, ' + str(press_point[1]) + 'g', (press_point[0], press_point[1] + 10))
        plt.annotate(str(release_point[0]) + 'mm, ' + str(release_point[1]) + 'g',
                     (release_point[0], release_point[1] - 10))
        plt.draw()
        ser.write(b'm-3200')
        print(ser.readline())

        self.export_data = {'down_x': down_data_x, 'down_y': down_data_y, 'up_x': down_data_x, 'up_y': up_data_y,
                            'press_point': press_point, 'release_point': release_point}


callback = Index()

up_ax = plt.axes([0.66, 0.01, 0.1, 0.075])
up_button = Button(up_ax, 'Up')
up_button.on_clicked(up)

down_ax = plt.axes([0.55, 0.01, 0.1, 0.075])
down_button = Button(down_ax, 'Down')
down_button.on_clicked(down)

measure_ax = plt.axes([0.44, 0.01, 0.1, 0.075])
measure_button = Button(measure_ax, 'Measure')
measure_button.on_clicked(callback.measure)

save_ax = plt.axes([0.33, 0.01, 0.1, 0.075])
save_button = Button(save_ax, 'Save')
save_button.on_clicked(callback.save)

tare_ax = plt.axes([0.77, 0.01, 0.1, 0.075])
tare_button = Button(tare_ax, 'Tare')
tare_button.on_clicked(tare)

reset_ax = plt.axes([0.88, 0.01, 0.1, 0.075])
reset_button = Button(reset_ax, 'reset')
reset_button.on_clicked(get_close)

name_ax = plt.axes([0.05, 0.01, 0.27, 0.075])
name_box = TextBox(name_ax, '', 'name')

plt.show()

ser.close()

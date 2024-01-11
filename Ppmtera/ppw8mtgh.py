#!/usr/bin/env python3

from gpiozero import Button, LED, Buzzer, DistanceSensor, MotionSensor
from gpiozero.pins.pigpio import PiGPIOFactory
from signal import pause
import threading
import time
import requests
import smbus
from time import sleep
import json
import jwt
import base64

mic_pin = 21
led_m_pin = 18
led_d_pin = 17
led_b_pin = 22
bz_d_pin = 27
ds_echo = 24
ds_trigger = 23
pir_pin = 13
btn_o_pin =19
btn_i_pin = 16
m_counter = 0
i_button_counter = 0

LINE_NOTIFY_TOKEN = "Lineのトークンを入力" #Need to delete info

project_id = "GCPで確認して入力"
topic_id = "GCPで確認して入力"

pubsub_endpoint = f"https://pubsub.googleapis.com/v1/GCPで確認して入力:publish"

service_account_key = { #Need to delete info
	"type": "JSONファイルから転記",
	"project_id": "JSONファイルから転記",
	"private_key_id": "JSONファイルから転記",
	"private_key": "JSONファイルから転記",
	"client_email": "JSONファイルから転記",
	"client_id": "JSONファイルから転記",
	"auth_uri": "JSONファイルから転記",
	"token_uri": "JSONファイルから転記",
	"auth_provider_x509_cert_url": "JSONファイルから転記",
	"client_x509_cert_url": "JSONファイルから転記",
	"universe_domain": "JSONファイルから転記"
}

def publish_to_pubsub(data):
	expiration_time = int(time.time()) + 3600

	jwt_payload = {
		"iss": service_account_key["client_email"],
		"sub": service_account_key["client_email"],
		"aud": "https://pubsub.googleapis.com/google.pubsub.v1.Publisher",
		"iat": int(time.time()),
		"exp": expiration_time,
	}
	jwt_token = jwt.encode(jwt_payload, service_account_key["private_key"], algorithm="RS256")

	headers = {

		"Authorization": f"Bearer {jwt_token}",
		"Content-Type": "application/json",
	}

	base64_data = base64.b64encode(data.encode()).decode()

	message_data = {
		"messages": [
			{
			"data": base64_data,
			}
		]
	}

	response = requests.post(pubsub_endpoint, headers=headers, data=json.dumps(message_data))

	if response.status_code == 200:
		print ("メッセージが正常に送信されました。")
	else:
		print (f"エラーコード: {response.status_code}")
		print (response.text)

#Adding the code of LCD from here

def delay(time):
	sleep(time/1000.0)

def delayMicroseconds(time):
	sleep(time/1000000.0)

class Screen():

	enable_mask = 1<<2
	rw_mask = 1<<1
	rs_mask = 1<<0
	backlight_mask = 1<<3

	data_mask = 0x00

	def __init__(self, cols = 16, rows = 2, addr=0x27, bus=1):
		self.cols = cols
		self.rows = rows
		self.bus_num = bus
		self.bus = smbus.SMBus(self.bus_num)
		self.addr = addr
		self.display_init()

	def enable_backlight(self):
		self.data_mask = self.data_mask|self.backlight_mask

	def disable_backlight(self):
		self.data_mask = self.data_mask & ~self.backlight_mask

	def display_data(self, *args):
		self.clear()
		for line, arg in enumerate(args):
			lines = arg.split('\n')
			for i, line_text in enumerate(lines):
				if line + i < self.rows:
					self.cursorTo(line + i, 0)
					self.println(line_text[:self.cols].ljust(self.cols))

	def cursorTo(self, row, col):
		offsets = [0x00, 0x40, 0x14, 0x54]
		self.command(0x80|(offsets[row]+col))

	def clear(self):
		self.command(0x10)

	def println(self, line):
		for char in line:
			self.print_char(char)

	def print_char(self, char):
		char_code = ord(char)
		self.send(char_code, self.rs_mask)

	def display_init(self):
		delay(1.0)
		self.write4bits(0x30)
		delay(4.5)
		self.write4bits(0x30)
		delay(4.5)
		self.write4bits(0x30)
		delay(0.15)
		self.write4bits(0x20)
		self.command(0x20|0x08)
		self.command(0x04|0x08, delay=80.0)
		self.clear()
		self.command(0x04|0x02)
		delay(3)

	def command(self, value, delay = 50.0):
		self.send(value, 0)
		delayMicroseconds(delay)

	def send(self, data, mode):
		self.write4bits((data & 0xF0)|mode)
		self.write4bits((data << 4)|mode)

	def write4bits(self, value):
		value = value & ~self.enable_mask
		self.expanderWrite(value)
		self.expanderWrite(value | self.enable_mask)
		self.expanderWrite(value)

	def expanderWrite(self, data):
		self.bus.write_byte_data(self.addr, 0, data|self.data_mask)

#added new code for LCD by here


def main():
	factory = PiGPIOFactory()
	snsr = Button(mic_pin, pin_factory=factory)
	led_mic = LED(led_m_pin, pin_factory=factory)
	led_pir = LED(led_d_pin, pin_factory=factory)
	led_btn = LED(led_b_pin, pin_factory=factory)
	pir_sensor = MotionSensor(pir_pin, pin_factory=factory)
	buzzer = Buzzer(bz_d_pin, pin_factory=factory)
	o_button = Button(btn_o_pin, pin_factory=factory)
	distance_sensor = DistanceSensor(echo=ds_echo, trigger=ds_trigger, pin_factory=factory)
	i_button = Button(btn_i_pin, pin_factory=factory)
	screen = Screen(bus=1, addr=0x27, cols=16, rows=2)
	screen.enable_backlight()
	screen.display_data("Start working!! \nSystem working!!")

	def press_btn():
		global m_counter
		m_counter += 1

	def display_count():
		global m_counter
		while True:
			time.sleep(5.0)
			if m_counter >= 5000:
				led_mic.blink(on_time=0.5, off_time=0.5, n=5)
			print (f"音_5秒で閾値越えの数: {m_counter}")
			m_counter = 0 #reset count

	def send_line_notification():
		url = "https://notify-api.line.me/api/notify"
		headers = {
			"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"
		}
		payload = {
#			"message": "5秒毎の閾値が5000を超えました"
			"message": "誰かが室内に入りました"
		}
		response = requests.post(url, headers=headers, data=payload)
		print ("LED点滅、LINE Notifyの応答:", response.text)

	def check_distance():
		while True:
			time.sleep(1.0)
			distance = distance_sensor.distance

			limited_distance_str = "{:.6f}".format(distance)[:10]
			limited_distance = float(limited_distance_str)

			print (f"距離_1秒ごと: {distance:.2f} m")
			if distance < 0.8:
				buzzer.on()
			else:
				buzzer.off()

			publish_to_pubsub(str(limited_distance))

	def pir_triggered():
		print ("PIR_入室者あり!!")
		led_pir.blink(on_time=0.5, off_time=0.5, n=5)
		send_line_notification()
		time.sleep(5.0)

	def button_o_pressed():
		led_btn.blink(on_time=0.5, off_time=0.5, n=5)
		time.sleep(5.0)

	def button_i_pressed():
		global i_button_counter
		i_button_counter += 1
		if i_button_counter <= 3:
			messages = ["!!Meeting now!!\nDont open door!", "!!Do task now!!\nPush button soft", "Rest now(*_*)zzz\nDont push button"]
			screen.display_data(messages[i_button_counter -1])
		else:
			screen.display_data("No task now(^^)/\nCan open door")
			i_button_counter = 0


	snsr.when_pressed = press_btn
	o_button.when_pressed = button_o_pressed
	i_button.when_pressed = button_i_pressed

	accumulate_thread = threading.Thread(target=display_count)
	accumulate_thread.start()

	distance_thread = threading.Thread(target=check_distance)
	distance_thread.start()

	pir_sensor.when_motion = pir_triggered

	pause()

if __name__ == '__main__':
	main()


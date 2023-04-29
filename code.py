import board, neopixel
import time, rtc
import time, rtc
import digitalio

import os, ssl, wifi, socketpool, json, adafruit_requests

from audiopwmio import PWMAudioOut as AudioOut
from audiocore import WaveFile
from adafruit_debouncer import Button
import adafruit_displayio_ssd1306
import terminalio
import busio, displayio
from adafruit_display_text import label


# function adapted from https://learn.adafruit.com/generating-text-with-chatgpt-pico-w-circuitpython/coding-the-text-generator
def get_joke():
    with requests.post("https://api.openai.com/v1/chat/completions",
                       json={"model": "gpt-3.5-turbo", "messages": full_prompt, "stream": True},
                       headers={"Authorization": f"Bearer {openai_api_key}",},) as response:
        joke = ""
        for line in iter_lines(response):
            if line.startswith("data: [DONE]"):
                break
            if line.startswith("data: "):
                content = json.loads(line[5:])
                try:
                    token = content['choices'][0]['delta'].get('content','')
                except (KeyError, IndexError) as e:
                    token = None

                if token:
                    joke += token

        joke = joke.replace("\n", "")
    return joke

def get_joke_wrap():
    show_text("Thinking...")
    joke = get_joke()
    while joke in joke_bank:
        joke = get_joke()

    joke_bank.append(joke)
    part1, part2 = "", ""
    part1, part2 = split_string(joke)

    show_text(part1)
    time.sleep(4)
    show_text(part2)
    time.sleep(4)

# function adapted from https://learn.adafruit.com/generating-text-with-chatgpt-pico-w-circuitpython/coding-the-text-generator
def iter_lines(resp):  # helper function for getting the text out of the response from gpt
    partial_line = []
    for c in resp.iter_content():
        if c == b'\n':
            yield (b"".join(partial_line)).decode('utf-8')
            del partial_line[:]
        else:
            partial_line.append(c)
    if partial_line:
        yield (b"".join(partial_line)).decode('utf-8')

# Split a joke into two strings to fit on screen
def split_string(joke):
    str1, str2 = "", ""
    s1_count, s2_count = 0, 0
    pt2 = False
    for i, c in enumerate(joke): #split into two parts
        if pt2:
            s2_count += 1
            if s2_count == 20:
                str2 += "\n"
            str2 += c

        else:
            s1_count += 1
            if s1_count == 20:
                str1 += "\n"
            str1 += c

        if c == "?":
            pt2 = True

    return str1, str2

# set up the display
def display_init():
    line_spacing = 9 # in pixels

    displayio.release_displays()
    oled_reset = board.GP9
    i2c = board.STEMMA_I2C()
    display_bus = displayio.I2CDisplay(i2c, device_address=0x3C, reset=oled_reset)

    WIDTH = 128
    HEIGHT = 64

    display = adafruit_displayio_ssd1306.SSD1306(
        display_bus, width=WIDTH, height=HEIGHT
    )
    display.auto_refresh = False
    return display

def get_time():
    url = "https://worldtimeapi.org/api/timezone/America/New_York"
    response = requests.get(url)
    json = response.json()

    unixtime = json["unixtime"]
    raw_offset = json['raw_offset']

    location_time = unixtime + raw_offset
    current_time = time.localtime(location_time)
    return current_time

# Show the text on screen in smaller font
def show_text(text):
    text_area = label.Label(terminalio.FONT, text=text, scale=1)
    text_area.x = 0
    text_area.y = 40
    display.show(text_area)
    display.refresh()

# Show the time on screen in bigger font
def show_time(clock):
    text = ""
    if (clock.datetime.tm_hour + 1) % 12 in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
        text += "0"
    text += str(clock.datetime.tm_hour % 12 + 1)
    text += ":"
    if clock.datetime.tm_min in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
        text += "0"
    text += str(clock.datetime.tm_min)
    #text = str(clock.datetime.tm_hour % 12 + 1) + ":" + str(clock.datetime.tm_min)
    text_area = label.Label(terminalio.FONT, text=text, scale=4)
    text_area.x = 7
    text_area.y = 32
    display.show(text_area)
    display.refresh()
    return text

def play_sound(filename, button):
    with open(path + filename, "rb") as wave_file:
        wave = WaveFile(wave_file)
        audio.play(wave)
        while audio.playing:
            button.update()
            if button.pressed:
                pixels.fill((0, 0, 0)) # turn lights off
                return

            pixels.fill((255, 0, 0))
            pixels.brightness = 0
            for i in range(101): # pulse lights
                pixels.brightness = i/100

        play_sound(filename, button) # keep playing audio until button pressed

mac_address = [f"{i:02x}" for i in wifi.radio.mac_address]
print(':'.join(mac_address))

# set up the display
display = display_init()

# set up buttons
button_input_A = digitalio.DigitalInOut(board.GP15) # Wired to GP15
button_input_A.switch_to_input(digitalio.Pull.UP) # Note: Pull.UP for external buttons
button_A = Button(button_input_A) # NOTE: False for external buttons
button_input_B = digitalio.DigitalInOut(board.GP14) # Wired to GP16
button_input_B.switch_to_input(digitalio.Pull.UP) # Note: Pull.UP for external buttons
button_B = Button(button_input_B) # NOTE: False for external buttons

# set up the speaker
audio = AudioOut(board.GP16)
path = "sounds/"

# set up the lights
pixels = neopixel.NeoPixel(board.GP19, 60, brightness = 0.5)

# set up WiFi
wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD"))
print("Connected to WIFI")
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# set up stuff for Chat GPT interface
prompt = os.getenv("MY_PROMPT").strip()
full_prompt = [{"role": "user", "content": prompt},]
openai_api_key = os.getenv("OPENAI_API_KEY")

# set the internal clock on the Pico
current_time = get_time()
clock = rtc.RTC()
clock.datetime = time.struct_time(current_time)


show_time(clock)
joke_bank = []
ALARM = "12:29" # set your desired alarm time here
first_alarm = True
while True:
    time_str = show_time(clock)
    if time_str == ALARM and first_alarm:
        play_sound("siren.wav", button_A)
        first_alarm = False # make sure alarm only goes off once

    button_A.update()
    button_B.update()

    if button_A.pressed:
        play_sound("siren.wav", button_A)

    if button_B.pressed:
        get_joke_wrap()

# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: Unlicense
"""
CircuitPython Simple Example for BME280 and LC709203 Sensors

mix of this tutorial:
https://learn.adafruit.com/adafruit-esp32-s2-feather/i2c-on-board-sensors

And the fact that rev c board has I2C_POWER_INVERTED, not I2C_POWER.
Setting I2C Power pin high requires:
# thanks https://github.com/adafruit/circuitpython/issues/5903
i2c_power = digitalio.DigitalInOut(board.I2C_POWER_INVERTED)
i2c_power.switch_to_output()
i2c_power.value = True
"""
import time
import ssl
import alarm
import board
import digitalio
import wifi
import socketpool
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from adafruit_bme280 import basic as adafruit_bme280
from adafruit_lc709203f import LC709203F, PackSize

try:
    from secrets import secrets
except ImportError:
    print("WiFi and Adafruit IO credentials are kept in secrets.py, please add them there!")
    raise

sleep_duration = 600

# Pull the I2C power pin high
# thanks https://github.com/adafruit/circuitpython/issues/5903
i2c_power = digitalio.DigitalInOut(board.I2C_POWER_INVERTED)
i2c_power.switch_to_output()
i2c_power.value = True

# Create sensor objects, using the board's default I2C bus.
i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

battery_monitor = LC709203F(i2c)
battery_monitor.pack_size = PackSize.MAH2000

led = digitalio.DigitalInOut(board.LED)
led.switch_to_output()



# change this to match your location's pressure (hPa) at sea level
# per https://aviationweather.gov/adds/metars/index?submit=1&station_ids=KPDX&chk_metars=on&hoursStr=2&std_trans=translated&chk_tafs=on
bme280.sea_level_pressure = 1018

# collect sensorvalues

# Collect the sensor data values and format the data
temperature = "{:.2f}".format(bme280.temperature)
temperature_f = "{:.2f}".format((bme280.temperature * (9 / 5) + 32))  # Convert C to F
humidity = "{:.2f}".format(bme280.relative_humidity)
pressure = "{:.2f}".format(bme280.pressure)
battery_voltage = "{:.2f}".format(battery_monitor.cell_voltage)
battery_percent = "{:.1f}".format(battery_monitor.cell_percent)

def go_to_sleep(sleep_period):
    # FIXME: maybe need board.I2C_POWER_INVERTED (see above)
    # i2c_power = digitalio.DigitalInOut(board.I2C_POWER)
    i2c_power.switch_to_input()

    # Create a an alarm that will trigger sleep_period number of seconds from now.
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep_period)
    # Exit and deep sleep until the alarm wakes us.
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)

def setup_feed(feed_name):
    try:
        # Get the feed of provided feed_name from Adafruit IO
        return io.get_feed(feed_name)
    except AdafruitIO_RequestError:
        # If no feed of that name exists, create it
        return io.create_new_feed(feed_name)


# Send the data. Requires a feed name and a value to send.
def send_io_data(feed, value):
    return io.send_data(feed["key"], value)


# Wi-Fi connections can have issues! This ensures the code will continue to run.
try:
    # Connect to Wi-Fi
    wifi.radio.connect(secrets["ssid"], secrets["password"])
    print("Connected to {}!".format(secrets["ssid"]))
    print("IP:", wifi.radio.ipv4_address)

    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())

# Wi-Fi connectivity fails with error messages, not specific errors, so this except is broad.
except Exception as e:  # pylint: disable=broad-except
    print(e)
    go_to_sleep(60)

# Set your Adafruit IO Username and Key in secrets.py
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)

# Turn on the LED to indicate data is being sent.
led.value = True
# Print data values to the serial console. Not necessary for Adafruit IO.
print("Current BME280 temperature: {0} C".format(temperature))
print("Current BME280 temperature: {0} F".format(temperature_f))
print("Current BME280 humidity: {0} %".format(humidity))
print("Current BME280 pressure: {0} hPa".format(pressure))
print("Current battery voltage: {0} V".format(battery_voltage))
print("Current battery percent: {0} %".format(battery_percent))

# Adafruit IO sending can run into issues if the network fails!
# This ensures the code will continue to run.
try:
    print("Sending data to AdafruitIO...")
    # Send data to Adafruit IO
    send_io_data(setup_feed("bme280-temperature"), temperature)
    send_io_data(setup_feed("bme280-temperature-f"), temperature_f)
    send_io_data(setup_feed("bme280-humidity"), humidity)
    send_io_data(setup_feed("bme280-pressure"), pressure)
    send_io_data(setup_feed("battery-voltage"), battery_voltage)
    send_io_data(setup_feed("battery-percent"), battery_percent)
    print("Data sent!")
    # Turn off the LED to indicate data sending is complete.
    led.value = False

# Adafruit IO can fail with multiple errors depending on the situation, so this except is broad.
except Exception as e:  # pylint: disable=broad-except
    print(e)
    go_to_sleep(60)

go_to_sleep(sleep_duration)


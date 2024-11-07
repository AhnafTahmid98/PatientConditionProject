import RPi.GPIO as GPIO
import time

# Pin definitions
green_led = 17  # GPIO 17 (Pin 11)
yellow_led = 27  # GPIO 27 (Pin 13)
red_led = 22  # GPIO 22 (Pin 15)

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(green_led, GPIO.OUT)
GPIO.setup(yellow_led, GPIO.OUT)
GPIO.setup(red_led, GPIO.OUT)

try:
    while True:
        # Turn on the green LED and print a message
        GPIO.output(green_led, GPIO.HIGH)
        print("Green LED is ON")
        time.sleep(1)  # LED stays on for 10 seconds
        
        # Turn off the green LED and print a message
        GPIO.output(green_led, GPIO.LOW)
        print("Green LED is OFF")
        
        # Turn on the yellow LED and print a message
        GPIO.output(yellow_led, GPIO.HIGH)
        print("Yellow LED is ON")
        time.sleep(1)  # LED stays on for 10 seconds
        
        # Turn off the yellow LED and print a message
        GPIO.output(yellow_led, GPIO.LOW)
        print("Yellow LED is OFF")
        
        # Turn on the red LED and print a message
        GPIO.output(red_led, GPIO.HIGH)
        print("Red LED is ON")
        time.sleep(1)  # LED stays on for 10 seconds
        
        # Turn off the red LED and print a message
        GPIO.output(red_led, GPIO.LOW)
        print("Red LED is OFF")

except KeyboardInterrupt:
    # Cleanup on exit
    GPIO.cleanup()

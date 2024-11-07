import RPi.GPIO as GPIO
import time

# Define the GPIO pin connected to the input pin of the buzzer
buzzer_pin = 23  # Adjust this based on your actual GPIO connection

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(buzzer_pin, GPIO.OUT)

try:
    # Turn the buzzer on and off in a loop
    while True:
        GPIO.output(buzzer_pin, GPIO.HIGH)  # Activate the buzzer
        time.sleep(0.3)                     # Buzzer on for 0.5 seconds
        GPIO.output(buzzer_pin, GPIO.LOW)   # Deactivate the buzzer
        time.sleep(0.5)                     # Buzzer off for 0.5 seconds

except KeyboardInterrupt:
    # Cleanup on exit
    GPIO.cleanup()

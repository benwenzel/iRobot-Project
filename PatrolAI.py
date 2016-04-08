import create
import time
import pygame
import numpy as np
import cv2
import os

# A helper function that tries to detect the OS and return the appropriate port path
def getPortPath():
	osName = os.name
	if (osName == "posix"):
		portPath = "/dev/tty.KeySerial1"
	elif (osName == "Linux"):
		portPath = "/dev/ttyUSB0"
	elif (osName == "Windows"):
		portPath = "COM3" #see https://piazza.com/class/ijdbjj478bi10j?cid=273
	else:
		raise Exception("Could not determine your OS.")
	return portPath

# The speed at which the robot moves, in centimeters per second
ROBOT_SPEED = 20

# Get the port path/name string
portPath = getPortPath()

# Initialize the robot
robot = create.Create(portPath)

# The videostream used by OpenCV
cap = cv2.VideoCapture(0)

# Run the robot's logic loop
patrol = True
while (patrol):

	##### ROBOT LOGIC #####
	# Poll sensor values
	sensors = robot.sensors([create.LEFT_BUMP, create.RIGHT_BUMP])
	# If either of the bumpers is depressed, stop patrolling
	if (sensors[create.LEFT_BUMP] == 1 or sensors[create.RIGHT_BUMP] == 1):
		robot.stop()
		#back up
		robot.go(-ROBOT_SPEED,0)
		#pause the loop to let the robot back up a bit
		time.sleep(0.1)
		robot.stop()
		robot.turn(180, 100)
		robot.go(ROBOT_SPEED,0)
	else:
		robot.go(ROBOT_SPEED,0)


	###### OPENCV LOGIC ######
	# Capture a single frame from the videostream
	frame = cap.read()[1]
	# Convert the BGR (Blue, Green, Red) colorspace to HSV (Hue, Saturation, Value/Brightness)
	hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
	# Define upper and lower bounds in HSV colorspace for the color detection
	lower_blue = np.array([90,100,50])
	upper_blue = np.array([130,255,255])
	# Create the mask to block all colors except the target color
	mask = cv2.inRange(hsv, lower_blue, upper_blue)
	# Apply the mask
	res = cv2.bitwise_and(hsv, hsv, mask=mask)
	# Threshhold the image so that all non-target color values are black and all
	# target color values are white
	rest = cv2.threshold(res, 0, 255, cv2.THRESH_BINARY)[1]	
		
# Release the OpenCV video capture
cap.release()






#Here is a general outline of a possible approach:
	
# 1. Create camera
# 2. Rotate in place until the blue node is in sight
# 3. Move toward the blue node until the bumper goes off
# 4 Move back slightly to reset the bumper, rotate in place until the red node is in sight
# 5 Move toward the red node until the bumper goes off

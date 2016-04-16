import create
import utilities as ut
import time
import pygame
import numpy as np
import cv2
import argparse


# Get commandline arguments
parser = argparse.ArgumentParser()
parser.add_argument("--source", type=int, help="specifies the camera that is the source of the video feed")
args = parser.parse_args()

# The camcode tells us what device to use: 0 for the built-in webcam, 1 for the external webcam
camCode = 0
if (args.source == 1):
	camCode = 1

# Get the serial port path/name string
portPath = ut.getPortPath()

# Initialize the robot
robot = create.Create(portPath)

# The speed at which the robot moves, in centimeters per second
ROBOT_SPEED = 10


# Define the HSV color ranges for blue, red, and green for color detection

# Define HSV range for blue
lower_blue = np.array([90,80,80])
upper_blue = np.array([130,255,255])

# Define the HSV range for green
lower_green = np.array([46,80,50])
upper_green = np.array([92,255,255])

# Define the HSV range for yellow
lower_yellow = np.array([31,80,50])
upper_yellow = np.array([45,255,255])

# Define the HSV color range for red--this is a special case, because red exists at both the
# upper and lower ends of the HSV hue spectrum, so we have to combine two ranges
# The red range at the lower end of the spectrum
lower_red1 = np.array([0,150,100])
upper_red1 = np.array([10,255,255])
# The red range at the upper end of the spectrum
lower_red2 = np.array([160,150,100])
upper_red2 = np.array([200,255,255])


# Returns a list of all contours with an area greater than 100 pixels of the given color in the given image
def findContours(image, color, min_area):
	# Remove noise in order to get cleaner contours
	denoised_image = cv2.GaussianBlur(image, (9,9), 0)
	
	# Convert the frame from BGR to HSV (Hue, Saturation, Value/Brightness) for threshholding
	hsv_image = cv2.cvtColor(denoised_image, cv2.COLOR_BGR2HSV)
	
	# Create the color-specific mask to remove all non-target colors
	if (color == Color.Blue):
		mask = cv2.inRange(hsv_image, lower_blue, upper_blue)
	elif (color == Color.Green):
		mask = cv2.inRange(hsv_image, lower_green, upper_green)
	elif (color == Color.Yellow):
		mask = cv2.inRange(hsv_image, lower_yellow, upper_yellow)
	elif (color == Color.Red):
		mask_lower = cv2.inRange(hsv_image, lower_red1, upper_red1)
		mask_upper = cv2.inRange(hsv_image, lower_red2, upper_red2)
		mask = mask_lower + mask_upper
	# Apply the mask
	masked_image = cv2.bitwise_and(frame, frame, mask=mask)
	
	# Convert to a greyscale image, otherwise cv2.findContours() complains (why is that?)
	greyscale_image = cv2.cvtColor(masked_image, cv2.COLOR_BGR2GRAY)
	
	# Threshhold the image so that all non-target color values are black and all target color values
	# are white
	thresh, black_white_image = cv2.threshold(greyscale_image, 0, 255, 0)
	
	# Find the contours
	# See http://stackoverflow.com/questions/25504964/opencv-python-valueerror-too-many-values-to-unpack
	output_image, contours, hierarchy = cv2.findContours(black_white_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
	
	# If there are any contours in the current frame, process them
	if (len(contours) > 0):
		# We only care about the largest contour (because this will most likely be our patrol node), so
		# sort the contours in place using a lambda to compare them by their size field (aka their area)
		contours.sort(key=lambda x: x.size, reverse=True)
		
		# Delete everything except the first (which is the largest) contour
		if (len(contours) > 1):
			del contours[1:]
		
		# If the largest contour has an area of less than 100 pixels, delete it too, as it's probably just noise
		if (len(contours[0]) < min_area):
			del contours[0]

	return contours

# returns a string saying whether the contour is centerd on screen, adjusted by sensitivity
def contourAlignment(contour, sensitivity, image):
	# Get the x,y coordinates of the bounding rect, as well as its width and height
	x,y,w,h = cv2.boundingRect(contour)
	node_left = x;
	node_right = x+h;
	# Get the height and width of the frame
	img_height, img_width, channels = image.shape
				
	# Calculate any adjustments in the robot's direction by comparing the respective differences between
	# the left side of the contour bounding rect and the
	left_difference = node_left
	right_difference = img_width - node_right
	if (left_difference+sensitivity < right_difference):
		return "left"
	elif (left_difference-sensitivity > right_difference):
		return "right"
	else:
		return "center"

enemy_color = Color.Red
target_color = Color.Blue

# The videostream used by OpenCV
cap = cv2.VideoCapture(camCode)
frame_count = 0

# Run the robot's logic loop
mode = "moveToNode" #, "findNode", "attack"
loop = True
while (loop):
	# Capture frame-by-frame
	frame = cap.read()[1]
	frame_count += 1
	print("=== FRAME " + str(frame_count) + " ===")
	if (target_color == Color.Blue):
		print("Target Color: Blue")
	elif(target_color == Color.Green):
		print("Target Color: Green")
	elif(target_color == Color.Red):
		print("Target Color: Red")

	# Poll sensor values
	sensors = robot.sensors([create.LEFT_BUMP, create.RIGHT_BUMP])

	# Very simplistic state machine
	if (mode == "moveToNode"):
		print("Mode: moveToNode")
		# If either of the bumpers is depressed, the node has been hit
		if (sensors[create.LEFT_BUMP] == 1 or sensors[create.RIGHT_BUMP] == 1):
			print("TRIGGERED!!")
			robot.stop()
			robot.go(-ROBOT_SPEED,0)
			time.sleep(0.5)
			robot.stop()
			# Change the color of the target node so it moves to the opposite one
			if (target_color == Color.Green):
				target_color = Color.Blue
			elif (target_color == Color.Blue):
				target_color = Color.Green
			mode = "findNode"
			continue
		#mode = "findNode"
		# Do other stuff
		enemies = findContours(frame, enemy_color, 150)
		if (len(enemies) > 0):
			print("ENEMY IN SIGHT")
			mode = "attack"
		else:
			contours = findContours(frame, target_color, 100)
			# Detect the node's orientation
			if (len(contours) > 0):
				alignment = contourAlignment(contours[0], 100, frame)
				if (alignment == "left"):
					print("\tSkewed to the left")
					robot.go(ROBOT_SPEED, 15)
				elif (alignment == "right"):
					print("\tSkewed to the right")
					robot.go(ROBOT_SPEED, -15)
				else:
					robot.go(ROBOT_SPEED, 0)

			# Draw the computed contours to the image
			cv2.drawContours(frame, contours, -1, (255, 255, 255), -1)
			
	elif (mode == "findNode"):
		print("Mode: findNode");
		robot.resetPose()
		robot.turn(36,720)
		contours = findContours(frame, target_color, 100)
		if (len(contours) > 0):
			mode = "moveToNode"
			continue;
		# Rotate in place, looking for a color
		# TODO: robot.resetPose(), spin around until you find the angle where
		# the largest contour is visible, remember that angle, then once you've completed
		# the 360 degree revolution, spin to that stored angle and target the node (which
		# would have to be of a certain base area size, probably around 200 pixels or so)
		
	elif (mode == "attack"):
		print("Mode: attack")
		# If either of the bumpers is depressed, the node has been hit
		if (sensors[create.LEFT_BUMP] == 1 or sensors[create.RIGHT_BUMP] == 1):
			print("TRIGGERED!!")
			#back up
			robot.stop()
			robot.go(-ROBOT_SPEED,0)
			robot.stop()
			target_color = last_node_color
			mode = "findNode"
			continue
		# Do other stuff
		enemies = findContours(frame, enemy_color, 150)
		if (len(enemies) > 0):
			print("ENEMY IN SIGHT")
			alignment = contourAlignment(enemies[0], 100, frame)
			if (alignment == "left"):
				print("\tSkewed to the left")
				robot.go(ROBOT_SPEED, 15)
			elif (alignment == "right"):
				print("\tSkewed to the right")
				robot.go(ROBOT_SPEED, -15)
			else:
				robot.go(ROBOT_SPEED, 0)
		else:
			mode = "findNode"
			continue

		# Draw the computed contours to the image
		cv2.drawContours(frame, enemies, -1, (255, 255, 255), -1)
	
	# Display the resulting frame
	cv2.imshow('Window', frame)
	if (cv2.waitKey(1) & 0xFF == ord('q')):
		loop = False

	# Limit the frame/loop rate by sleeping a little at the end of each frame
	time.sleep(0.02)
# End of loop

# The logic loop is done, stop the robot and release the capture
robot.stop()
cap.release()
cv2.destroyAllWindows()

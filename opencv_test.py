import numpy as np
import cv2
import time

# Python enum emulation for colors
class Color:
    Blue, Red, Green, Yellow = range(4)


# Define the HSV color ranges for blue, red, and green for color detection

# Define HSV range for blue
lower_blue = np.array([90,50,50])
upper_blue = np.array([130,255,255])

# Define the HSV range for green
lower_green = np.array([46,50,50])
upper_green = np.array([92,255,255])

# Define the HSV range for yellow
lower_yellow = np.array([31,50,50])
upper_yellow = np.array([45,255,255])

# Define the HSV color range for red--this is a special case, because red exists at both the
# upper and lower ends of the HSV hue spectrum, so we have to combine two ranges
# The red range at the lower end of the spectrum
lower_red1 = np.array([0,150,100])
upper_red1 = np.array([10,255,255])
# The red range at the upper end of the spectrum
lower_red2 = np.array([160,150,100])
upper_red2 = np.array([200,255,255])


#set the initial color that the robot will search for when it begins its patrol path
target_color = Color.Blue

# This is the videocapture that OpenCV will use to capture frames from the camera
cap = cv2.VideoCapture(1)
frame_count = 0

while (True):
    frame_count += 1
    print("=== FRAME " + str(frame_count) + " ===")
	
    # Capture frame-by-frame
    frame = cap.read()[1]
	
	# Remove noise in order to get cleaner contours later on
    frame = cv2.GaussianBlur(frame, (9,9), 0)
	
    # Flip the frame horizontally if needed
	#frame = cv2.flip(frame,1)

    # Convert BGR to HSV (Hue, Saturation, Value/Brightness) for threshholding
    hsv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

	# Create the mask to remove all non-target colors
    if (target_color == Color.Blue):
        mask = cv2.inRange(hsv_image, lower_blue, upper_blue)
    elif (target_color == Color.Green):
        mask = cv2.inRange(hsv_image, lower_green, upper_green)
    elif (target_color == Color.Yellow):
        mask = cv2.inRange(hsv_image, lower_yellow, upper_yellow)
    elif (target_color == Color.Red):
        mask_lower = cv2.inRange(hsv_image, lower_red1, upper_red1)
        mask_upper = cv2.inRange(hsv_image, lower_red2, upper_red2)
        mask = mask_lower + mask_upper
	#mask = cv2.inRange(hsv_image, lower_green, upper_green)
	# Apply the mask
    masked_image = cv2.bitwise_and(frame, frame, mask=mask)
	
	# Convert to a greyscale image, otherwise cv2.findContours() complains (why is that?)
    greyscale_image = cv2.cvtColor(masked_image,cv2.COLOR_BGR2GRAY)

	# Threshhold the image so that all non-target color values are black and all
	# target color values are white
    thresh, black_white_image = cv2.threshold(greyscale_image, 0, 255, 0)
	
	# Find the contours
    # See http://stackoverflow.com/questions/25504964/opencv-python-valueerror-too-many-values-to-unpack
    output_image, contours, hierarchy = cv2.findContours(black_white_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    # If there are any contours in the current frame, process them
    if (len(contours) > 0):
		# We only care about the largest contour (because this will most likely be our patrol node), so
		# sort the contours in place using a lambda to compare them by their size field (aka their area)
        contours.sort(key=lambda x: x.size, reverse=True)
		
		# We only care about the largest contour, so delete everything except the first (largest) contour
        if (len(contours) > 1):
            del contours[1:]
		
        # If the largest contour has an area of less than 100 pixels, delete it too, as it's probably just noise
        if (len(contours[0]) < 100):
            del contours[0]
		
		# Now that we've culled the noise and (hopefully) isolated the node, detect the node's orientation
        if (len(contours)>0):
            x,y,w,h = cv2.boundingRect(contours[0])
            node_left = x;
            node_right = x+h;
            img_height, img_width, channels = frame.shape
			# Sensitivity is a pixel value, if the left difference and right difference differ by more than
			# the value of sensitivity, the contour is skewed to one side
            sensitivity = 150
            left_difference = node_left
            right_difference = img_width - node_right
			
            print("L/R differences: " + str(left_difference) + " " + str(right_difference))
            if (left_difference+sensitivity < right_difference):
                print("\tSkewed to the left")
            if (left_difference-sensitivity > right_difference):
                print("\tSkewed to the right")
			
		    #print out the area of the contour (which is the number of pixels the contour occupies)
            for element in contours:
                print("\tContour Area: " + str(len(element)))
            # Draw the bounding box of the contour
            cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),1)


	# Draw the computed contours to the image
    cv2.drawContours(frame,contours,-1,(255,255,255),-1)

    # Display the resulting frame
    cv2.imshow('Window',frame)
    if (cv2.waitKey(1) & 0xFF == ord('q')):
        break
    # Limit the frame/loop rate by sleeping a little at the end of each frame
    time.sleep(0.012)

# When the loop is done, release the capture
cap.release()
cv2.destroyAllWindows()

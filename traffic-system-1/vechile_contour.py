import numpy as np
import cv2
import os
import time
path_contour = '/home/thiruvenkatam/Desktop/hackathon/contour_images'
path_image = '/home/thiruvenkatam/Desktop/hackathon/frame_images'
videoList = ['highway2.mp4', 'highway.mp4', 'highway3.mp4', 'highway4.mp4']


def contour(imgray, index, n):
    # imgray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # imgray = cv2.GaussianBlur(imgray, (5, 5), 0)
    #
    ret, thresh = cv2.threshold(imgray, 127, 255, 0)
    #
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # print(len(contours))

    minarea = 300

    # max area for contours, can be quite large for buses
    maxarea = 50000
    vechile_count = 0;
    for i in range(len(contours)):
        if hierarchy[0, i, 3] == -1:  # using hierarchy to only count parent contours (contours not within others)
            area = cv2.contourArea(contours[i])
            if minarea < area < maxarea:
                cv2.drawContours(imgray, contours, i, (255, 255, 0), 3)
                vechile_count += 1

    # cv2.imwrite(os.path.join(path_contour, "contour"+str(n)+str(index)+".jpg"), imgray)
    # print(vechile_count)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    return vechile_count, imgray



# print(weights)
def process_images(n):
    weights = []
    for index, video in enumerate(videoList):
        # print(video)
        # print(index)
        cap = cv2.VideoCapture(video)
        _, first_frame = cap.read()
        first_gray = cv2.cvtColor(first_frame, cv2.COLOR_BGR2GRAY)
        first_gray = cv2.GaussianBlur(first_gray, (5, 5), 0)
        count = 0;

        while count <= 100 * n:
            _, frame = cap.read()
            count += 1
        # cv2.imwrite(os.path.join(path_image, "frame" + str(n) + str(index+1) + ".jpg"), frame)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_frame = cv2.GaussianBlur(gray_frame, (5, 5), 0)

        difference = cv2.absdiff(first_gray, gray_frame)

        # print difference
        # break
        _, difference = cv2.threshold(difference, 25, 255, cv2.THRESH_BINARY)
        # cv2.imshow("first_frame"+video, first_frame)
        # cv2.imshow("tenth_frame"+video, frame)
        # cv2.imshow("difference" + video, difference)
        count, contours = contour(difference, index+1,n)
        weights.append((index+1, count))
    return weights

n = 1;
while n <= 5:
    start = time.time()
    print(process_images(n))
    end=time.time()
    print(end-start)
    n+=1

cv2.waitKey(0)
cv2.destroyAllWindows()



import cv2
import os
import time
from operator import itemgetter, attrgetter
from collections import OrderedDict
import requests
import json


path_contour = '/home/thiruvenkatam/Desktop/hackathon/contour_images'
path_image = '/home/thiruvenkatam/Desktop/hackathon/frame_images'
videoList = ['highway2.mp4', 'highway.mp4', 'highway3.mp4', 'highway4.mp4']
total_time = 60
time_left = 0

url = 'http://66b4885b.ngrok.io/traffic-service/traffic-signals/'
traffic_id = str(1)
#yet to work
req = requests.get(url+traffic_id)
res = json.loads(req.text)
lane = res['message']['lane_order']
#print(lane)
lane_order = []
lane_list = lane.split(",")
for i in lane_list:
    lane_order.append(int(i))

three_lane_universal_matrix = [[0, 1, 2, 3], [3, 0, 1, 2], [2, 3, 0, 1], [1, 2, 3, 0]]


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

def weights_harmonization(weights):
    harmonized_list = []
    harmonized_weights = []
    for index,(key,value) in enumerate(weights):
        harmonized_list.append(value)

    for index in range(len(harmonized_list)):
        count=1
        for index2 in range(index+1, len(harmonized_list)):
            if harmonized_list[index] == harmonized_list[index2]:
                harmonized_list[index2] = harmonized_list[index2] + 0.001 * count
                count+=1

    for index,values in enumerate(harmonized_list):
        harmonized_weights.append((index+1,values))

    return harmonized_weights

# print(sorted_weights)

def get_signal_number(weights, vehicle_count):
    for key, value in weights.items():
        if vehicle_count == value:
            return key


def get_rank(weight,sorted_weights):
    net_sum = sum(weight)
    rank_list = []
    for index, value in enumerate(weight):
        rank_list.append((get_signal_number(sorted_weights, value), round(float(value)/net_sum, 2)))
    return rank_list

def get_time(rank):
    global time_left
    time = []
    for key,value in rank:
        time.append((key, round(value * 60, 2)))
        time_left= time_left + round(value * 60, 2)
    return time



# rank_list = get_rank(weight_list)
# # print(rank_list)
# rank_time = get_time(rank_list)
# print(rank_time)


def two_lane_threshold(lane1, lane2):
    if(abs(lane1 - lane2)) < 10:
        return True


def get_rank_time(rank_time, signal_id):
    for key,value in rank_time:
        if signal_id == key:
            return value


def check_adjacent_interleave(weight1, weight2, sorted_weights):
    lane1 = get_signal_number(sorted_weights, weight1)
    lane2 = get_signal_number(sorted_weights, weight2)
    if abs(lane1-lane2) != 2:
        if lane1>lane2 or lane2>lane1 or (lane1==4 and lane2==1) or (lane1==1 and lane2==4):
            return True
    return False


def allocate_lanes(weight1, weight2, time, sorted_weights, missing_lane):
    # print("function")
    # print(weight1,weight2)
    if missing_lane is None:
        if find_order(sorted_weights,weight1) < find_order(sorted_weights,weight2):
            alloc1 = [(get_signal_number(sorted_weights, weight1), -1, 'right',
                       'straight', round(time / 3, 2))]
        else:
            alloc1 = [(get_signal_number(sorted_weights, weight2), -1, 'right',
                       'straight', round(time / 3, 2))]

        alloc2 = [(get_signal_number(sorted_weights, weight1), get_signal_number(sorted_weights, weight2), 'right',
               'straight', round(time / 3, 2))]

        if find_order(sorted_weights,weight1) > find_order(sorted_weights,weight2):
            alloc3 = [(get_signal_number(sorted_weights, weight1), -1, 'right',
                       'straight', round(time / 3, 2))]
        else:
            alloc3 = [(get_signal_number(sorted_weights, weight2), -1, 'right',
                       'straight', round(time / 3, 2))]


    else:
        lane1 = three_lane_universal_matrix[missing_lane - 1][get_signal_number(sorted_weights, weight1) - 1]
        lane2 = three_lane_universal_matrix[missing_lane - 1][get_signal_number(sorted_weights, weight2) - 1]
        # print(lane1, lane2)
        # print(get_signal_number(sorted_weights, weight1), get_signal_number(sorted_weights, weight2))
        # print(weight1,weight2)
        if lane1 == 1 and lane2 == 2:
            alloc1 = [(get_signal_number(sorted_weights, weight1), -1, 'right', 'straight', round(time / 3, 2))]
            alloc2 = [(get_signal_number(sorted_weights, weight2), -1, 'right', None, round(time / 3, 2))]
        elif lane1 == 2 and lane2 == 1:
            alloc2 = [(get_signal_number(sorted_weights, weight1), -1, 'right', None, round(time / 3, 2))]
            alloc1 = [(get_signal_number(sorted_weights, weight2), -1, 'right', 'straight', round(time / 3, 2))]
        elif lane1 == 3 and lane2 == 2:
            alloc1 = [(get_signal_number(sorted_weights, weight1), -1, None, 'straight', round(time / 3, 2))]
            alloc2 = [(get_signal_number(sorted_weights, weight2), -1, 'right', None, round(time / 3, 2))]
        elif lane1 == 2 and lane2 == 3:
            alloc2 = [(get_signal_number(sorted_weights, weight1), -1, 'right', None, round(time / 3, 2))]
            alloc1 = [(get_signal_number(sorted_weights, weight2), -1, None, 'straight', round(time / 3, 2))]
        alloc3 = []
    return alloc1, alloc2, alloc3


def allocate_adjacent_lane(weight1, weight2, time, sorted_weights, missing_lane):
    lane1 = get_signal_number(sorted_weights, weight1)
    lane2 = get_signal_number(sorted_weights, weight2)
    # print(lane1,lane2)
    # print(weight1, weight2)
    if(lane1 !=1 or lane2 !=4) and (lane1 != 4 or lane2 != 1):
        if lane1 > lane2:
            # print("one")
            alloc1, alloc2, alloc3 = allocate_lanes(weight1, weight2, time, sorted_weights, missing_lane)
        else:
            # print("two")
            alloc1, alloc2, alloc3 = allocate_lanes(weight2, weight1, time, sorted_weights, missing_lane)
    else:
        if lane1 == 1 and lane2 == 4:
            # print("one")
            alloc1, alloc2, alloc3 = allocate_lanes(weight1, weight2, time, sorted_weights, missing_lane)
        elif lane1 == 4 and lane2 == 1:
            # print("two")
            alloc1, alloc2, alloc3 = allocate_lanes(weight2, weight1, time, sorted_weights, missing_lane)

    return alloc1, alloc2, alloc3


def allocate_single_lane(vehicle_count, sorted_weights, rank_time, signals_alloted, weights_assigned, missing_lane):
    global time_left
    time = get_rank_time(rank_time, get_signal_number(sorted_weights, vehicle_count))

    # print(time_left,time)
    if time_left >= time:
        if missing_lane:
            lanes_to_be_allocated = three_lane_universal_matrix[missing_lane-1][get_signal_number(sorted_weights, vehicle_count)-1]
            if lanes_to_be_allocated == 1:
                alloc = [(get_signal_number(sorted_weights, vehicle_count), -1, 'straight', 'right', time)]
            if lanes_to_be_allocated == 2:
                alloc = [(get_signal_number(sorted_weights, vehicle_count), -1, None, 'right', time)]
            if lanes_to_be_allocated == 3:
                alloc = [(get_signal_number(sorted_weights, vehicle_count), -1, 'straight', None, time)]
        else:
            alloc = [(get_signal_number(sorted_weights, vehicle_count), -1, 'straight', 'right', time)]
        time_left = time_left - time
        signals_alloted.append(get_signal_number(sorted_weights, vehicle_count))
        weights_assigned.append(vehicle_count)
        # print(alloc)
        return alloc


def allocate_two_lanes(weight1, weight2, sorted_weights, rank_time,signals_alloted,weights_assigned, missing_lane):
    global time_left
    opp_time = max(get_rank_time(rank_time,get_signal_number(sorted_weights, weight1)), get_rank_time(rank_time, get_signal_number(sorted_weights, weight2)))
    adj_time = get_rank_time(rank_time,get_signal_number(sorted_weights, weight1)) + get_rank_time(rank_time,get_signal_number(sorted_weights, weight2))
    if time_left >= opp_time or time_left >= adj_time:
        if check_adjacent_interleave(weight1, weight2, sorted_weights):
            alloc1, alloc2, alloc3 = allocate_adjacent_lane(weight1, weight2, adj_time, sorted_weights, missing_lane)
            time_left = time_left - adj_time
        else:
            if missing_lane:
                lane1 = three_lane_universal_matrix[missing_lane-1][get_signal_number(sorted_weights, weight1)-1]
                lane2 = three_lane_universal_matrix[missing_lane - 1][get_signal_number(sorted_weights, weight2) - 1]
                # print(lane1,lane2)
                alloc1 = [(get_signal_number(sorted_weights, weight1), get_signal_number(sorted_weights, weight2),
                           'straight', 'straight', round(opp_time / 2, 2))]
                if lane1 == 1:
                    alloc2 = [(get_signal_number(sorted_weights, weight1), -1,
                               'straight', 'right', round(opp_time / 2, 2))]
                elif lane2 == 1:
                    alloc2 = [(get_signal_number(sorted_weights, weight2), -1,
                               'straight', 'right', round(opp_time / 2, 2))]
            else:
                alloc1 = [(get_signal_number(sorted_weights, weight1), get_signal_number(sorted_weights, weight2),
                       'straight', 'straight', round(opp_time/2, 2))]
                alloc2 = [(get_signal_number(sorted_weights, weight1), get_signal_number(sorted_weights, weight2), 'right',
                       'right', round(opp_time/2, 2))]

            alloc3 = []
            time_left = time_left - opp_time

        time_left = round(time_left, 2)
        signals_alloted.append(get_signal_number(sorted_weights, weight1))
        signals_alloted.append(get_signal_number(sorted_weights, weight2))
        weights_assigned.append(weight1)
        weights_assigned.append(weight2)
        return alloc1, alloc2, alloc3


def compare_weight(weight1,weight2):
    difference = round(abs(weight1 - weight2), 2)
    return [(difference, weight1, weight2)]


def check_order(index, weight_list,difference_array):
    i = index
    j = index+1
    if(index < 3):
        for i in range(i, len(weight_list)-1):
            for j in range(j, len(weight_list)):
                # print(i,j)
                difference_array.append(compare_weight(weight_list[i], weight_list[j]))
                # j += 1
            # i += 1
        return difference_array


def find_order(sorted_weights,value):
    position = get_signal_number(sorted_weights, value)
    return lane_order.index(position)


def check_other_weights(weight1, weight2, list, sorted_weights):
    max_value = 0
    min_value = 0
    max_value_position = -1
    min_value_position = -1
    for value in list:
        if value > weight1 and value > weight2:
            max_value = value
        elif value < weight1 and value < weight2:
            min_value = value

    if max_value > 0:
        max_value_position = find_order(sorted_weights, max_value)
    if min_value > 0:
        min_value_position = find_order(sorted_weights, min_value)

    #print(max_value, min_value, max_value_position, min_value_position)
    return max_value, min_value, max_value_position, min_value_position


def check_interleave(array, weight_list, sorted_weights,rank_time, signals_alloted, weights_assigned, missing_lane):
    sorted_x = sorted(array, key=itemgetter(0))
    #print(sorted_x)
    for p in sorted_x:
        for index, (diff, value1, value2) in enumerate(p):
            if index == 0 and diff <= 9:
                max_value, min_value, max_value_position, min_value_position = check_other_weights(value1, value2, weight_list,sorted_weights)
                if max_value > 0 and (max_value_position < find_order(sorted_weights,value1) or max_value_position < find_order(sorted_weights,value2)):
                    allocation.append(allocate_single_lane(max_value, sorted_weights, rank_time, signals_alloted, weights_assigned,missing_lane))
                if min_value > 0 and (min_value_position < find_order(sorted_weights,value1) or min_value_position < find_order(sorted_weights,value2)):
                    allocation.append(allocate_single_lane(min_value, sorted_weights, rank_time, signals_alloted, weights_assigned,missing_lane))

                alloc1, alloc2, alloc3 = allocate_two_lanes(value1, value2, sorted_weights, rank_time, signals_alloted, weights_assigned, missing_lane)
                allocation.append(alloc1)
                allocation.append(alloc2)
                if alloc3:
                    allocation.append(alloc3)

                if max_value > 0 and (max_value_position > find_order(sorted_weights,value1) or max_value_position > find_order(sorted_weights,value2)):
                    allocation.append(allocate_single_lane(max_value, sorted_weights, rank_time, signals_alloted, weights_assigned,missing_lane))
                if min_value > 0 and (min_value_position > find_order(sorted_weights,value1) or min_value_position > find_order(sorted_weights,value2)):
                    allocation.append(allocate_single_lane(min_value, sorted_weights, rank_time, signals_alloted, weights_assigned,missing_lane))

                return True
            else:
                return False
                break
        break


def prepare_algorthim(weights):
    global allocation
    missing_lane = None
    weights = weights_harmonization(weights)
    ordered_weights = []
    #print(weights)
    for key in lane_order:
        if weights[key - 1]:
            ordered_weights.append(weights[key - 1])

    # print(ordered_weights)
    # sorted_weights = OrderedDict(sorted(weights, key=lambda kv: kv[1], reverse=True))
    sorted_weights = OrderedDict(ordered_weights)

    weight_list = list(sorted_weights.values())
    weight_list = [item for item in weight_list if item >= 0]
    rank_list = get_rank(weight_list,sorted_weights)
    # print(rank_list)

    diff = list(set(list(sorted_weights.values())) - set(weight_list))
    if diff:
        missing_lane = get_signal_number(sorted_weights, diff[0])
    # print(diff[0])
    rank_time = get_time(rank_list)
    signals_alloted = []
    weights_assigned = []
    allocation = []
    return rank_time, sorted_weights, weight_list, signals_alloted, weights_assigned, missing_lane


def add_incoming(weights, sum_weights, traffic_signal_id):
    modified_weights = []
    result = requests.get(url+'laneconnection?signal1='+traffic_id+'&signal2='+str(traffic_signal_id))
    # print(result.text)
    result = json.loads(result.text)
    lane_number = result['lane']
    factor = result['weight']

    for key,value in weights:
        if key == int(lane_number):
            modified_weights.append((key,value+round(sum_weights*float(factor)/100,0)))
        else:
            modified_weights.append((key, value))

    # return modified_weights
    #print(modified_weights)
    return modified_weights


def traffic_algorithm(weights, sum_weights, traffic_signal_id):
    #print(weights)
    if sum_weights>0:
        weights = add_incoming(weights,sum_weights, traffic_signal_id)
    rank_time, sorted_weights, weight_list, signals_alloted, weights_assigned, missing_lane = prepare_algorthim(weights)
    difference_array = []
    for index, value in enumerate(weight_list):
        # print(weight_list[index])
        if index == 0 and not weight_list[index] in weights_assigned:
            if two_lane_threshold(weight_list[index], weight_list[index+1]):
                alloc1, alloc2, alloc3 = allocate_two_lanes(weight_list[index], weight_list[index+1], sorted_weights, rank_time, signals_alloted, weights_assigned, missing_lane)
                allocation.append(alloc1)
                allocation.append(alloc2)
                if alloc3:
                    allocation.append(alloc3)
            else:
                allocation.append(allocate_single_lane(weight_list[index], sorted_weights, rank_time, signals_alloted, weights_assigned, missing_lane))
        elif not weight_list[index] in weights_assigned:
            difference_array = check_order(index, weight_list,difference_array)
            if difference_array:
                if not check_interleave(difference_array, list(set(weight_list) - set(weights_assigned)), sorted_weights,rank_time, signals_alloted, weights_assigned, missing_lane):
                    allocation.append(allocate_single_lane(weight_list[index], sorted_weights, rank_time, signals_alloted, weights_assigned, missing_lane))
            else:
                # print("hello")
                allocation.append(allocate_single_lane(weight_list[index], sorted_weights, rank_time, signals_alloted, weights_assigned, missing_lane))

    # signals_alloted = []
    # weights_assigned = []
    # print(signals_alloted)
    # print(weights_assigned)
    # print(sorted_weights)
    return allocation, sorted_weights


# this the function we need to call the parameter to be passed is a integer that loop from 1 to 5
# print(traffic_algorithm([(1,29),(2,20),(3,16),(4,18)],[(3,10)
print(traffic_algorithm(process_images(4),60,1))
import numpy as np
from operator import itemgetter, attrgetter
from collections import OrderedDict


total_time = 120
time_left = 0

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
        time.append((key, round(value * 120, 2)))
        time_left= time_left + round(value * 120, 2)
    return time



# rank_list = get_rank(weight_list)
# # print(rank_list)
# rank_time = get_time(rank_list)
# print(rank_time)


def two_lane_threshold(lane1, lane2):
    if(lane1 - lane2) < 10:
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

def allocate_lanes(weight1, weight2, time, sorted_weights):
    # print("function")
    # print(weight1,weight2)
    alloc1 = [(get_signal_number(sorted_weights, weight1), get_signal_number(sorted_weights, weight2), 'right',
               'straight', round(time / 3, 2))]
    alloc2 = [(get_signal_number(sorted_weights, weight1), -1 , 'right',
               'straight', round(time / 3, 2))]
    alloc3 = [(get_signal_number(sorted_weights, weight2), -1, 'right',
               'straight', round(time / 3, 2))]
    return alloc1, alloc2, alloc3


def allocate_adjacent_lane(weight1, weight2, time, sorted_weights):
    lane1 = get_signal_number(sorted_weights, weight1)
    lane2 = get_signal_number(sorted_weights, weight2)
    # print(lane1,lane2)
    # print(weight1, weight2)
    if(lane1 !=1 or lane2 !=4) and (lane1 !=4 or lane2 !=1):
        if lane1 > lane2:
            # print("one")
            alloc1, alloc2, alloc3 = allocate_lanes(weight1, weight2, time, sorted_weights)
        else:
            # print("two")
            alloc1, alloc2, alloc3 = allocate_lanes(weight2, weight1, time, sorted_weights)
    else:
        if lane1 == 1 and lane2 == 4:
            # print("one")
            alloc1, alloc2, alloc3 = allocate_lanes(weight1, weight2, time, sorted_weights)
        elif lane1 == 4 and lane2 == 1:
            # print("two")
            alloc1, alloc2, alloc3 = allocate_lanes(weight2, weight1, time, sorted_weights)

    return alloc1, alloc2, alloc3


def allocate_single_lane(vehicle_count, sorted_weights, rank_time, signals_alloted, weights_assigned):
    global time_left
    time = get_rank_time(rank_time, get_signal_number(sorted_weights, vehicle_count))
    # print("hello")
    # print(time_left,time)
    if time_left >= time:
        alloc = [(get_signal_number(sorted_weights, vehicle_count), -1, 'straight', 'right', time)]
        time_left = time_left - time
        signals_alloted.append(get_signal_number(sorted_weights, vehicle_count))
        weights_assigned.append(vehicle_count)
        # print(alloc)
        return alloc


def allocate_two_lanes(weight1, weight2, sorted_weights, rank_time,signals_alloted,weights_assigned ):
    global time_left
    opp_time = max(get_rank_time(rank_time,get_signal_number(sorted_weights, weight1)), get_rank_time(rank_time, get_signal_number(sorted_weights, weight2)))
    adj_time = get_rank_time(rank_time,get_signal_number(sorted_weights, weight1)) + get_rank_time(rank_time,get_signal_number(sorted_weights, weight2))
    if time_left >= opp_time or time_left >= adj_time:
        if check_adjacent_interleave(weight1, weight2, sorted_weights):
            alloc1, alloc2, alloc3 = allocate_adjacent_lane(weight1, weight2, adj_time, sorted_weights)
            time_left = time_left - adj_time
        else:
            alloc1 = [(get_signal_number(sorted_weights, weight1), get_signal_number(sorted_weights, weight2),
                       'straight', 'straight', round(opp_time/2, 2))]
            alloc2 = [(get_signal_number(sorted_weights, weight1), get_signal_number(sorted_weights, weight2), 'right',
                       'right', round(opp_time/2, 2))]
            alloc3 = []
            time_left = time_left - opp_time

        time_left =  round(time_left, 2)
        signals_alloted.append(get_signal_number(sorted_weights, weight1))
        signals_alloted.append(get_signal_number(sorted_weights, weight2))
        weights_assigned.append(weight1)
        weights_assigned.append(weight2)
        return alloc1, alloc2, alloc3


def compare_weight(weight1,weight2):
    difference = round(weight1 - weight2, 2)
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


def check_other_weights(weight1, weight2, list):
    for value in list:
        if value > weight1 and value > weight2:
            return value
    return -1


def check_interleave(array, weight_list, sorted_weights,rank_time, signals_alloted, weights_assigned):
    sorted_x = sorted(array, key=itemgetter(0))
    for p in sorted_x:
        for index, (diff, value1, value2) in enumerate(p):
            if index == 0 and diff <= 9:
                value = check_other_weights(value1, value2, weight_list)
                if value > 0:
                    allocation.append(allocate_single_lane(value,sorted_weights, rank_time, signals_alloted, weights_assigned))
                alloc1, alloc2, alloc3 = allocate_two_lanes(value1, value2, sorted_weights, rank_time, signals_alloted, weights_assigned)
                allocation.append(alloc1)
                allocation.append(alloc2)
                if alloc3:
                    allocation.append(alloc3)
                return True
            else:
                return False
                break
        break


def prepare_algorthim(weights):
    global allocation
    weights = weights_harmonization(weights)
    sorted_weights = OrderedDict(sorted(weights, key=lambda kv: kv[1], reverse=True))
    weight_list = list(sorted_weights.values())
    weight_list = [item for item in weight_list if item >= 0]
    rank_list = get_rank(weight_list,sorted_weights)
    # print(rank_list)
    rank_time = get_time(rank_list)
    signals_alloted = []
    weights_assigned = []
    allocation = []
    return rank_time, sorted_weights, weight_list, signals_alloted, weights_assigned


def traffic_algorithm(weights):
    rank_time, sorted_weights, weight_list, signals_alloted, weights_assigned = prepare_algorthim(weights)
    difference_array = []
    for index, value in enumerate(weight_list):
        # print(weight_list[index])
        if index == 0 and not weight_list[index] in weights_assigned:
            if two_lane_threshold(weight_list[index], weight_list[index+1]):
                alloc1, alloc2, alloc3 = allocate_two_lanes(weight_list[index], weight_list[index+1], sorted_weights, rank_time, signals_alloted, weights_assigned )
                allocation.append(alloc1)
                allocation.append(alloc2)
                if alloc3:
                    allocation.append(alloc3)
            else:
                allocation.append(allocate_single_lane(weight_list[index], sorted_weights, rank_time, signals_alloted, weights_assigned))
        elif not weight_list[index] in weights_assigned:
            difference_array = check_order(index, weight_list,difference_array)
            if difference_array:
                if not check_interleave(difference_array, list(set(weight_list) - set(weights_assigned)), sorted_weights,rank_time, signals_alloted, weights_assigned):
                    allocation.append(allocate_single_lane(weight_list[index], sorted_weights, rank_time, signals_alloted, weights_assigned))
            else:
                # print("hello")
                allocation.append(allocate_single_lane(weight_list[index], sorted_weights, rank_time, signals_alloted, weights_assigned))

    # signals_alloted = []
    # weights_assigned = []
    # print(signals_alloted)
    # print(weights_assigned)
    # print(sorted_weights)
    return allocation

# n = 0;
# while n<5:
#
#     if(n==0):
#         rank_time, sorted_weights, weight_list, signals_alloted, weights_assigned = prepare_algorthim([(1, 31), (2, 8), (3, 6), (4, 12)])
#     if (n == 1):
#         rank_time, sorted_weights, weight_list, signals_alloted, weights_assigned = prepare_algorthim([(1, 32), (2, 11), (3, 7), (4, 8)])
#     if (n == 2):
#         rank_time, sorted_weights, weight_list, signals_alloted, weights_assigned = prepare_algorthim([(1, 28), (2, 4), (3, 10), (4, 9)])
#     if (n == 3):
#         rank_time, sorted_weights, weight_list, signals_alloted, weights_assigned = prepare_algorthim([(1, 25), (2, 6), (3, 8), (4, 12)])
#     if (n == 4):
#         rank_time, sorted_weights, weight_list, signals_alloted, weights_assigned = prepare_algorthim([(1, 22), (2, 6), (3, 7), (4, 14)])
#     n += 1
#     print(n)


# print(traffic_algorithm([(1, 24), (2, 4), (3, 10), (4, 9)]))


# print(time_left)
# print(signals_alloted)
# print(weights_assigned)
# print(allocation)
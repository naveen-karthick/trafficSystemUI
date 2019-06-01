from algorithm import traffic_algorithm, process_images
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import json
from collections import OrderedDict

class SimpleEcho(WebSocket):

    def handleMessage(self):
        print(self.data)
        parsed_data = json.loads(self.data)
        weights = OrderedDict()
        if parsed_data['type'] == 'live':
            print(int(parsed_data['frame']))
            allocation, weights = traffic_algorithm(process_images(int(parsed_data['frame'])),-1,-1)
            organizedSlots = []
            for individual_slot in allocation:
                if individual_slot is not None:
                    for value in individual_slot:
                        slot = {}
                        slot['lane1'] = value[0]
                        slot['lane2'] = value[1]
                        slot['lane1Direction'] = value[2]
                        slot['lane2Direction'] = value[3]
                        slot['durationOpen'] = value[4]
                        organizedSlots.append(slot)
            jsonOutput = {}
            jsonOutput['slots'] = organizedSlots
            for key,value in weights.items():

                jsonOutput['lane'+str(key)+'Weight'] = value
            jsonObject = json.dumps(jsonOutput)
            self.sendMessage(jsonObject)
        elif parsed_data['type'] == 'incoming_traffic':
            allocation, weights = traffic_algorithm(process_images(int(parsed_data['frame'])),int(parsed_data['weight']),int(parsed_data['id']))
            organizedSlots = []
            for individual_slot in allocation:
                if individual_slot is not None:
                    for value in individual_slot:
                        slot = {}
                        slot['lane1'] = value[0]
                        slot['lane2'] = value[1]
                        slot['lane1Direction'] = value[2]
                        slot['lane2Direction'] = value[3]
                        slot['durationOpen'] = value[4]
                        organizedSlots.append(slot)
            jsonOutput = {}
            jsonOutput['slots'] = organizedSlots
            for key,value in weights.items():

                jsonOutput['lane'+str(key)+'Weight'] = value
            jsonObject = json.dumps(jsonOutput)
            self.sendMessage(jsonObject)
        else :
            self.sendMessage('Invalid Data')
        # echo message back to client
        # if 'send me live traffic' in self.data:
        #     output = traffic_algorithm(process_images(1))
        #     self.sendMessage(output)
        # else:
        #     self.sendMessage('Invalid')




    def handleConnected(self):
        print(self.address, 'connected')

    def handleClose(self):
        print(self.address, 'closed')

server = SimpleWebSocketServer('', 8001, SimpleEcho)
server.serveforever()
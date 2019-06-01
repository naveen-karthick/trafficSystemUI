var pythonWebsocketConnection;
var nodeWebSocketConnection;
var trafficData;
var trafficSystem;
var trafficId = 1;
var frameCount = 0;
var slotIndex = 0;
var frame = 1;
var initialValue = 1;
var json = [];
var nodeWebSocketUrl = 'd91f03ee.ngrok.io';
var phpUrl = '5db58243.ngrok.io';
var outputFromPython;
var trafficAlert = false;
var trafficAlertId = -1
var trafficAlertLane;
var trafficAlertDensity;
var ambulanceEmergency = false;
var ambulanceLane = -1;
var ambulancePassed = false;
var ambulanceThresholdTime = 30000;
// var yellowLightDelay = 2000;
var yellowToGreenDelay = 1000;
var yellowToRedDelay = 4000;
var weightThresholdToNotifyTraffic = 20;
var sequentialAlgoDelay = 30000;
var sameLaneAmbulance = false;

var timerSpeed = 1;

/* Establishing Connection to Node Websoket */
function establishConnectionwithNodeWebsocket() {
    nodeWebSocketConnection = new WebSocket('ws://' + nodeWebSocketUrl + ':80');
    nodeWebSocketConnection.onopen = function () {
        // connection is opened and ready to use
        console.log('Connected to node websocket');
        nodeWebSocketConnection.send('{"id":' + trafficId + ',"type":"traffic"}');
    };

    nodeWebSocketConnection.onerror = function (error) {
        // an error occurred when sending/receiving data
    };
    nodeWebSocketConnection.onmessage = function (message) {
        console.log('Receiving alert from node websockeet');
        try {
            console.log(message.data);
            let nodeData = JSON.parse(message.data);
            if (nodeData.type === 'traffic_alert') {
                if (!trafficAlert) {
                    trafficAlert = true;
                    trafficAlertLane = nodeData.lane;
                    trafficAlertId = nodeData.trafficId;
                    trafficAlertDensity = nodeData.trafficDensity;
                    // pythonWebsocketConnection.send('{"frame":"' + frame + '","type":"incoming_traffic","lane":' + nodeData.lane + ',"traffic_density":' + nodeData.trafficDensity + '}');
                } else {
                    console.log('queue is full');
                }
            } else if (nodeData.type === 'Ambulance_alert') {
                if (!ambulanceEmergency) {
                    if (nodeData.state === 'clear') {
                        ambulanceEmergency = true;
                        ambulanceLane = nodeData.lane;
                    }
                } else {
                    if (nodeData.state === 'crossed') {
                        ambulancePassed = true;
                    } else {
                        console.log('ambulance queue is full');
                    }

                }
            }
        } catch (err) {
            console.log('invalid message format');
        }
    };
}

/* Send signal to nearby Traffic through Node websocket to inform there is a traffic heading their way */

function sendSignalToNearbyTraffic(valueOfLane, weight) {
    laneToAlert = valueOfLane;
    let nearbyTrafficId = trafficSystem['nearby_signal_id_' + laneToAlert];
    nodeWebSocketConnection.send(JSON.stringify({
        "id": trafficId, "type": "traffic_alert", "nearbyTrafficId": nearbyTrafficId, "weight": weight
    }));
}

window.onload = function () {
    initialize();
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200) {
            // Typical action to be performed when the document is ready:
            trafficData = JSON.parse(xhttp.responseText);
            trafficSystem = trafficData.message;
            console.log(trafficSystem);
        }
    };
    xhttp.open("GET", "http://" + phpUrl + "/traffic-service/traffic-signals/" + trafficId, true);
    xhttp.send();

    /* Establish Connection with python websocket to get input on image data */

    pythonWebsocketConnection = new WebSocket('ws://127.0.0.1:8001');
    var inputFromImageAlgo = false;
    document.getElementById('image-algo').classList.add('display-none');
    pythonWebsocketConnection.onopen = function () {
        // connection is opened and ready to use
        console.log('Connected to python websocket');
        pythonWebsocketConnection.send('{"id":' + trafficId + ',"type":"traffic"}');
        document.getElementById('process-live-traffic').addEventListener('click', () => {
            frame = (frameCount * 3) + trafficId;
            pythonWebsocketConnection.send('{"frame":"' + frame + '","type":"live"}');

            frameCount++;

        })
    };

    pythonWebsocketConnection.onerror = function (error) {
        // an error occurred when sending/receiving data
    };
    pythonWebsocketConnection.onmessage = function (message) {

        try {
            outputFromPython = JSON.parse(message.data);
            json = outputFromPython.slots;
            console.log(json);
            slotIndex = 0;
            let totalWeight = 0;
            for (let j = 1; j <= 4; j++) {
                document.getElementById('lane-' + j + '-image').src = "./algo-images/contour" + frame + '' + j + ".jpg";
                if (Number(json['lane' + j + 'Weight']) > 0) {
                    totalWeight += json['lane' + j + 'Weight'];
                }
            }
            inputFromImageAlgo = true;
            document.getElementById('image-algo').classList.remove('display-none');
            initialValue = 1;
            initialize();

            for (let i = 1; i <= 4; i++) {
                if (trafficSystem['signal_lane_' + i] === 1) {
                    sendSignalToNearbyTraffic(i);
                }
            }
        } catch (e) {
            console.log('This doesn\'t look like a valid JSON: ',
                message.data);
            return;
        }

        // handle incoming message
    };

    /* Establish Connection with node websocket to get signals on 
    incoming traffic or to notify other traffic signals or to clear route for ambulance */
    establishConnectionwithNodeWebsocket();

    /* Initialize the values of traffic such that all the signals are red at start */
    function initialize() {
        for (let i3 = 1; i3 <= 4; i3++) {
            if (!(i3 == ambulanceLane && sameLaneAmbulance)) {
                document.getElementById('lane' + i3 + '-Red').classList.add('lampRed');
                document.getElementById('lane' + i3 + '-Yellow').classList.remove('lampYellow');
                document.getElementById('lane' + i3 + '-Green').classList.remove('up-arrow');
                document.getElementById('lane' + i3 + '-Green-Right').classList.remove('right-arrow');
                document.getElementById('lane' + i3 + '-Green-left').classList.add('left-arrow');
                document.getElementById('lane-' + i3 + '-ped').classList.add('display-none');
                document.getElementById('timer-' + i3).innerHTML = "000";
            }
        }
        turnOnSequentialAlgorithm();
    }


    async function switchLights() {
        if (inputFromImageAlgo) {
            if (slotIndex < json.length) {
                let firstLane = json[slotIndex].lane1;
                let secondLane = json[slotIndex].lane2;
                let pastFirstLane;
                let pastSecondlane;
                if ((slotIndex - 1) >= 0) {
                    pastFirstLane = json[slotIndex - 1].lane1;
                    pastSecondlane = json[slotIndex - 1].lane2;
                }
                let oneLane = false;
                if (json[slotIndex].lane1 !== -1 && json[slotIndex].lane2 !== -1) {
                    /* check if lane 1 was opened already to prevent yellow light from showing */
                    if (!((slotIndex - 1) >= 0 && (pastFirstLane === firstLane || pastSecondlane === firstLane))) {
                        document.getElementById('lane' + firstLane + '-Yellow').classList.add('lampYellow');
                    }
                    /* check if lane 2 was opened already to prevent yellow light from showing */
                    if (!((slotIndex - 1) >= 0 && (pastFirstLane === secondLane || pastSecondlane === secondLane))) {
                        document.getElementById('lane' + secondLane + '-Yellow').classList.add('lampYellow');
                    }
                    await timer(yellowToGreenDelay);
                    /* lane 1 */
                    document.getElementById('lane' + firstLane + '-Yellow').classList.remove('lampYellow');
                    document.getElementById('lane' + firstLane + '-Red').classList.remove('lampRed');
                    if (json[slotIndex].lane1Direction === 'straight') {
                        document.getElementById('lane' + firstLane + '-Green').classList.add('up-arrow');
                    } else {
                        document.getElementById('lane' + firstLane + '-Green-Right').classList.add('right-arrow');
                    }

                    /* lane 2 */
                    document.getElementById('lane' + secondLane + '-Yellow').classList.remove('lampYellow');
                    document.getElementById('lane' + secondLane + '-Red').classList.remove('lampRed');
                    if (json[slotIndex].lane2Direction === 'straight') {
                        document.getElementById('lane' + secondLane + '-Green').classList.add('up-arrow');
                    } else {
                        document.getElementById('lane' + secondLane + '-Green-Right').classList.add('right-arrow');
                    }
                } else {
                    oneLane = true;
                    /* check if lane 1 was opened already to prevent yellow light from showing */
                    if (!((slotIndex - 1) >= 0 && (pastFirstLane === firstLane || pastSecondlane === firstLane))) {
                        document.getElementById('lane' + firstLane + '-Yellow').classList.add('lampYellow');
                        await timer(yellowToGreenDelay);
                        document.getElementById('lane' + firstLane + '-Yellow').classList.remove('lampYellow');
                        document.getElementById('lane' + firstLane + '-Red').classList.remove('lampRed');
                        document.getElementById('lane' + firstLane + '-Green').classList.add('up-arrow');
                        document.getElementById('lane' + firstLane + '-Green-Right').classList.add('right-arrow');
                    } else {
                        document.getElementById('lane' + firstLane + '-Yellow').classList.remove('lampYellow');
                        document.getElementById('lane' + firstLane + '-Red').classList.remove('lampRed');
                        document.getElementById('lane' + firstLane + '-Green').classList.add('up-arrow');
                        document.getElementById('lane' + firstLane + '-Green-Right').classList.add('right-arrow');
                    }

                }

                // checkForPedestrian(slotIndex);

                let futureFirstLane;
                let futureSecondlane;
                if ((slotIndex + 1) < json.length) {
                    futureFirstLane = json[slotIndex + 1].lane1;
                    futureSecondlane = json[slotIndex + 1].lane2;
                }
                if (json[slotIndex].lane1 !== -1) {
                    if (json[slotIndex].lane1 === futureFirstLane || json[slotIndex].lane1 === futureSecondlane &&
                        json[slotIndex].lane2 !== -1) {
                        displayTimer(json[slotIndex].lane1, parseInt(json[slotIndex].durationOpen + (yellowToRedDelay / 1000)));
                    } else {
                        displayTimer(json[slotIndex].lane1, parseInt(json[slotIndex].durationOpen));
                    }
                }
                if (json[slotIndex].lane2 !== -1) {
                    if (json[slotIndex].lane2 === futureFirstLane || json[slotIndex].lane2 === futureSecondlane &&
                        json[slotIndex].lane1 !== -1) {
                        displayTimer(json[slotIndex].lane2, parseInt(json[slotIndex].durationOpen + (yellowToRedDelay / 1000)));
                    } else {
                        displayTimer(json[slotIndex].lane2, parseInt(json[slotIndex].durationOpen));
                    }
                }

                await timer(json[slotIndex].durationOpen * 1000);
                console.log('weight of traffic density ' + outputFromPython['lane' + json[slotIndex].lane1 + 'Weight']);
                // if (outputFromPython['lane' + json[slotIndex].lane1 + 'Weight'] > weightThresholdToNotifyTraffic) {
                //     sendSignalToNearbyTraffic(JSON.stringify(slotIndex));
                // } else if (json[slotIndex].lane2 !== -1 &&
                //     Number(outputFromPython['lane' + json[slotIndex].lane1 + 'Weight'] + outputFromPython['lane' + json[slotIndex].lane2 + 'Weight']) > weightThresholdToNotifyTraffic) {
                //     sendSignalToNearbyTraffic(JSON.stringify(slotIndex));
                // }
                if (!sameLaneAmbulance) {
                    if ((slotIndex + 1) < json.length) {
                        futureFirstLane = json[slotIndex + 1].lane1;
                        futureSecondlane = json[slotIndex + 1].lane2;
                    }

                    if (json[slotIndex].lane1 !== -1 && json[slotIndex].lane2 !== -1) {
                        /* check if lane 1 is opened again to prevent red light from showing */
                        if (!((slotIndex + 1) < json.length && (futureFirstLane === firstLane || futureSecondlane === firstLane))) {
                            if (json[slotIndex].lane1Direction === 'straight') {
                                document.getElementById('lane' + firstLane + '-Green').classList.remove('up-arrow');
                            } else {
                                document.getElementById('lane' + firstLane + '-Green-Right').classList.remove('right-arrow');
                            }
                            document.getElementById('lane' + firstLane + '-Yellow').classList.add('lampYellow');
                            displayTimer(json[slotIndex].lane1, yellowToRedDelay / 1000);
                        }

                        /* check if lane 2 is opened again to prevent red light from showing */
                        if (!((slotIndex + 1) < json.length && (futureFirstLane === secondLane || futureSecondlane === secondLane))) {
                            if (json[slotIndex].lane2Direction === 'straight') {
                                document.getElementById('lane' + secondLane + '-Green').classList.remove('up-arrow');
                            } else {
                                document.getElementById('lane' + secondLane + '-Green-Right').classList.remove('right-arrow');
                            }
                            document.getElementById('lane' + secondLane + '-Yellow').classList.add('lampYellow');
                            displayTimer(json[slotIndex].lane2, yellowToRedDelay / 1000);
                        }

                        await timer(yellowToRedDelay);
                        if (!((slotIndex + 1) < json.length && (futureFirstLane === firstLane || futureSecondlane === firstLane))) {
                            document.getElementById('lane' + firstLane + '-Yellow').classList.remove('lampYellow');
                            document.getElementById('lane' + firstLane + '-Red').classList.add('lampRed');
                        }
                        if (!((slotIndex + 1) < json.length && (futureFirstLane === secondLane || futureSecondlane === secondLane))) {
                            document.getElementById('lane' + secondLane + '-Yellow').classList.remove('lampYellow');
                            document.getElementById('lane' + secondLane + '-Red').classList.add('lampRed');
                        }

                    } else {
                        /* check if lane 1 is opened again to prevent red light from showing */
                        if (!((slotIndex + 1) < json.length && (futureFirstLane === firstLane || futureSecondlane === firstLane))) {
                            document.getElementById('lane' + firstLane + '-Green').classList.remove('up-arrow');
                            document.getElementById('lane' + firstLane + '-Green-Right').classList.remove('right-arrow');
                            document.getElementById('lane' + firstLane + '-Yellow').classList.add('lampYellow');
                            displayTimer(json[slotIndex].lane1, yellowToRedDelay / 1000);
                            await timer(yellowToRedDelay);
                        }
                        if (!((slotIndex + 1) < json.length && (futureFirstLane === firstLane || futureSecondlane === firstLane))) {
                            document.getElementById('lane' + firstLane + '-Yellow').classList.remove('lampYellow');
                            document.getElementById('lane' + firstLane + '-Red').classList.add('lampRed');
                        }
                        /* Edge Case */
                        if (futureFirstLane === firstLane) {
                            if (json[slotIndex + 1].lane1Direction === 'straight') {
                                document.getElementById('lane' + firstLane + '-Green-Right').classList.remove('right-arrow');
                            } else {
                                document.getElementById('lane' + firstLane + '-Green').classList.remove('up-arrow');
                            }
                        } else if (futureSecondlane === firstLane) {
                            if (json[slotIndex + 1].lane2Direction === 'straight') {
                                document.getElementById('lane' + firstLane + '-Green-Right').classList.remove('right-arrow');
                            } else {
                                document.getElementById('lane' + firstLane + '-Green').classList.remove('up-arrow');
                            }
                        }
                    }
                }
                if (!ambulanceEmergency) {
                    slotIndex++;
                    switchLights();
                } else {
                    slotIndex++;
                    initialize();
                }
            } else {
                if (frameCount < 3) {
                    frame = (frameCount * 3) + trafficId;
                    if (!trafficAlert) {
                        pythonWebsocketConnection.send('{"frame":"' + frame + '","type":"live"}');
                    } else {
                        trafficAlert = false;
                        pythonWebsocketConnection.send('{"frame":"' + frame + '","type":"incoming_traffic", "id":'
                            + trafficAlertId + ', "weight":' + trafficAlertDensity + '}');
                    }

                    frameCount++;
                } else {
                    inputFromImageAlgo = false;
                    document.getElementById('image-algo').classList.add('display-none');
                    initialValue = 1;
                    initialize();
                }
            }
        }
        function checkForPedestrian(index) {
            if (!ambulanceEmergency) {
                /* Check for pedestrian */
                for (let k = 1; k <= 4; k++) {
                    let currentLane = k;
                    let firstLane = json[index].lane1;
                    let secondLane = json[index].lane2;
                    let oppositeLane = k + 2 > 4 ? k - 2 : k + 2;
                    let adjacentLane = k - 1 <= 0 ? k + 3 : k - 1;
                    let laneLeftToClose = k + 1 > 4 ? k - 3 : k + 1;
                    if (firstLane !== currentLane && secondLane !== currentLane
                        && firstLane !== oppositeLane && secondLane !== oppositeLane
                        && trafficSystem['signal_lane_' + k] === 1) {
                        if (firstLane === adjacentLane || secondLane === adjacentLane) {
                            let canPedestrianCross = true;
                            if (firstLane === adjacentLane) {
                                if (json[index].lane1Direction === 'right' || secondLane === -1) {
                                    canPedestrianCross = false;
                                }
                            }
                            if (secondLane === adjacentLane) {
                                if (json[index].lane2Direction === 'right') {
                                    canPedestrianCross = false;
                                }
                            }
                            if (canPedestrianCross) {
                                switchPedestrianSignal(laneLeftToClose, k, json[index].durationOpen);
                            }
                        } else {
                            switchPedestrianSignal(laneLeftToClose, k, json[index].durationOpen);
                        }
                    }
                }
                async function switchPedestrianSignal(_leftLaneToClose, index, _duration) {
                    if (!ambulanceEmergency) {
                        document.getElementById('lane' + _leftLaneToClose + '-Green-left').classList.remove('left-arrow');
                        document.getElementById('lane-' + index + '-ped').classList.remove('display-none');
                        await timer(_duration * 1000);
                        document.getElementById('lane' + _leftLaneToClose + '-Green-left').classList.add('left-arrow');
                        document.getElementById('lane-' + index + '-ped').classList.add('display-none');
                    }
                }
            }
        }
    }



    async function turnOnSequentialAlgorithm() {
        if (!inputFromImageAlgo && !ambulanceEmergency) {
            if (initialValue > 4) {
                initialValue = 1;
            }
            if (initialValue === 1) {
                for (let i = 2; i <= 4; i++) {
                    let waitTime = ((sequentialAlgoDelay + yellowToGreenDelay + yellowToRedDelay) * (i - 1)) / 1000;
                    displayTimerforSequentialAlgo(i, waitTime);
                }
            }
            document.getElementById('lane' + initialValue + '-Yellow').classList.add('lampYellow');
            await timer(yellowToGreenDelay);
            document.getElementById('lane' + initialValue + '-Red').classList.remove('lampRed');
            document.getElementById('lane' + initialValue + '-Yellow').classList.remove('lampYellow');
            document.getElementById('lane' + initialValue + '-Green').classList.add('up-arrow');
            document.getElementById('lane' + initialValue + '-Green-Right').classList.add('right-arrow');
            displayTimerforSequentialAlgo(initialValue, sequentialAlgoDelay / 1000);
            pedestrianSignal(initialValue);
            await timer(sequentialAlgoDelay);
            if (!inputFromImageAlgo) {
                document.getElementById('lane' + initialValue + '-Green').classList.remove('up-arrow');
                document.getElementById('lane' + initialValue + '-Green-Right').classList.remove('right-arrow');
                document.getElementById('lane' + initialValue + '-Yellow').classList.add('lampYellow');
                displayTimerforSequentialAlgo(initialValue, yellowToRedDelay / 1000);
                await timer(yellowToRedDelay);
                let waitTime = sequentialAlgoDelay + yellowToGreenDelay + yellowToRedDelay;
                if (!ambulanceEmergency && !inputFromImageAlgo) {
                    displayTimerforSequentialAlgo(initialValue, waitTime * 3 / 1000);
                    if (!inputFromImageAlgo) {
                        document.getElementById('lane' + initialValue + '-Yellow').classList.remove('lampYellow');
                        document.getElementById('lane' + initialValue + '-Red').classList.add('lampRed');
                        if (!ambulanceEmergency) {
                            initialValue++;
                            turnOnSequentialAlgorithm();
                        } else {
                            initialize();
                        }
                    }
                } else if (ambulanceEmergency) {
                    initialize();
                }
            }
        } else if (ambulanceEmergency) {
            switchLaneForAmbulanceEmergency(ambulanceLane);

        } else {
            switchLights();
        }
    }

    function displayTimerforSequentialAlgo(_lane, waitTime) {
        if (waitTime < 100) {
            if (waitTime < 10) {
                document.getElementById('timer-' + _lane).innerHTML = "00" + waitTime;
            } else {
                document.getElementById('timer-' + _lane).innerHTML = "0" + waitTime;
            }
        } else {
            document.getElementById('timer-' + _lane).innerHTML = waitTime;
        }
        let interval = setInterval(() => {
            waitTime -= 1;
            if (inputFromImageAlgo) {
                return;
            }
            if (waitTime > 6 && ambulanceEmergency) {
                if (initialValue !== _lane) {
                    document.getElementById('timer-' + _lane).innerHTML = "000";
                    clearInterval(interval);
                    return;
                }
                waitTime = 6;
            }
            if (waitTime < 1) {
                clearInterval(interval);
            }
            if (waitTime < 100) {
                if (waitTime < 10) {
                    document.getElementById('timer-' + _lane).innerHTML = "00" + waitTime;
                } else {
                    document.getElementById('timer-' + _lane).innerHTML = "0" + waitTime;
                }
            } else {
                document.getElementById('timer-' + _lane).innerHTML = waitTime;
            }
        }, 1000 / timerSpeed);

    }
    function displayTimer(_lane, waitTime) {
        if (waitTime < 100) {
            if (waitTime < 10) {
                document.getElementById('timer-' + _lane).innerHTML = "00" + waitTime;
            } else {
                document.getElementById('timer-' + _lane).innerHTML = "0" + waitTime;
            }
        } else {
            document.getElementById('timer-' + _lane).innerHTML = waitTime;
        }
        let interval = setInterval(() => {
            waitTime -= 1;
            if (_lane == ambulanceLane) {
                sameLaneAmbulance = true;
                document.getElementById('timer-' + _lane).innerHTML = "120";
                clearInterval(interval);
                return;
            } else if (waitTime > 6 && ambulanceEmergency) {
                waitTime = 6;
            }
            if (waitTime < 1) {
                clearInterval(interval);
            }
            if (waitTime < 100) {
                if (waitTime < 10) {
                    document.getElementById('timer-' + _lane).innerHTML = "00" + waitTime;
                } else {
                    document.getElementById('timer-' + _lane).innerHTML = "0" + waitTime;
                }
            } else {
                document.getElementById('timer-' + _lane).innerHTML = waitTime;
            }
        }, 1000 / timerSpeed);

    }
    async function pedestrianSignal(_lane) {
        let laneToOpenForPedestrian;
        if (_lane === 1) {
            laneToOpenForPedestrian = 4;
        } else {
            laneToOpenForPedestrian = _lane - 1;
        }
        document.getElementById('lane' + _lane + '-Green-left').classList.remove('left-arrow');
        document.getElementById('lane-' + laneToOpenForPedestrian + '-ped').classList.remove('display-none');
        await timer(sequentialAlgoDelay / 2);
        if (!inputFromImageAlgo) {
            document.getElementById('lane' + _lane + '-Green-left').classList.add('left-arrow');
            document.getElementById('lane-' + laneToOpenForPedestrian + '-ped').classList.add('display-none');
        }
    }

    async function switchLaneForAmbulanceEmergency(lane) {
        if (!sameLaneAmbulance) {
            document.getElementById('lane' + lane + '-Yellow').classList.add('lampYellow');
            await timer(yellowToGreenDelay);
            document.getElementById('lane' + lane + '-Red').classList.remove('lampRed');
            document.getElementById('lane' + lane + '-Yellow').classList.remove('lampYellow');
            document.getElementById('lane' + lane + '-Green').classList.add('lampGreen');
            document.getElementById('lane' + lane + '-Green-Right').classList.add('arrow-right');
        } else {
            document.getElementById('lane' + lane + '-Green').classList.add('lampGreen');
            document.getElementById('lane' + lane + '-Green-Right').classList.add('arrow-right');
        }
        document.getElementById('timer-' + lane).innerHTML = "120";
        /* keep checking if the ambulance has passed */
        var check = setInterval(() => {
            if (ambulancePassed) {
                if (ambulanceEmergency) {
                    ambulanceEmergency = false;
                    sameLaneAmbulance = false;
                    resetAmbulanceClearance();
                    clearInterval(check);
                }
            }
        }, 5000);

        /* Ambulance Threshold time has been reached */
        await timer(ambulanceThresholdTime, true);
        if (ambulanceEmergency) {
            ambulanceEmergency = false;
            sameLaneAmbulance = false;
            resetAmbulanceClearance();
        }


        async function resetAmbulanceClearance() {
            ambulanceLane = -1;
            document.getElementById('lane' + lane + '-Green').classList.remove('lampGreen');
            document.getElementById('lane' + lane + '-Green-Right').classList.remove('arrow-right');
            document.getElementById('lane' + lane + '-Yellow').classList.add('lampYellow');
            await timer(yellowToRedDelay, true);
            document.getElementById('lane' + lane + '-Yellow').classList.remove('lampYellow');
            document.getElementById('lane' + lane + '-Red').classList.add('lampRed');
            document.getElementById('timer-' + lane).innerHTML = "000";
            if (frameCount < 3) {
                if (inputFromImageAlgo) {
                    switchLights();
                } else {
                    frame = (frameCount * 3) + trafficId;
                    if (!trafficAlert) {
                        pythonWebsocketConnection.send('{"frame":"' + frame + '","type":"live"}');
                    } else {
                        trafficAlert = false;
                        pythonWebsocketConnection.send('{"frame":"' + frame + '","type":"incoming_traffic", "lane":'
                            + trafficAlertLane + ', "weight":' + trafficAlertDensity + '}');
                    }
                    frameCount++;
                }
            } else {
                inputFromImageAlgo = false;
                document.getElementById('image-algo').classList.add('display-none');
                initialValue = 1;
                initialize();
            }


        }
    }



    function timer(_time, isAmbulance) {
        return new Promise((resolve, reject) => {
            let time = (_time / 1000) - 1;
            let interval = setInterval(() => {
                if (ambulanceEmergency && !isAmbulance) {
                    if (time > 6) {
                        time = 6;
                    }
                }
                if (time <= 0) {
                    clearInterval(interval);
                    resolve(true);
                }
                time -= 1;
            }, 1000 / timerSpeed);


            // setTimeout(() => {
            //     resolve(true);
            // }, _time);
        })
    }
}
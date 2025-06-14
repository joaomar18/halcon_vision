let socket = null;
let ws_connected = false;
let reconnectInterval = 2000;

function process_message(message){
    let peripheral = message['peripheral'];
    let type = message['type'];
    let data = message['data'];
    if(peripheral == "manager"){
        if(type == 'response'){
            for(let vision_device of data){
                vision_manager.add_vision_device(vision_device);
                let new_device = document.createElement("option");
                new_device.innerHTML = vision_device;
                document.getElementById("camera_devices_select").appendChild(new_device);
                if(vision_manager.active_device == null){
                    vision_manager.select_device(vision_device);
                    document.getElementById("camera_devices_select").value = vision_device;
                    document.getElementById("active_camera_name").innerText = vision_device;
                }
            }
        }
    }
    if(peripheral in vision_manager.vision_devices){
        let section = message['section'];
        let value = message['value'];
        if(type == "status"){
            if(section == 'inputs_register'){
                vision_manager.vision_devices[peripheral].inputs.inputs_register = JSON.parse(JSON.stringify(value));
            }
            else if(section == "inputs_variables"){
                vision_manager.vision_devices[peripheral].inputs.inputs_variables = JSON.parse(JSON.stringify(value));
            }
            else if(section == "status"){
                vision_manager.vision_devices[peripheral].outputs.status = JSON.parse(JSON.stringify(value));
            }
            else if(section == "statistics"){
                vision_manager.vision_devices[peripheral].outputs.statistics = JSON.parse(JSON.stringify(value));
            }
            else if(section == "program_number_acknowledge"){
                vision_manager.vision_devices[peripheral].outputs.program_number_acknowledge = JSON.parse(JSON.stringify(value));
            }
            else if(section == "outputs_bool_register"){
                vision_manager.vision_devices[peripheral].outputs.outputs_bool_register = JSON.parse(JSON.stringify(value));
            }
            else if(section == "outputs_register"){
                vision_manager.vision_devices[peripheral].outputs.outputs_register = JSON.parse(JSON.stringify(value));
            }
            else if(section == "outputs_variables"){
                vision_manager.vision_devices[peripheral].outputs.outputs_variables = JSON.parse(JSON.stringify(value));
            }
        }
    }
}

function connectWebSocket() {

    socket = new WebSocket('ws://localhost:8080');

    socket.onopen = function(event) {
        ws_connected = true;
        retryCount = 0;
        let message = {
            'peripheral': 'frontend',
            'type': 'status',
            'data': 'connected'
        };
        socket.send(JSON.stringify(message));
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        process_message(data)
    };

    socket.onclose = function(event) {
        ws_connected = false;
        console.log('WebSocket connection closed:', event);
        attemptReconnect();
    }

    socket.onerror = function(error) {
        ws_connected = false;
        console.log('WebSocket error:', error);
        socket.close();
    };
}

function attemptReconnect() {
    console.log('Attempting to reconnect...');
    setTimeout(function() {
        connectWebSocket();
    }, reconnectInterval);
}

connectWebSocket();
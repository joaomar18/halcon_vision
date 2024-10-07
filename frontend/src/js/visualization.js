let header_div = document.getElementById("camera_image_header");
let left_div = document.getElementById("camera_image_left");
let right_div = document.getElementById("camera_image_right");
let footer_div = document.getElementById("footer");
let sidebar_div = document.getElementById("side_bar");
let camera_div = document.getElementById("camera_div");

let inputs_outputs_state = document.getElementById("inputs_outputs_state");

function invert_inputs_outputs_display(){
    if(header_div.classList.contains("hidden")){
        header_div.classList.remove("hidden");
        left_div.classList.remove("hidden");
        right_div.classList.remove("hidden");
        footer_div.classList.remove("hidden");
        sidebar_div.classList.remove("amplify");
        camera_div.classList.remove("amplify");
        inputs_outputs_state.style.backgroundColor = "rgb(0,255,0)";
    }    
    else{
        header_div.classList.add("hidden");
        left_div.classList.add("hidden");
        right_div.classList.add("hidden");
        footer_div.classList.add("hidden");
        sidebar_div.classList.add("amplify");
        camera_div.classList.add("amplify");
        inputs_outputs_state.style.backgroundColor = "rgb(255,0,0)";
    }
}



let connection_state = document.getElementById("connection_status");
let last_connection_status = false;
let check_connection_handler = setInterval(check_connection, 10);

function check_connection(){
    if(ws_connected && !last_connection_status){
        connection_state.style.backgroundColor = "rgb(0, 255, 0)";
        last_connection_status = true;
    }
    else if(!ws_connected && last_connection_status){
        connection_state.style.backgroundColor = "rgb(255, 0, 0)";
        last_connection_status = false;
    }
}

let control_state = document.getElementById("control_state");
let control_status = true;
let trigger_button_element = document.getElementById("trigger_button");

function invert_control_status(){
    if(control_status){
        trigger_button_element.style.backgroundColor = "rgb(216,216,216)";
        trigger_button_element.style.cursor = "auto";
        trigger_button_element.disabled = true;
        control_state.style.backgroundColor = "rgb(255, 0, 0)";
        control_status = false;
    }
    else{
        trigger_button_element.style.backgroundColor = "rgb(127,127,127)";
        trigger_button_element.style.cursor = "pointer";
        control_state.style.backgroundColor = "rgb(0, 255, 0)";
        control_status = true;
    }
}

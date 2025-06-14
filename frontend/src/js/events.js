function camera_change(){
    let camera_selected = document.getElementById("camera_devices_select").value;
    let camera_name = document.getElementById("active_camera_name");
    camera_name.innerText = camera_selected;
    vision_manager.select_device(camera_selected);
}


document.getElementById("program_number_value").addEventListener('input', function() {
    this.value = Number(this.value);
    if(this.value > 999){
        this.value = 999;
    }
    else if(this.value < 0){
        this.value = 0;
    }
    this.value = this.value.padStart(3, '0');
});

document.getElementById("program_number_value").addEventListener('blur', function() {
    this.value = Number(this.value);
    this.value = this.value.padStart(3, '0');
});

function program_number_changed(){
    vision_manager.active_device.set_program_number(document.getElementById("program_number_value").value); 
    vision_manager.active_device.set_program_change(true);
}

function trigger_button(){
    if(control_status){
        vision_manager.active_device.set_trigger(true);
    }
}

function reset_button(){
    if(control_status){
        vision_manager.active_device.set_reset(true);
    }
}

let continuous_trigger_state = false;

function continuous_trigger_button(){
    continuous_trigger_state = !continuous_trigger_state;
    document.getElementById("continuous_trigger_button").style.backgroundColor = continuous_trigger_state ? "rgb(0, 255, 0)" : "rgb(127, 127, 127)";
    vision_manager.active_device.set_continuous_trigger(continuous_trigger_state);
}
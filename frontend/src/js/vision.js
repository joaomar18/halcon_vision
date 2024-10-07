class VisionInputs{
    
    constructor(name){
        
        this.name = name;

        this.trigger = false;
        this.continuous_trigger = false;
        this.program_change = false;
        this.reset = false;
        this.program_number = null;
        this.inputs_register = new Array();
        this.inputs_variables = new Array();

        this.old_trigger = this.trigger;
        this.old_continous_trigger = this.continuous_trigger;
        this.old_program_change = this.program_change;
        this.old_reset = this.reset;
        this.old_program_number = this.program_number,
        this.old_inputs_register = [...this.inputs_register];
        this.old_inputs_variables = [...this.inputs_variables];

    }

}

class VisionOutputs{

    constructor(name){

        this.name = name;

        this.status = {'ready':false,
            'run':false,
            'trigger_acknowledge':false,
            'program_change_acknowledge':false,
            'trigger_error':false,
            'program_change_error':false,
            'new_image':false
        };

        this.statistics = {'min_run_time':0.0,
                        'run_time':0.0,
                        'max_run_time':0.0
        };
        this.program_number_acknowledge = null;
        this.outputs_register = new Array();
        this.outputs_variables = new Array();

        this.old_status = { ...this.status };
        this.old_statistics = { ...this.statistics };
        this.old_program_number_acknowledge = this.program_number_acknowledge;
        this.old_outputs_register = [...this.outputs_register];
        this.old_outputs_variables = [...this.outputs_variables];

    }

}

class VisionDevice{

    constructor(name){

        this.name = name;
        this.active = false;
        this.inputs = new VisionInputs(name);
        this.outputs = new VisionOutputs(name);

        this.startInputsChangeDetection();
        this.startOutputsChangeDetection();

        this.camera_image_element = document.getElementById("camera_image");

        this.status_elements = {'ready':document.getElementById("io_ready"),
                                'run':document.getElementById("io_run"),
                                'trigger_acknowledge':document.getElementById("io_trigger_ack"),
                                'program_change_acknowledge':document.getElementById("io_prog_change_ack"),
                                'trigger_error':document.getElementById("io_trigger_error"),
                                'program_change_error':document.getElementById("io_prog_change_error")};

        this.run_time_elements = {'min_run_time':document.getElementById("io_min_run_ime"),
                                  'run_time':document.getElementById("io_run_time"),
                                  'max_run_time':document.getElementById("io_max_run_time")};

        this.program_number_element = document.getElementById("program_number_value");

        this.inputs_table_element = document.getElementById("inputs_div");
        this.outputs_table_element = document.getElementById("outputs_div");

        this.inputs_elements = new Array();
        this.inputs_types = new Array();

        this.outputs_elements = new Array();
        this.outputs_types = new Array();

    }


    update_inputs_variables(){
        const inputs_variables = this.inputs_table_element.querySelectorAll("div");
        inputs_variables.forEach(div => div.remove());
        this.inputs_elements.length = 0;
        this.inputs_types.length = 0;
        let i = 0;
        for (let variable of this.inputs.old_inputs_variables) {
            if(variable != null){
                let variable_name = variable[0];
                let variable_type = variable[1];
                let variable_div = document.createElement("div");
                let variable_name_span = document.createElement("span");
                variable_name_span.className = "variable";
                variable_name_span.innerText = variable_name;
                let variable_type_span = document.createElement("span");
                variable_type_span.innerText = variable_type;
                variable_type_span.className = "type";
                let variable_input = document.createElement("input");
                variable_input.type = "number";
                this.inputs_elements.push(variable_input);
                this.inputs_types.push(variable_type);
                let currentIndex = i;
                variable_input.onchange = () => {
                    this.set_input_register(currentIndex, variable_type, variable_input.value);
                };

                variable_div.appendChild(variable_name_span);
                variable_div.appendChild(variable_type_span);
                variable_div.appendChild(variable_input);
                this.inputs_table_element.appendChild(variable_div);

                i++;
            }
        }
        this.update_inputs();
    }

    update_outputs_variables(){
        const outputs_variables = this.outputs_table_element.querySelectorAll("div");
        outputs_variables.forEach(div => div.remove());
        this.outputs_elements.length = 0;
        this.outputs_types.length = 0;
        let i = 0;
        for (let variable of this.outputs.old_outputs_variables) {
            if(variable != null){
                let variable_name = variable[0];
                let variable_type = variable[1];
                let variable_div = document.createElement("div");
                let variable_name_span = document.createElement("span");
                variable_name_span.className = "variable";
                variable_name_span.innerText = variable_name;
                let variable_type_span = document.createElement("span");
                variable_type_span.innerText = variable_type;
                variable_type_span.className = "type";
                let variable_output = document.createElement("input");
                variable_output.type = "text";
                variable_output.disabled = true;
                this.outputs_elements.push(variable_output);
                this.outputs_types.push(variable_type);
                variable_div.appendChild(variable_name_span);
                variable_div.appendChild(variable_type_span);
                variable_div.appendChild(variable_output);
                this.outputs_table_element.appendChild(variable_div);
                i++;
            }
        }
        this.update_outputs();
    }

    update_program_number(){
        this.program_number_element.value = Number(this.outputs.old_program_number_acknowledge);
        this.program_number_element.value = String(this.program_number_element.value).padStart(3, '0');
    }

    update_status(){
        this.status_elements['ready'].style.backgroundColor = this.outputs.status['ready'] ? "rgb(0, 255, 0)" : "rgb(255, 255, 255)";
        this.status_elements['run'].style.backgroundColor = this.outputs.status['run'] ? "rgb(255, 255, 0)" : "rgb(255, 255, 255)";
        this.status_elements['trigger_acknowledge'].style.backgroundColor = this.outputs.status['trigger_acknowledge'] ? "rgb(0, 255, 0)" : "rgb(255, 255, 255)";
        this.status_elements['program_change_acknowledge'].style.backgroundColor = this.outputs.status['program_change_acknowledge'] ? "rgb(0, 255, 0)" : "rgb(255, 255, 255)";
        this.status_elements['trigger_error'].style.backgroundColor = this.outputs.status['trigger_error'] ? "rgb(255, 0, 0)" : "rgb(255, 255, 255)";
        this.status_elements['program_change_error'].style.backgroundColor = this.outputs.status['program_change_error'] ? "rgb(255, 0, 0)" : "rgb(255, 255, 255)";
    }

    update_image(){
        const newImage = new Image();
        newImage.src = "../../hdevelop/"+this.name+"/output/output_image.jpg?t=" + new Date().getTime();
        newImage.onload = () => {
            this.camera_image_element.style.backgroundImage = "url('" + newImage.src + "')";
        };
    }

    update_min_run_time(){
        this.run_time_elements['min_run_time'].value = (this.outputs.statistics['min_run_time']*1000).toFixed(2) + " ms";
    }

    update_run_time(){
        this.run_time_elements['run_time'].value = (this.outputs.statistics['run_time']*1000).toFixed(2) + " ms";
    }

    update_max_run_time(){
        this.run_time_elements["max_run_time"].value = (this.outputs.statistics['max_run_time']*1000).toFixed(2) + " ms";
    }

    update_inputs(){
        let i = 0;
        for(let value of this.inputs.old_inputs_register){
            if(i >= this.inputs_elements.length){
                break;
            }
            this.inputs_elements[i].value = value;
            i++;
        }
    }

    update_outputs(){

        let i = 0;
        for(let value of this.outputs.old_outputs_register){
            if(i >= this.outputs_elements.length){
                break;
            }
            if(this.outputs_types[i] == 'float'){
                this.outputs_elements[i].value = Number(value).toFixed(2);
            }
            else if(this.outputs_types[i] == 'string'){
                this.outputs_elements[i].value = String(value);
            }
            else{
                this.outputs_elements[i].value = value;
            }
            i++;
        }
    }



    set_active(state){
        if(state){
            this.active = true;
            this.update_image();
            this.update_inputs_variables();
            this.update_inputs();
            this.update_status();
            this.update_min_run_time();
            this.update_run_time();
            this.update_max_run_time();
            this.update_outputs_variables();
            this.update_outputs();
            this.update_program_number();
        }
        else{
            this.active = false;
        }
    }

    set_trigger(state){
        if(this.active){
            if(this.inputs.trigger == false && this.outputs.status['trigger_acknowledge'] == false && state == true){
                let message = {'peripheral':this.name,
                    'type':'request',
                    'section':'control',
                    'data':'trigger',
                    'value':String(state)};
                socket.send(JSON.stringify(message));
                this.inputs.trigger = true;
            }
            else if(this.inputs.trigger == true && state == false){
                let message = {'peripheral':this.name,
                    'type':'request',
                    'section':'control',
                    'data':'trigger',
                    'value':String(state)};
                socket.send(JSON.stringify(message));
                this.inputs.trigger = false;
            }
        }
    }

    set_continuous_trigger(state){
        if(this.active){
            if(state){
                this.set_trigger(true);
            }
            this.inputs.continuous_trigger = state;
        }
    }

    set_program_change(state){
        if(this.active){
            let message = {'peripheral':this.name,
                'type':'request',
                'section':'control',
                'data':'program_change',
                'value':String(state)};      
            socket.send(JSON.stringify(message));
            this.inputs.program_change = state;
        }
    }

    set_reset(state){
        if(this.active){
            let message = {'peripheral':this.name,
                'type':'request',
                'section':'control',
                'data':'reset',
                'value':String(state)};      
            socket.send(JSON.stringify(message));
            this.inputs.reset = state;
        }
    }

    set_program_number(program_number){
        if(this.active){
            let message = {'peripheral':this.name,
                'type':'request',
                'section':'program_number',
                'value':String(program_number)};
            socket.send(JSON.stringify(message));
            this.inputs.program_number = program_number;
        }
    }
    set_input_register(index, type, value){
        if(this.active){
            let message = {'peripheral':this.name,
                'type':'request',
                'section':'inputs_register',
                'index':String(index),
                'value_type':String(type),
                'value':String(value)};
            socket.send(JSON.stringify(message));
            this.inputs.inputs_register[index] = value;            
        }
    }


    detectInputsChanges() {
        if (JSON.stringify(this.inputs.inputs_register) !== JSON.stringify(this.inputs.old_inputs_register)) {
            this.inputs.old_inputs_register = [...this.inputs.inputs_register];

            if(this.active){
                this.update_inputs();
            }
        }

        if (JSON.stringify(this.inputs.inputs_variables) != JSON.stringify(this.inputs.old_inputs_variables)) {
            this.inputs.old_inputs_variables = [...this.inputs.inputs_variables];

            if(this.active){
                this.update_inputs_variables();
            }
        }
    }

    detectOutputsChanges() {
        if (JSON.stringify(this.outputs.status) !== JSON.stringify(this.outputs.old_status)) {

            if(this.active){
               this.update_status();
            }
           
            if(this.outputs.status['new_image'] == true && this.outputs.old_status['new_image'] == false){
                if(this.active){
                    this.update_image();
                    if(this.inputs.continuous_trigger){
                        let new_trigger_handler = setInterval(() => {
                            if(this.outputs.status['ready']){
                                this.set_trigger(true);
                                clearInterval(new_trigger_handler);
                            }
                        },10);
                    }
                }
            }

            if(this.outputs.status['trigger_acknowledge'] == true && this.outputs.old_status['trigger_acknowledge'] == false
                || this.outputs.status['trigger_error'] == true && this.outputs.old_status['trigger_error'] == false){
                    this.set_trigger(false);
            }


            if(this.outputs.status['program_change_acknowledge'] == true && this.outputs.old_status['program_change_acknowledge'] == false
            || this.outputs.status['program_change_error'] == true && this.outputs.old_status['program_change_error'] == false){
                this.set_program_change(false);
            }

            this.outputs.old_status = { ...this.outputs.status };
        }

        if (JSON.stringify(this.outputs.statistics) !== JSON.stringify(this.outputs.old_statistics)) {
            if(this.active){
                if(this.outputs.statistics['min_run_time'] != this.outputs.old_statistics['min_run_time']){
                    this.update_min_run_time();
                }
                if(this.outputs.statistics['run_time'] != this.outputs.old_statistics['run_time']){
                    this.update_run_time();
                }
                if(this.outputs.statistics['max_run_time'] != this.outputs.old_statistics['max_run_time']){
                    this.update_max_run_time();
                }  
            }
   
            this.outputs.old_statistics = { ...this.outputs.statistics };
        }

        if (this.outputs.program_number_acknowledge !== this.outputs.old_program_number_acknowledge) {
            this.outputs.old_program_number_acknowledge = this.outputs.program_number_acknowledge;
            if(this.active){
                this.update_program_number();
            }
        }

        if (JSON.stringify(this.outputs.outputs_register) !== JSON.stringify(this.outputs.old_outputs_register)) {
            this.outputs.old_outputs_register = [...this.outputs.outputs_register];
            if(this.active){
                this.update_outputs();
            }
        }

        if (JSON.stringify(this.outputs.outputs_variables) !== JSON.stringify(this.outputs.old_outputs_variables)) {
            this.outputs.old_outputs_variables = [...this.outputs.outputs_variables];
            if(this.active){
                this.update_outputs_variables();
            }
        }
    }

    startInputsChangeDetection() {
        setInterval(() => {
            this.detectInputsChanges();
        }, 10);
    }

    startOutputsChangeDetection() {
        setInterval(() => {
            this.detectOutputsChanges();
        }, 10);
    }

}

class VisionManager{
    constructor(){
        this.vision_devices = {};
        this.active_device = null;
    }

    add_vision_device(name){
        this.vision_devices[name] = new VisionDevice(name);
    }

    select_device(name){

        for (let name in this.vision_devices) {
            this.vision_devices[name].set_active(false);
        }

        if(name in this.vision_devices){
            this.active_device = this.vision_devices[name]; 
            this.vision_devices[name].set_active(true);
        }
        else{
            this.active_device = null;
        }

    }
}

vision_manager = new VisionManager()


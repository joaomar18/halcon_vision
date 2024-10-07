from vision.data.inputs import VisionInputs
from vision.data.outputs import VisionOutputs
    
class VisionCommunication():
    
    def __init__(self, device_name: str, reg_size: int, init_program: int):

    ############################     P U B L I C     A T T R I B U T E S     ############################

        self.inputs = VisionInputs(device_name, reg_size, init_program)
        self.outputs = VisionOutputs(device_name, reg_size)
    
    ###########################     P R I V A T E     A T T R I B U T E S     ###########################



    ###############################     P U B L I C     M E T H O D S     ###############################



    ##############################     P R I V A T E     M E T H O D S     ##############################
class HalconVariable():

    def __init__(self, value = None):

    ############################     P U B L I C     A T T R I B U T E S     ############################

        self.value = value

    ###########################     P R I V A T E     A T T R I B U T E S     ###########################


    
    ###############################     P U B L I C     M E T H O D S     ###############################

    def set_value(self, value):
        self.value = value
    
    def get_type(self):
        return type(self.value)
    
    @staticmethod
    def serialize_list(list: list['HalconVariable']) -> list[str]:
        output = []
        for variable in list:
            output.append(str(variable.value))
        return output
    
    ##############################     P R I V A T E     M E T H O D S     ##############################

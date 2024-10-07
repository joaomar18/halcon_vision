from vision.procedure import create_vision_procedure

def create_pulley_camera(program_path:str):

    open = create_vision_procedure(program_directory=program_path,
                                                       name='OpenCamera',
                                                       output_control={'AcqHandle': 'handle'})

    trigger = create_vision_procedure(program_directory=program_path,
                                                          name='TriggerCamera',
                                                          input_control={'AcqHandle':'handle'},
                                                          output_iconic=['Image'])

    program_01 = create_vision_procedure(program_directory=program_path,
                                                          name='ExtractPulleys',
                                                          input_iconic=['Image'],
                                                          input_control={'MinIntRadius':'float',
                                                                         'MaxIntRadius':'float',
                                                                         'MinExtRadius':'float',
                                                                         'MaxExtRadius':'float'
                                                                         },
                                                          output_iconic=['Pulleys', 'CorrectRefPulleys', 'IncorrectRefPulleys', 'BestPulley'],
                                                          output_control={'X':'float',
                                                                          'Y':'float',
                                                                          'CorrectRefCount':'int',
                                                                          'IncorrectRefCount':'int',
                                                                          'MinIntRadiusResult':'float',
                                                                          'MaxIntRadiusResult':'float',
                                                                          'MinExtRadiusResult':'float',
                                                                          'MaxExtRadiusResult':'float'})
    
    programs = [program_01]

    display_01 = create_vision_procedure(program_directory=program_path,
                                                          name='GetPulleysImage',
                                                          input_iconic=['Image', 'Pulleys', 'CorrectRefPulleys', 'IncorrectRefPulleys', 'BestPulley'])
    
    displays = [display_01]
    
    return open, trigger, programs, displays

def create_final_inspection_camera(program_path:str):

    open = create_vision_procedure(program_directory=program_path,
                                                       name='OpenCamera',
                                                       output_control={'AcqHandle': 'handle'})

    trigger = create_vision_procedure(program_directory=program_path,
                                                          name='TriggerCamera',
                                                          input_control={'AcqHandle':'handle'},
                                                          output_iconic=['Image'])

    program_01 = create_vision_procedure(program_directory=program_path,
                                                          name='Inspection',
                                                          input_iconic=['Image'],
                                                          input_control={'ProgramNumber':'int',
                                                                         'MinAngle':'float',
                                                                         'MaxAngle':'float',
                                                                         'MinScore':'float'
                                                                         },
                                                          output_control={'Angle':'float',
                                                                          'Score':'float',
                                                                          'OK':'int',
                                                                          'NOK':'int',
                                                                          'X':'float',
                                                                          'Y':'float',
                                                                          'Ref':'string',
                                                                          'Width':'float',
                                                                          'Height':'float'})
    
    programs = [program_01]

    display_01 = create_vision_procedure(program_directory=program_path,
                                                          name='Display',
                                                          input_iconic=['Image'],
                                                          input_control={'X':'float',
                                                                         'Y':'float',
                                                                         'Width':'float',
                                                                         'Height':'float',
                                                                         'OK':'int',
                                                                         'NOK':'int',
                                                                         'Ref':'string',
                                                                         'Score':'float'})
    
    displays = [display_01]
    
    return open, trigger, programs, displays
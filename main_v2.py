from tqdm import tqdm
import subprocess
import numpy as np
from ctypes import Structure, c_int, c_double, POINTER, CDLL
import pandas as pd

SCHEDULING_VERSION = 3
HORIZON = 289
NUM_ACTIVITIES = 0
group_to_type = {
    0: 'home',
    1: 'education',
    2: 'work',
    3: 'leisure',
    4: 'shop'
}

######################################################
##### START OF STRUCTURE #############################


class Group_mem(Structure):
    pass

Group_mem._fields_ = [
    ("g", c_int),
    ("previous", POINTER(Group_mem)),
    ("next", POINTER(Group_mem))
]

class Activity(Structure):
    pass

Activity._fields_ = [
    ("id", c_int),
    ("earliest_start", c_int),
    ("latest_start", c_int),
    ("min_duration", c_int),
    ("max_duration", c_int),
    ("x", c_int),
    ("y", c_int),
    ("group", c_int),
    ("memory", POINTER(Group_mem)),
    ("des_duration", c_int),
    ("des_start_time", c_int)
]

class Label(Structure):
    pass

Label._fields_ = [
    ("acity", c_int),
    ("time", c_int),
    ("start_time", c_int),
    ("duration", c_int),
    ("utility", c_double),
    ("mem", POINTER(Group_mem)),
    ("previous", POINTER(Label)),
    ("act", POINTER(Activity))
]

class L_list(Structure):
    pass

L_list._fields_ = [
    ("element", POINTER(Label)),
    ("previous", POINTER(L_list)),
    ("next", POINTER(L_list))
]

##### END OF STRUCTURE ###############################
######################################################
##### START OF INITIALIZATION ########################

def initialize_activities(df, num_activities): # utiliser les data et enlever le none by default
    ''' Cree un vecteur d activite en les initialisant en fonction d'un dataframe en input '''
    activities_array = (Activity * num_activities)()

    for index, row in df.iterrows(): # index + 1 to let some place to home first and last
        activities_array[index+1].id = index+1
        activities_array[index+1].x = row['x']
        activities_array[index+1].y = row['y']
        activities_array[index+1].earliest_start = row['earliest_start']
        activities_array[index+1].latest_start = row['latest_start']
        activities_array[index+1].max_duration = row['max_duration']
        activities_array[index+1].min_duration = row['min_duration']
        activities_array[index+1].group = row['group']

    return activities_array


def personalize(activities_array, num_activities, individual, group_to_type):
    ''' Pour chaque individu, personnalise le vecteur d'activite en fonction 
        de sa home et de ses preferences '''

    # dawn
    activities_array[0].id = 0
    activities_array[0].x = individual['home_x']
    activities_array[0].y = individual['home_y']
    activities_array[0].earliest_start = 0  
    activities_array[0].latest_start = 0      
    activities_array[0].max_duration = 0   
    activities_array[0].min_duration = 1
    activities_array[0].des_duration = 0 
    activities_array[0].des_start_time = 0 
    activities_array[0].group = 0

    # dusk
    activities_array[num_activities-1].id = num_activities-1
    activities_array[num_activities-1].x = individual['home_x']
    activities_array[num_activities-1].y = individual['home_y']
    activities_array[num_activities-1].earliest_start = 0
    activities_array[num_activities-1].latest_start = HORIZON
    activities_array[num_activities-1].max_duration = 0                      
    activities_array[num_activities-1].min_duration = 1 
    activities_array[num_activities-1].des_duration = 1   
    activities_array[num_activities-1].des_start_time = 287   
    activities_array[num_activities-1].group = 0

    # home
    activities_array[num_activities-2].id = num_activities-2
    activities_array[num_activities-2].x = individual['home_x']
    activities_array[num_activities-2].y = individual['home_y']
    activities_array[num_activities-2].earliest_start = 0
    activities_array[num_activities-2].latest_start = HORIZON
    activities_array[num_activities-2].max_duration = 0                      
    activities_array[num_activities-2].min_duration = 1 
    activities_array[num_activities-2].des_duration = 0 
    activities_array[num_activities-2].des_start_time = 0   
    activities_array[num_activities-2].group = 0

    for index, activity in enumerate(activities_array):
        group = activity.group
        if group == 0: 
            continue
        activity_type = group_to_type[group]
        activity.des_duration = individual[f'{activity_type}_duration']
        activity.des_start_time = individual[f'{activity_type}_starting']          

    return activities_array


def initialize_param(): 
    ''' Initialise les parametres de la utility function'''
    # REVOIR LES SIGNES + 
    # sont ils par minutes ?? pcq je travaille en time interval de 1 pour 5m 
    parameters = np.zeros(17)

    # flexibility parameters
    # parameters[0] = 0               # O_start_early_F
    # parameters[1] = 0.61           # O_start_early_MF
    # parameters[2] = 2.4            # O_start_early_NF
    # parameters[3] = 0               # O_start_late_F
    # parameters[4] = 2.4            # O_start_late_MF
    # parameters[5] = 9.6            # O_start_late_NF
    # parameters[6] = 0.61           # O_dur_short_F
    # parameters[7] = 2.4            # O_dur_short_MF
    # parameters[8] = 9.6            # O_dur_short_NF
    # parameters[9] = 0.61           # O_dur_long_F
    # parameters[10] = 2.4           # O_dur_long_MF
    # parameters[11] = 9.6           # O_dur_long_NF

    # others 
    # parameters[12] = 1            # beta_cost    
    # parameters[13] = 0           # beta_travel_cost
    # parameters[14] = 0            # theta_travel
    # parameters[15] = 0            # c_a
    # parameters[16] = 0           # c_t

    parameters[0] = 0               # O_start_early_F
    parameters[1] = 0           # O_start_early_MF
    parameters[2] = 0             # O_start_early_NF
    parameters[3] = 0               # O_start_late_F
    parameters[4] = 0             # O_start_late_MF
    parameters[5] = 0             # O_start_late_NF
    parameters[6] = 0            # O_dur_short_F
    parameters[7] = 0             # O_dur_short_MF
    parameters[8] = 0             # O_dur_short_NF
    parameters[9] = 0            # O_dur_long_F
    parameters[10] = 0            # O_dur_long_MF
    parameters[11] = 0            # O_dur_long_NF

    # others 
    parameters[12] = 0            # beta_cost    
    parameters[13] = 0           # beta_travel_cost
    parameters[14] = 0            # theta_travel
    parameters[15] = 0            # c_a
    parameters[16] = 0           # c_t

    return parameters

##### END OF INITIALIZATION ##########################
######################################################
##### START OF FUNCTIONS #############################

def compile_code():
    ''' Compile le code C '''
    compile_command = ["gcc", "-m64", "-O3", "-shared", "-o", 
                   f"scheduling/scheduling_v{SCHEDULING_VERSION}.dll", 
                   f"scheduling/scheduling_v{SCHEDULING_VERSION}.c", "-lm"]
    subprocess.run(compile_command)

def recursive_print(label_pointer):
    """
    Recursively prints information about the given Label and all of its predecessors 
    Parameters: label_pointer: ctypes.POINTER(Label)
    """
    if label_pointer:
        label = label_pointer.contents
        
        if label.previous:
            recursive_print(label.previous)
        
        activity = label.act.contents # aussi imprimer la des_start/dur pour test ?
        print(f"(act = {label.acity}, group = {group_to_type[activity.group]}, start = {label.start_time}, duration = {label.duration}) ", end="")

def extract_schedule_data(label_pointer, activity_df):
    """
    Tire d'un pointeur vers un label le deroule du schedule 
    en remontant a sa racine et stockant les donnees importantes
    """
    path_to_root = []
    while label_pointer:
        path_to_root.append(label_pointer)
        label_pointer = label_pointer.contents.previous

    schedule_data = []
    for label_pointer in reversed(path_to_root):
        label = label_pointer.contents

        acity = label.acity 
        if (acity > 0) and (acity < NUM_ACTIVITIES-2):
            activity_row_froim_csv = activity_df.iloc[acity-1]
            facility_id = activity_row_froim_csv['facility']
        else:
            facility_id = 0

        data = {
            "acity": label.acity,
            "facility": facility_id,
            "group": group_to_type[label.act.contents.group],
            # "group_id": label.act.contents.group,
            "start": label.start_time,
            "duration": label.duration,
            "time" :label.time,
            "cum_utility" : label.utility
        }
        schedule_data.append(data)

    return schedule_data

##### END OF FUNCTIONS ###############################
######################################################
##### START OF EXECUTION #############################

def main():

    compile_code()
    lib = CDLL(f"./scheduling/scheduling_v{SCHEDULING_VERSION}.dll")            # python is 64 bits and compiler too (check with gcc --version)
    lib.get_final_schedule.restype = POINTER(Label)
    lib.get_total_time.restype = c_double
    lib.get_count.restype = c_int

    activity_csv = pd.read_csv("./data_preprocessed/activity.csv")
    population_csv = pd.read_csv("./data_preprocessed/population.csv")

    global NUM_ACTIVITIES 
    NUM_ACTIVITIES = len(activity_csv) + 3                                      # we will add dusk, home and dawn
    
    activities_array = initialize_activities(activity_csv, NUM_ACTIVITIES) 
    thetas = initialize_param()                                                 # REVOIR LES SIGNES ET AUTRE

    lib.set_num_activities(NUM_ACTIVITIES)
    lib.set_utility_parameters(thetas.ctypes.data_as(POINTER(c_double)))

    DSSR_iterations = []
    execution_times = []
    final_utilities = []
    schedules = []
    ids = []
    for index, individual in tqdm(population_csv.iterrows(), total=population_csv.shape[0]):
        
        if (index < 2 or index > 2):                                            # controle iterations to test
            continue

        perso_activities_array = personalize(activities_array, NUM_ACTIVITIES, individual, group_to_type)
        lib.set_activities_pointer(perso_activities_array)
        # for activity in perso_activities_array:
        #     print(f"ID: {activity.id}, Group: {activity.group}, desired start: {activity.des_start_time}, desired duration: {activity.des_duration}")


        lib.main()

        iter = lib.get_count()
        time = lib.get_total_time()
        schedule_pointer = lib.get_final_schedule()   

        DSSR_iterations.append(iter)
        execution_times.append(time)
        schedule_data = extract_schedule_data(schedule_pointer, activity_csv)
        schedules.append(schedule_data) 
        ids.append(individual['id'])
        if schedule_pointer and schedule_pointer.contents:
            final_utilities.append(schedule_pointer.contents.utility)
        else:
            final_utilities.append(0)


    results = pd.DataFrame({
        'id': ids,
        # 'age': population_csv['age'],
        'execution_time': execution_times,
        'DSSR_iterations': DSSR_iterations,
        'utility': final_utilities,
        'daily_schedule': schedules  
    })

    results.to_csv('./data_output/schedules.csv', index=False)
    results.to_json('./data_output/schedules.json', orient='records', lines=False, indent = 4) 


if __name__ == "__main__":
    main()

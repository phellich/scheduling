from tqdm import tqdm
import subprocess
import ctypes # je pourrai clean un peu ca
import numpy as np
from ctypes import Structure, c_int, c_double, POINTER
import pandas as pd

SCHEDULING_VERSION = 2
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

from ctypes import Structure, c_int, c_double, POINTER

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
    ("des_duration", c_int)
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
    activities_array[0].latest_start = 0                                      # ? 
    activities_array[0].max_duration = 0                                      # ? 
    activities_array[0].min_duration = 0
    activities_array[0].des_duration = 0    # supprimer ou NULL ?                         # ? 
    activities_array[0].des_start_time = 0    # supprimer ou NULL ?                         # ? 
    activities_array[0].group = 0

    # dusk
    activities_array[num_activities-1].id = num_activities-1
    activities_array[num_activities-1].x = individual['home_x']
    activities_array[num_activities-1].y = individual['home_y']
    activities_array[num_activities-1].earliest_start = 0
    activities_array[num_activities-1].latest_start = HORIZON
    activities_array[num_activities-1].max_duration = 0                       # ?
    activities_array[num_activities-1].min_duration = 0 
    activities_array[num_activities-1].des_duration = 0   # supprimer ou NULL ?          # ? 
    activities_array[num_activities-1].des_start_time = 0   # supprimer ou NULL ?                         # ? 
    activities_array[num_activities-1].group = 0

    for index, activity in enumerate(activities_array):
        group = activity.group
        if group == 0: 
            continue
        activity_type = group_to_type[group]
        activity.des_duration = individual[f'{activity_type}_duration']
        activity.des_start_time = individual[f'{activity_type}_starting']          

    return activities_array


def initialize_param(): 
    ''' Initialise tous les parametres de la utility function'''
    # REVOIR LES SIGNES + 
    # sont ils par minutes ?? pcq je travaille en time interval de 1 pour 5m 
    thetas = np.zeros(12)

    thetas[0] = 0
    thetas[1] = -0.61
    thetas[2] = -2.4

    thetas[3] = 0
    thetas[4] = -2.4
    thetas[5] = -9.6

    thetas[6] = -0.61
    thetas[7] = -2.4
    thetas[8] = -9.6

    thetas[9] = -0.61
    thetas[10] = -2.4
    thetas[11] = -9.6

    return thetas

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
        
        activity = label.act.contents
        print(f"(a{label.acity}, g{activity.group}, t{label.time}) ", end="")

def extract_schedule_data(label_pointer):
    """
    Tire d'un pointeur vers un label le deroule du schedule 
    en remontant a sa racine et stockant les donnees importantes
    """
    # Traverse to the root first
    path_to_root = []
    while label_pointer:
        path_to_root.append(label_pointer)
        label_pointer = label_pointer.contents.previous

    # Walk backward from the root to build the schedule
    schedule_data = []
    for label_pointer in reversed(path_to_root):
        label = label_pointer.contents
        data = {
            "acity": label.acity,
            "group": label.act.contents.group,
            "time": label.time,
            "duration": label.duration,
        }
        schedule_data.append(data)

    return schedule_data


##### END OF FUNCTIONS ###############################
######################################################
##### START OF EXECUTION #############################

def main_iterative():

    compile_code()
    lib = ctypes.CDLL(f"./scheduling/scheduling_v{SCHEDULING_VERSION}.dll") # python is 64 bits and compiler too (check with gcc --version)
    lib.get_final_schedule.restype = ctypes.POINTER(Label)
    lib.get_total_time.restype = ctypes.c_double
    lib.get_count.restype = ctypes.c_int

    activity_csv = pd.read_csv("./data_preprocessed/activity.csv")
    population_csv = pd.read_csv("./data_preprocessed/population.csv")

    global NUM_ACTIVITIES 
    NUM_ACTIVITIES = len(activity_csv) + 2 # we will add dusk and dawn
    
    activities_array = initialize_activities(activity_csv, NUM_ACTIVITIES) 
    # pyduration_Ut = initialize_duration_utility(NUM_ACTIVITIES)
    # pytime_Ut = initialize_start_utility(NUM_ACTIVITIES)
    thetas = initialize_param() # REVOIR LES SIGNES ET AUTRE

    lib.set_num_activities(NUM_ACTIVITIES)
    # lib.set_start_utility(pytime_Ut)
    # lib.set_duration_utility(pyduration_Ut)
    lib.set_utility_parameters(thetas.ctypes.data_as(ctypes.POINTER(ctypes.c_double)))

    DSSR_iterations = []
    execution_times = []
    schedules = []
    for index, individual in tqdm(population_csv.iterrows(), total=population_csv.shape[0]):
        
        perso_activities_array = personalize(activities_array, NUM_ACTIVITIES, individual, group_to_type)

        lib.set_activities_pointer(perso_activities_array)
        lib.main()

        iter = lib.get_count()
        time = lib.get_total_time()
        schedule_pointer = lib.get_final_schedule()   

        DSSR_iterations.append(iter)
        execution_times.append(time)
        schedule_data = extract_schedule_data(schedule_pointer)
        schedules.append(schedule_data) 

    results = pd.DataFrame({
        'id': population_csv['id'],
        'age': population_csv['age'],
        'execution_time': execution_times,
        'DSSR_iterations': DSSR_iterations,
        'daily_schedule': schedules  
    })

    results.to_csv('./data_output/schedules.csv', index=False)
    results.to_json('./data_output/schedules.json', orient='records', lines=True) 

if __name__ == "__main__":
    main_iterative()

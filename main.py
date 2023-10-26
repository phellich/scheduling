from tqdm import tqdm
import subprocess
import ctypes # je pourrai clean un peu ca
import numpy as np
from ctypes import Structure, c_int, c_double, POINTER
import pandas as pd

SCHEDULING_VERSION = 2
HORIZON = 289
NUM_ACTIVITIES = 0

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
    ("t1", c_int),
    ("t2", c_int),
    ("t3", c_int),
    ("x", c_int),
    ("y", c_int),
    ("group", c_int),
    ("memory", POINTER(Group_mem)),
    ("min_duration", c_int),
    ("des_duration", c_double)
]

class Label(Structure):
    pass

Label._fields_ = [
    ("acity", c_int),
    ("time", c_int),
    ("duration", c_int),
    ("cost", c_double),
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

def initialize_activities(num_activities): # utiliser les data et enlever le none by default
    # Create an array of Activity
    x_values = [84, 29, 1, 44, 71, 45, 70, 48, 3, 70, 1, 8, 79, 38, 14, 7, 75, 19, 75, 86, 46, 5, 53, 95, 22, 22, 4, 73, 20, 69, 46, 77, 29, 73, 31, 40, 91, 40, 23, 50, 90, 68, 81, 30, 68, 8, 86, 78, 85, 34, 88, 27, 57, 99, 2, 32, 19, 36, 10, 66, 41, 83, 90, 38, 99, 29, 85, 56, 15, 47, 30, 76, 17, 9, 6, 95, 80, 91, 12, 79, 51, 3, 23, 17, 43, 28, 49, 69, 51, 73, 64, 90, 29, 22, 91, 22, 66, 35, 60, 81, 92, 16, 26, 19, 6, 48, 15, 27, 28, 78, 95, 84, 29, 9, 87, 50, 12, 74, 44, 76, 49, 61, 59, 69, 21, 55, 41, 67, 55, 63, 9, 26, 4, 98, 91, 18, 79, 51, 6, 35, 81, 57, 52, 66, 51, 61, 82, 74, 74, 37]
    y_values = [84, 37, 84, 71, 59, 90, 92, 40, 53, 2, 88, 13, 32, 68, 9, 30, 5, 68, 20, 21, 5, 25, 69, 89, 20, 48, 41, 92, 5, 93, 74, 40, 29, 3, 27, 12, 72, 98, 64, 53, 66, 14, 17, 28, 34, 82, 46, 95, 54, 78, 40, 37, 20, 42, 83, 70, 67, 22, 64, 71, 3, 85, 53, 70, 15, 53, 99, 87, 50, 35, 6, 39, 45, 73, 8, 48, 18, 1, 6, 11, 99, 45, 12, 97, 42, 66, 78, 86, 4, 99, 83, 81, 74, 99, 71, 37, 66, 61, 67, 7, 44, 48, 69, 74, 68, 33, 35, 89, 17, 2, 66, 12, 78, 43, 61, 14, 19, 73, 4, 10, 94, 84, 99, 62, 95, 61, 80, 83, 8, 25, 29, 48, 31, 85, 6, 12, 36, 62, 53, 14, 87, 11, 59, 88, 52, 40, 14, 64, 20, 40]  
    # print(f"\n x is length : {len(x_values)} \n ")

    activities_array = (Activity * num_activities)()

    for i in range(num_activities):
        activities_array[i].id = i
        activities_array[i].x = x_values[i]
        activities_array[i].y = y_values[i]
        activities_array[i].t1 = 5
        activities_array[i].t2 = HORIZON - 1
        activities_array[i].t3 = HORIZON - 1
        activities_array[i].min_duration = 24
        activities_array[i].des_duration = 30.0
        activities_array[i].group = 0

    # Special cases
    activities_array[0].min_duration = 24
    activities_array[0].t1 = 0
    activities_array[num_activities - 1].min_duration = 0
    activities_array[num_activities - 1].t1 = 0
    activities_array[num_activities - 1].t2 = HORIZON

    # Initialization for group 1
    for a in range(1, 5):
        activities_array[a].t1 = 24
        activities_array[a].t2 = 200
        activities_array[a].group = 1

    # Initialization for group 2
    for a in range(5, 11):
        activities_array[a].t1 = 50
        activities_array[a].t2 = 230
        activities_array[a].group = 2

    # Initialization for group 3
    for a in range(11, 17):
        activities_array[a].t1 = 0
        activities_array[a].t2 = 255
        activities_array[a].group = 3

    # Initialization for group 4
    for a in range(17, 24):
        activities_array[a].t1 = 10
        activities_array[a].t2 = 266
        activities_array[a].group = 4

    # Initialization for group 5
    num_activities = len(activities_array)
    for a in range(24, num_activities-1):
        activities_array[a].t1 = 40
        activities_array[a].t2 = HORIZON  # Make sure horizon is defined somewhere in your Python code
        activities_array[a].group = 5

    # Special Initialization
    activities_array[num_activities - 1].group = 0

    return activities_array


def initialize_activities_2(df, num_activities): # utiliser les data et enlever le none by default

    activities_array = (Activity * num_activities)()

    for index, row in df.iterrows(): # index + 1 to let some place to home first and last
        activities_array[index+1].id = index+1
        activities_array[index+1].x = row['x']
        activities_array[index+1].y = row['y']
        activities_array[index+1].t1 = row['t1']
        activities_array[index+1].t2 = row['t2']
        activities_array[index+1].t3 = row['t3']
        activities_array[index+1].min_duration = row['min_duration']
        activities_array[index+1].des_duration = row['des_duration']
        activities_array[index+1].group = row['group']

    return activities_array


def personalize(activities_array, num_activities, individual):
        # dusk
        activities_array[0].id = 0
        activities_array[0].x = individual['home_x']
        activities_array[0].y = individual['home_y']
        activities_array[0].t1 = 0  
        activities_array[0].t2 = 0                                      # ? 
        activities_array[0].t3 = 0                                      # ? 
        activities_array[0].min_duration = 24
        activities_array[0].des_duration = 30                           # ? 
        activities_array[0].group = 0

        # dawn
        activities_array[num_activities-1].id = num_activities-1
        activities_array[num_activities-1].x = individual['home_x']
        activities_array[num_activities-1].y = individual['home_y']
        activities_array[num_activities-1].t1 = 0
        activities_array[num_activities-1].t2 = HORIZON
        activities_array[num_activities-1].t3 = 0                       # ?
        activities_array[num_activities-1].min_duration = 0
        activities_array[num_activities-1].des_duration = 30            # ? 
        activities_array[num_activities-1].group = 0

        return activities_array


def initialize_start_utility(num_activities): 
    time_Ut = [[0.0 for j in range(HORIZON)] for i in range(num_activities)]

    time_Ut[3][5] = 70

    # Loop to fill time_Ut
    for a in range(num_activities):
        for i in range(5, HORIZON):
            time_Ut[a][i] = 1000 / i

    time_Ut_c = (ctypes.POINTER(ctypes.c_double) * num_activities)()
    for i, row in enumerate(time_Ut):
        time_Ut_c[i] = (ctypes.c_double * HORIZON)(*row)

    return time_Ut_c


def initialize_duration_utility(num_activities): 
    duration_Ut = [[0.0 for j in range(HORIZON)] for i in range(num_activities)]

    # Arbitrary assignments
    duration_Ut[3][3] = 10
    duration_Ut[3][4] = 11

    # Convert the Python lists to C-compatible arrays
    duration_Ut_c = (ctypes.POINTER(ctypes.c_double) * num_activities)()
    for i, row in enumerate(duration_Ut):
        duration_Ut_c[i] = (ctypes.c_double * HORIZON)(*row)

    return duration_Ut_c


def initialize_thetas(): # REVOIR LES SIGNES
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

def main_test():

    global NUM_ACTIVITIES 
    NUM_ACTIVITIES = 60

    compile_code()
    lib = ctypes.CDLL(f"./scheduling/scheduling_v{SCHEDULING_VERSION}.dll") # python is 64 bits and compiler too (check with gcc --version)
    lib.get_final_schedule.restype = ctypes.POINTER(Label)
    lib.get_total_time.restype = ctypes.c_double

    activities_array = initialize_activities(NUM_ACTIVITIES)
    pyduration_Ut = initialize_duration_utility(NUM_ACTIVITIES)
    pytime_Ut = initialize_start_utility(NUM_ACTIVITIES)

    lib.set_start_utility(pytime_Ut)
    lib.set_duration_utility(pyduration_Ut)
    lib.set_activities_pointer(activities_array)

    lib.main()

    DSSR_iter = lib.get_count()
    C_time = lib.get_total_time()
    final_schedule = lib.get_final_schedule()

    print(f"The execution took {C_time}s for {DSSR_iter} DSSR iterations")
    # print(final_schedule)
    print("Sequence of activities is :")
    recursive_print(final_schedule)


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
    
    activities_array = initialize_activities_2(activity_csv, NUM_ACTIVITIES) 
    pyduration_Ut = initialize_duration_utility(NUM_ACTIVITIES)
    pytime_Ut = initialize_start_utility(NUM_ACTIVITIES)
    thetas = initialize_thetas() # REVOIR LES SIGNES

    lib.set_num_activities(NUM_ACTIVITIES)
    lib.set_start_utility(pytime_Ut)
    lib.set_duration_utility(pyduration_Ut)
    lib.set_theta_parameters(thetas.ctypes.data_as(ctypes.POINTER(ctypes.c_double)))

    DSSR_iterations = []
    execution_times = []
    schedules = []
    for index, individual in tqdm(population_csv.iterrows(), total=population_csv.shape[0]):
        
        perso_activities_array = personalize(activities_array, NUM_ACTIVITIES, individual)

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
    # main_test()
    main_iterative()

    # coord en m !! see swiss national grid

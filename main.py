from tqdm import tqdm
import subprocess
import numpy as np
from ctypes import Structure, c_int, c_double, POINTER, CDLL
import pandas as pd
from collections import namedtuple

SCHEDULING_VERSION = 5
HORIZON = 289
NUM_ACTIVITIES = 0
group_to_type = {
    0: 'home',
    1: 'education',
    2: 'work',
    3: 'leisure',
    4: 'shop'
}
groups = ['home', 'education', 'work', 'leisure', 'shop']

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
    activities_array[0].max_duration = HORIZON-2   
    activities_array[0].min_duration = 1
    activities_array[0].des_duration = 0 
    activities_array[0].des_start_time = 0 
    activities_array[0].group = 0

    # dusk
    activities_array[num_activities-1].id = num_activities-1
    activities_array[num_activities-1].x = individual['home_x']
    activities_array[num_activities-1].y = individual['home_y']
    activities_array[num_activities-1].earliest_start = 0
    activities_array[num_activities-1].latest_start = HORIZON-2
    activities_array[num_activities-1].max_duration = HORIZON-2                       
    activities_array[num_activities-1].min_duration = 1 
    activities_array[num_activities-1].des_duration = 0   
    activities_array[num_activities-1].des_start_time = 0   
    activities_array[num_activities-1].group = 0

    # home
    activities_array[num_activities-2].id = num_activities-2
    activities_array[num_activities-2].x = individual['home_x']
    activities_array[num_activities-2].y = individual['home_y']
    activities_array[num_activities-2].earliest_start = 0
    activities_array[num_activities-2].latest_start = HORIZON
    activities_array[num_activities-2].max_duration = HORIZON-2                       
    activities_array[num_activities-2].min_duration = 4 
    activities_array[num_activities-2].des_duration = 0 
    activities_array[num_activities-2].des_start_time = 0   
    activities_array[num_activities-2].group = 0

    # work
    activities_array[num_activities-3].id = num_activities-3
    activities_array[num_activities-3].x = individual['work_x']
    activities_array[num_activities-3].y = individual['work_y']
    activities_array[num_activities-3].earliest_start = 72 # 6h
    activities_array[num_activities-3].latest_start = 276 # 23h
    activities_array[num_activities-3].max_duration = 192 # (de 7h a 23h)                       
    activities_array[num_activities-3].min_duration = 6 # 30m
    activities_array[num_activities-3].group = 2

    for activity in activities_array:
        group = activity.group
        if (group == 0): #################### will change again TO CHANGE
            continue
        activity_type = group_to_type[group]
        activity.des_duration = individual[f'{activity_type}_duration']
        activity.des_start_time = individual[f'{activity_type}_starting']          

    return activities_array


def initialize_param(): 
    ''' Initialise les parametres de la utility function'''

    UtilityParams = namedtuple('UtilityParams', 'asc early late long short')
    # params = UtilityParams( # TRUE PARAMETERS
    #     # order = [home, education, work, leisure, shop]
    #     asc=[0, 18.7, 13.1, 8.74, 10.5],
    #     early=[0, 1.35, 0.619, 0.0996, 1.01],
    #     late=[0, 1.63, 0.338, 0.239, 0.858],
    #     long=[0, 1.14, 1.22, 0.08, 0.683],
    #     short=[0, 1.75, 0.932, 0.101, 1.81]
    # )
    params = UtilityParams(
        # order = [home, education, work, leisure, shop]
        asc=[0, 9.7, 20.1, 8.74, 10.5],
        early=[0, 1.35, 0.619, 0.0996, 1.01],
        late=[0, 1.63, 0.338, 0.239, 0.858],
        long=[0, 1.14, 1.22, 0.08, 0.683],
        short=[0, 1.75, 0.932, 0.101, 1.81]
    )

    return params

def participation_vector(individual, groups): 
    ''' if a people hasn't take part to an activity, its utility to do this activity is reduced '''
    penalty_part = []
    for i, group in enumerate(groups):
        if (i == 0): # home 
            penalty_part.append(1) # + terme random centre sur 1 et tres proche en vrai 
        elif (individual[f"{group}_participation"] == 1): 
            penalty_part.append(1)
        else: 
            penalty_part.append(0.5)

    return penalty_part

##### END OF INITIALIZATION ##########################
######################################################
##### START OF FUNCTIONS #############################

def compile_code():
    ''' Compile le code C '''
    compile_command = ["gcc", "-m64", "-O3", "-shared", "-o", 
                   f"Optimizer/scheduling_v{SCHEDULING_VERSION}.dll", 
                   f"Optimizer/scheduling_v{SCHEDULING_VERSION}.c", "-lm"]
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
        print(f"(act = {label.acity}, group = {group_to_type[activity.group]}, start = {label.start_time}, desired start = {activity.des_start_time}, duration = {label.duration}, desired duration = {activity.des_duration}, cumulative utility = {label.utility})\n", end="")

def extract_schedule_data(label_pointer, activity_df, individual):
    """
    Extrait les données de planning à partir d'un pointeur de label, 
    en remontant à la racine et en stockant les données importantes.
    """
    path_to_root = []
    while label_pointer:
        path_to_root.append(label_pointer)
        label_pointer = label_pointer.contents.previous

    # Utiliser un dictionnaire pour conserver la durée maximale pour chaque identifiant (activity, start)
    schedule_data_dict = {}
    for label_pointer in reversed(path_to_root):
        label = label_pointer.contents

        acity = label.acity
        if (acity > 0) and (acity < NUM_ACTIVITIES-3):
            activity_row_from_csv = activity_df.iloc[acity-1]
            facility_id = activity_row_from_csv['facility']
        elif (acity == NUM_ACTIVITIES-3):
            facility_id = individual['work_id']
        else:
            facility_id = 0

        data = {
            "acity": label.acity,
            "facility": facility_id,
            "group": group_to_type[label.act.contents.group],
            "start": label.start_time,
            "duration": label.duration,
            "time": label.time,
            "cum_utility": label.utility
        }

        # Clé unique pour identifier chaque activité avec son heure de début
        unique_key = (data["acity"], data["start"])

        # Vérifier si la durée est plus grande que celle déjà stockée pour cette clé
        if unique_key not in schedule_data_dict or schedule_data_dict[unique_key]["duration"] < data["duration"]:
            schedule_data_dict[unique_key] = data

    # Convertir le dictionnaire en liste pour les données de sortie
    schedule_data = list(schedule_data_dict.values())
    
    return schedule_data

##### END OF FUNCTIONS ###############################
######################################################
##### START OF EXECUTION #############################

def main():

    compile_code()
    lib = CDLL(f"Optimizer/scheduling_v{SCHEDULING_VERSION}.dll")            # python is 64 bits and compiler too (check with gcc --version)
    lib.get_final_schedule.restype = POINTER(Label)
    lib.get_total_time.restype = c_double
    lib.get_count.restype = c_int

    activity_csv = pd.read_csv("Data/PreProcessed/activity.csv")
    population_csv = pd.read_csv("Data/PreProcessed/population.csv")

    global NUM_ACTIVITIES 
    NUM_ACTIVITIES = len(activity_csv) + 4 
    SPEED = 10*16.667 # 1km/h = 16.667 m/min
    TRAVEL_TIME_PENALTY = 0.1                                    # we will add dusk, home, dawn and work
    
    activities_array = initialize_activities(activity_csv, NUM_ACTIVITIES) 
    params = initialize_param()                                                 

    
    # Convert Python lists to ctypes arrays
    asc_array = (c_double * len(params.asc))(*params.asc)
    early_array = (c_double * len(params.early))(*params.early)
    late_array = (c_double * len(params.late))(*params.late)
    long_array = (c_double * len(params.long))(*params.long)
    short_array = (c_double * len(params.short))(*params.short)

    lib.set_utility_parameters(
        asc_array,  
        early_array,
        late_array,
        long_array,
        short_array
    )
        
    DSSR_iterations = []
    execution_times = []
    final_utilities = []
    schedules = []
    ids = []
    for index, individual in tqdm(population_csv.iterrows(), total=population_csv.shape[0]):
        # print(f"{index} \n")
        # if (index < 2 or index > 2): 
        #     continue

        participation = participation_vector(individual, groups)
        pyparticipation = (c_double * len(participation))(*participation)
        lib.set_particpation_array(pyparticipation)

        perso_activities_array = personalize(activities_array, NUM_ACTIVITIES, individual, group_to_type)
        lib.set_activities_variables(perso_activities_array, NUM_ACTIVITIES, c_double(SPEED), c_double(TRAVEL_TIME_PENALTY))
        # for activity in perso_activities_array:
        #     print(f"ID: {activity.id}, Group: {activity.group}, desired start: {activity.des_start_time}, desired duration: {activity.des_duration}")

        lib.main()

        iter = lib.get_count()
        time = lib.get_total_time()
        schedule_pointer = lib.get_final_schedule()   
        schedule_data = extract_schedule_data(schedule_pointer, activity_csv, individual)

        DSSR_iterations.append(iter)
        execution_times.append(time)
        schedules.append(schedule_data) 
        ids.append(individual['id'])
        if schedule_pointer and schedule_pointer.contents:
            final_utilities.append(schedule_pointer.contents.utility)
            # print(f"\n UTILITY = {schedule_pointer.contents.utility}")
        else:
            final_utilities.append(0)

        # recursive_print(schedule_pointer)
        lib.free_bucket()
        # lib.free_activities()

    results = pd.DataFrame({
        'id': ids,
        'execution_time': execution_times,
        'DSSR_iterations': DSSR_iterations,
        'utility': final_utilities,
        'daily_schedule': schedules  
    })

    results.to_json('Data/Generated/schedules.json', orient='records', lines=False, indent = 4) 


if __name__ == "__main__":
    main()

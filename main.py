from tqdm import tqdm
import subprocess
import numpy as np
from ctypes import Structure, c_int, c_double, POINTER, CDLL
import pandas as pd
from collections import namedtuple
import time
import Post_processing

LOCAL = 'Lausanne'
# LOCAL = 'Avenches'
SCHEDULING_VERSION = 6
TIME_INTERVAL = 5
HORIZON = round(24*60/TIME_INTERVAL) + 1
SPEED = 19*16.667                                                       # 1km/h = 16.667 m/min
TRAVEL_TIME_PENALTY = 0.1                                              # we will add dusk, home, dawn and work
H8 = round(8*60/TIME_INTERVAL) + 1                
H12 = round(12*60/TIME_INTERVAL) + 1  
H13 = round(13*60/TIME_INTERVAL) + 1  
H17 = round(17*60/TIME_INTERVAL) + 1  
H20 = round(20*60/TIME_INTERVAL) + 1  
FLEXIBLE = round(60/TIME_INTERVAL)
MIDDLE_FLEXIBLE = round(30/TIME_INTERVAL)
NOT_FLEXIBLE = round(10/TIME_INTERVAL)
group_to_type = {
    0: 'home',
    1: 'education',
    2: 'work',
    3: 'leisure',
    4: 'shop'
}
groups = ['home', 'education', 'work', 'leisure', 'shop']
# https://www.swisstopo.admin.ch/en/maps-data-online/calculation-services/navref.html # Check the facility location

############################################################################################################
##### START OF STRUCTURE ###################################################################################
############################################################################################################

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
    ("deviation_start", c_int),
    ("deviation_dur", c_int),
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

##### END OF STRUCTURE #####################################################################################
############################################################################################################
##### START OF INITIALIZATION ##############################################################################

def initialize_activities(df, num_activities): # utiliser les data et enlever le none by default
    ''' Cree un vecteur d activite en les initialisant en fonction d'un dataframe en input '''
    activities_array = (Activity * num_activities)()

    for index, row in df.iterrows(): # index + 1 to let some place to home dawn
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
    activities_array[num_activities-2].min_duration = 1 
    activities_array[num_activities-2].des_duration = 0 
    activities_array[num_activities-2].des_start_time = 0   
    activities_array[num_activities-2].group = 0

    # work
    activities_array[num_activities-3].id = num_activities-3
    activities_array[num_activities-3].x = individual['work_x']
    activities_array[num_activities-3].y = individual['work_y']
    activities_array[num_activities-3].earliest_start = round(5*60/TIME_INTERVAL) # 5h
    activities_array[num_activities-3].latest_start = round(23*60/TIME_INTERVAL) # 23h
    activities_array[num_activities-3].max_duration = round(12*60/TIME_INTERVAL) # 12h
    activities_array[num_activities-3].min_duration = round(10/TIME_INTERVAL) # 10m
    activities_array[num_activities-3].group = 2

    for activity in activities_array:
        group = activity.group
        if (group == 0): 
            continue
        activity_type = group_to_type[group]
        activity.des_duration = individual[f'{activity_type}_dur']
        activity.des_start_time = individual[f'{activity_type}_start']          

    return activities_array


def initialize_utility(): 
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
        asc=[0, 18.7, 13.1, 8.74, 10.5],
        early=[0, 1.35, 0.619, 0.0996, 1.01],
        late=[0, 1.63, 0.338, 0.239, 0.858],
        long=[0, 1.14, 1.22, 0.08, 0.683],
        short=[0, 1.75, 0.932, 0.101, 1.81]
    )

    return params

##### END OF INITIALIZATION ################################################################################
############################################################################################################
##### START OF FUNCTIONS ###################################################################################

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

def extract_schedule_data(label_pointer, activity_df, individual, num_activities):
    """
    Extrait les données de planning à partir d'un pointeur de label, 
    en remontant à la racine et en stockant les données importantes.
    """
    path_to_root = []
    while label_pointer:
        path_to_root.append(label_pointer)
        label_pointer = label_pointer.contents.previous

    schedule_data_dict = {}
    for label_pointer in reversed(path_to_root):
        label = label_pointer.contents

        acity = label.acity
        if (acity > 0) and (acity < num_activities-3):              # general activity
            activity_row_from_csv = activity_df.iloc[acity-1]
            facility_id = activity_row_from_csv['facility']
            x = activity_row_from_csv['x']
            y = activity_row_from_csv['y']      
        elif (acity == num_activities-3):                           # work
            facility_id = individual['work_id']
            x = individual['work_x']
            y = individual['work_y']
        else:                                                       # home
            facility_id = individual['homeid']
            x = individual['home_x']
            y = individual['home_y']

        data = {
            "acity": label.acity,
            "facility": facility_id,
            "group": group_to_type[label.act.contents.group],
            "start": label.start_time,
            "duration": label.duration,
            "time": label.time,
            "cum_utility": label.utility,
            "deviation_start": label.deviation_start,
            "deviation_dur": label.deviation_dur,
            "x": x,
            "y": y
        }

        unique_key = (data["acity"], data["start"])
        # Vérifier si la durée est plus grande que celle déjà stockée pour cette clé
        if unique_key not in schedule_data_dict or schedule_data_dict[unique_key]["duration"] < data["duration"]:
            schedule_data_dict[unique_key] = data

    schedule_data = list(schedule_data_dict.values())
    return schedule_data

def filter_closest(all_activities, individual, num_act_to_select):
    home = np.array((individual['home_x'], individual['home_y']))
    work = np.array((individual['work_x'], individual['work_y']))

    # Calculate distances using numpy for better performance
    activities_locations = all_activities[['x', 'y']].to_numpy()
    distances_home = np.linalg.norm(activities_locations - home, axis=1)
    distances_work = np.linalg.norm(activities_locations - work, axis=1)
    min_distances = np.minimum(distances_home, distances_work)

    # Add distances to DataFrame
    closest_activities = all_activities.copy()
    closest_activities['distance'] = min_distances

    # Calculate fraction of each facility type in the original DataFrame
    type_fractions = all_activities['type'].value_counts(normalize=True)

    # Select closest facilities for each type based on the fraction
    selected_activities = pd.DataFrame()
    for facility_type, fraction in type_fractions.items():
        type_activities = closest_activities[closest_activities['type'] == facility_type]
        n_closest = int(num_act_to_select * fraction)
        selected_activities = pd.concat([selected_activities, type_activities.sort_values('distance').head(n_closest)])
        
    return selected_activities.reset_index(drop=True)

##### END OF FUNCTIONS #####################################################################################
############################################################################################################
##### START OF EXECUTION ###################################################################################


def compile_and_initialize(): 
    
    compile_code()
    lib = CDLL(f"Optimizer/scheduling_v{SCHEDULING_VERSION}.dll")            # python is 64 bits and compiler too (check with gcc --version)

    activity_csv = pd.read_csv(f"Data/2_PreProcessed/activities_{LOCAL}.csv")
    population_csv = pd.read_csv(f"Data/2_PreProcessed/population_{LOCAL}.csv")
     
    lib.get_final_schedule.restype = POINTER(Label)
    lib.get_total_time.restype = c_double
    lib.get_count.restype = c_int
                                                    
    util_params = initialize_utility() 
    asc_array = (c_double * len(util_params.asc))(*util_params.asc)
    early_array = (c_double * len(util_params.early))(*util_params.early)
    late_array = (c_double * len(util_params.late))(*util_params.late)
    long_array = (c_double * len(util_params.long))(*util_params.long)
    short_array = (c_double * len(util_params.short))(*util_params.short) 

    lib.set_general_parameters(c_int(HORIZON), c_double(SPEED), c_double(TRAVEL_TIME_PENALTY), 
                               c_int(H8), c_int(H12), c_int(H13), c_int(H17), c_int(H20), c_int(TIME_INTERVAL),
                               asc_array, early_array, late_array, long_array, short_array,
                               c_int(FLEXIBLE), c_int(MIDDLE_FLEXIBLE), c_int(NOT_FLEXIBLE))

    return activity_csv, population_csv, lib

def call_to_optimizer(activity_csv, population_csv, scenario, constraints, num_act_to_select = 30, i_break= None):

    print(f"Running scenario: {scenario}")
    constraints_array = (c_int * len(constraints))(*constraints)
    lib.set_scenario_constraints(constraints_array)

    total_deviations_start = []
    total_deviations_dur = []
    DSSR_iterations = []
    execution_times = []
    final_utilities = []
    schedules = []
    ids = []
    for i, individual in tqdm(population_csv.iterrows(), total=population_csv.shape[0]):
        
        # print(f"\nIndividual : {individual['id']} || leisure_dur : {individual['leisure_dur']} || work_dur : {individual['work_dur']} || work_start : {individual['work_start']} ")
        if (i >= i_break): 
            break
                
        act_in_peri = filter_closest(activity_csv, individual, num_act_to_select)
        # print(f"\nIndividual : {individual['id']} || home : ({individual['home_x']}, {individual['home_y']}) || home : ({individual['work_x']}, {individual['work_y']})")
        # print(act_in_peri.sample(20))
        num_activities = len(act_in_peri)+4
        perso_activities_array = (Activity * num_activities)()
        activities_array = initialize_activities(act_in_peri, num_activities) 
        perso_activities_array = personalize(activities_array, num_activities, individual, group_to_type)
        lib.set_activities(perso_activities_array, num_activities)
        # for activity in perso_activities_array:
        #     print(f"ID: {activity.id}, Group: {activity.group}, desired start: {activity.des_start_time}, desired duration: {activity.des_duration}")

        lib.main()

        iter = lib.get_count()
        time = lib.get_total_time()
        schedule_pointer = lib.get_final_schedule()   
        schedule_data = extract_schedule_data(schedule_pointer, activity_csv, individual, num_activities)

        DSSR_iterations.append(iter)
        execution_times.append(time)
        schedules.append(schedule_data) 
        ids.append(individual['id'])

        if schedule_pointer and schedule_pointer.contents:
            final_utilities.append(schedule_pointer.contents.utility)
            # print(f"\n UTILITY = {schedule_pointer.contents.utility}")
            total_deviations_start.append(schedule_pointer.contents.deviation_start)
            total_deviations_dur.append(schedule_pointer.contents.deviation_dur)
        else:
            final_utilities.append(0)
            total_deviations_start.append(0)
            total_deviations_dur.append(0)

        # recursive_print(schedule_pointer)
        lib.free_bucket()
        lib.free_activities()

    results = pd.DataFrame({
        'id': ids,
        'execution_time': execution_times,
        'DSSR_iterations': DSSR_iterations,
        'utility': final_utilities,
        'total_deviation_start' : total_deviations_start,
        'total_deviation_dur' : total_deviations_dur,
        'daily_schedule': schedules  
    })

    results.to_json(f"Data/3_Generated/{scenario}.json", orient='records', lines=False, indent = 4) 


if __name__ == "__main__":
        
    activity_csv, population_csv, lib = compile_and_initialize()    

    # constraints = [
    #     leisure closure,
    #     shop closure,
    #     education closure,
    #     work closure,
    #     Outings limitation,
    #     Early curfew,
    #     Finding balance]

    constraints = {
        'Normal_life' :          [0, 0, 0, 0, 0, 0, 0],
        'Outings_limitation' :   [1, 0, 0, 0, 1, 0, 0], # partial shop close
        'Only_economy' :         [1, 1, 1, 0, 0, 0, 0],
        'Early_curfew' :         [0, 0, 0, 0, 0, 1, 0],
        'Essential_needs' :      [0, 1, 0, 1, 0, 0, 0],
        'Finding_balance' :      [0, 0, 0, 0, 0, 0, 1],
        'Impact_of_leisure' :    [1, 0, 0, 0, 0, 0, 0]
    }

    scenari = ['Normal_life', 'Outings_limitation', 'Only_economy', 'Early_curfew', 
                'Essential_needs', 'Finding_balance', 'Impact_of_leisure']
    scenari = ['Normal_life']    

    i = 100
    n = 15
    elapsed_times = []
    for scenario_name in scenari:
        start_time = time.time()
        call_to_optimizer(activity_csv, population_csv, scenario_name, constraints[scenario_name], num_act_to_select=n, i_break=i)
        end_time = time.time()
        elapsed_time = end_time - start_time
        elapsed_times.append(round(elapsed_time, 2))
        print(f"For {len(population_csv) if i > 5000 else i} individuals and {n} closest activities around their home/work, the execution time of scenario {scenario_name} is {elapsed_time:.1f} seconds\n")

    # print(elapsed_times)
    print("Creating the Post-processed files...")
    Post_processing.create_postprocess_files(LOCAL, TIME_INTERVAL, scenari, i)

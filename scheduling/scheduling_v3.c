#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

/////////////////////////////////////////////////////////////
///////////////////////// STRUCT ////////////////////////////
/////////////////////////////////////////////////////////////

typedef struct Group_mem Group_mem;                         // retiens le groupe d'une activite, et les groupes des activites avant et apres
struct Group_mem{
    int g;
    Group_mem* previous;
    Group_mem* next;
};

typedef struct Activity {
    int id;
    int earliest_start;
    int latest_start;
    int min_duration;
    int max_duration;
    int x;
    int y;
    int group;
    Group_mem* memory;
    int des_duration;
    int des_start_time;
}Activity;

typedef struct Label Label;                                 // holds data about a particular state or decision at a certain step in the process
struct Label {                                              // like a tree
    int acity;                                              // additional activity identifier ? (faster than L->act->id)
    int time;                                               // current time 
    int start_time;
    int duration;                                           // time since the start 
    double utility;                                         // cumulative utility
    Group_mem * mem;
    Label* previous;
    Activity* act;
};

// Label_List
typedef struct L_list L_list;                               // L_list est aux Label ce que group_mem est aux Activity
struct L_list{
    Label* element;
    L_list* previous;
    L_list* next;
};

/////////////////////////////////////////////////////////////

int time_factor = 5;    // VITESSE EN UNITE ?? 
int num_activities;
int horizon;
double** duration_Ut;
double** time_Ut;
L_list** bucket;
Activity* activities = NULL;
int DSSR_count;
double total_time;
Label* final_schedule;

////////////////////////
double O_start_early_F;
double O_start_early_MF;
double O_start_early_NF;

double O_start_late_F;
double O_start_late_MF;
double O_start_late_NF;

double O_dur_short_F;
double O_dur_short_MF;
double O_dur_short_NF;

double O_dur_long_F;
double O_dur_long_MF;
double O_dur_long_NF;

double beta_cost;
double beta_travel_cost;
double theta_travel;
double c_a; 
double c_t;
//////////////////////

/////////////////////////////////////////////////////////////
/////////////////////// FUNCTIONS ///////////////////////////
/////////////////////////////////////////////////////////////

int get_count() {
    return DSSR_count;
}

double get_total_time() {
    return total_time;
}

Label* get_final_schedule() {
    return final_schedule;
}

void set_num_activities(int pynum_activities) {
    num_activities = pynum_activities;
};

void set_activities_pointer(Activity* activities_array) {
    activities = activities_array;
};

void set_start_utility(double** pytime_Ut){
    time_Ut = pytime_Ut;
};

void set_duration_utility(double** pyduration_Ut){
    duration_Ut = pyduration_Ut;
};

void set_utility_parameters(double* thetas){
// void set_utility_parameters(
//     double* thetas, 
//     double beta_cost,
//     double beta_travel_cost, 
//     double theta_travel,
//     double c_a,
//     double c_t,
//     ){
    O_start_early_F = thetas[0];
    O_start_early_MF = thetas[1];
    O_start_early_NF = thetas[2];

    O_start_late_F = thetas[3];
    O_start_late_MF = thetas[4];
    O_start_late_NF = thetas[5];

    O_dur_short_F = thetas[6];
    O_dur_short_MF = thetas[7];
    O_dur_short_NF = thetas[8];

    O_dur_long_F = thetas[9];
    O_dur_long_MF = thetas[10];
    O_dur_long_NF = thetas[11];

    // beta_cost = ;
    // beta_travel_cost = ;
    // theta_travel = ;
    // c_a = ; 
    // c_t = ;
};

double distance_x(Activity* a1, Activity* a2){
    double dx = (double)(a2->x - a1->x);
    double dy = (double)(a2->y - a1->y);
    double dist = sqrt(dx * dx + dy * dy);
    return dist; 
};

int time_x(Activity* a1, Activity* a2){
    double dist = distance_x(a1, a2);
    int bubu = ceil(dist/(time_factor*60));
    return bubu; 
};

// checks if a given Activity a is present in the group memory of a Label L. 
int mem_contains(Label* L, Activity* a){ 
    if(a->group == 0){return 0;}

    Group_mem* gg = L->mem;                         // see if the group memory in Label matches the group of a.
    while(gg!= NULL){
        if(gg->g == a->group){return 1;}            // Returns 1 if there is a match
        gg=gg->next;
    }

    return 0;
};

// determines if every Group_mem in the memory of Label L1 is also contained in the memory of Label L2
int dom_mem_contains(Label* L1, Label* L2){
    // if(a->group == 0){return 0;}
    Group_mem* gg = L1->mem;

    while(gg!= NULL){                               // For every Group_mem in L1->mem
        Group_mem* gg2 = L2->mem;
        int contain = 0; 

        while(gg2 != NULL){                         // For every Group_mem in L2->mem
            if(gg->g == gg2->g){
                contain = 1;
            }
            gg2 = gg2->next;
        }

        // If a particular Group_mem from L1->mem is not in L2->mem, the function returns 0 (false)
        if(!contain){return 0;} 
        gg=gg->next;
    }
    // If all Group_mem in L1->mem are found in L2->mem, it returns 1 (true)
    return 1;
};

// checks if an Activity a is linked to the provided Label L (or its predecessors) based on the group of the activity
int contains(Label* L, Activity* a){
    if(a->group == 0){return 0;}
    while(L != NULL){
        if( L->act->group == a->group ){
            return 1;                               // If there's a match, the function returns 1 (true)
        }
        L= L->previous;
    }
    return 0;
};

// Recursively prints information about the given Label and all of its predecessors dans l'ordre du premier non null au dernier
void recursive_print(Label* L){
    if(L!=NULL){
        if(L->previous!=NULL){                                      
            recursive_print(L->previous);
        }
        printf(" act(a%d ,g%d , t%d), ", L->acity, L->act->group, L->time);
    }
};

int feasible(Label* L, Activity* a){
    /* Determines if an Activity a can be added to a sequence ending in label L. 
       It returns 1 if it's feasible and 0 if it's not. */
    
    if(L == NULL){                          // if no Label, 'a' cann't be added
        return 0;
    }                                            
    if(L->acity != 0 && a->id == 0){        // If L is an act that's not the 1st, but a is the 1st act => not feasible
        return 0;
    }
    if(L->acity != a->id){                  // If act of L isn't the same as a, do some checks
        if(L->previous !=NULL && L->previous->acity == a->id ){             // is the previous activity the same as a ? 
            return 0;
        }
        if(L->acity == num_activities -1){                                  // Ensuring the current activity isn't the last one
            return 0;
        }
        if(L->duration <  L->act->min_duration){                            // Verifying the minimum duration of the current activity
            //printf(" Minimum duration %d, %d, %d, %d \n", L->duration, L->act->min_duration, L->acity, L->act->id);
            return 0;
        }
        // temps actuel + trajet pour a + duree min de a + trajet de a a home > fin de journee 
        // Ie enough time left in the horizon to add this activity
        if(L->time + time_x(L->act, a) + a->min_duration + time_x(a, &activities[num_activities-1]) >= horizon -1){
            return 0;
        }
        // Making sure the new activity starts and ends within its allowed time window
        if(L->time + time_x(L->act, a) < a->earliest_start){
            return 0;
        }
        if(L->time + time_x(L->act, a) > a->latest_start){
            return 0;
        }
        if(mem_contains(L,a)){              // Checking if memory contains the group of the new activity
            return 0; 
        }
    }
    else{                                   // If the current activity in L is the same as a, check the duration
        if(L->duration + 1 > a->max_duration){        // max duration  
            return 0;
        }
    }
    /*if(contains(L,a)){                    // utile ?
        return 0;
    }*/
    return 1;                               // si tout va bien
};

int dominates(Label* L1, Label* L2){                                                      // UTILITY STUFF
    /* checks if Label L1 dominates Label L2 based on certain criteria. 
    It can return 0 (no dominance), 1 (L2 is NULL, so L1 dominates by default), or 2 (L1 dominates L2 based on the criteria). */

    if(L2 == NULL){return 1;}
    if(L1 == NULL){return 0;}
    if(L1->acity == L2->acity){                                 // comparaisons only if both labels are for the same activity
        if(L1->utility <= L2->utility){
            if(L1->duration == L2->duration){
                if(dom_mem_contains(L1,L2)){                    // Ensuring memory domination with dom_mem_contains.
                    return 2;
                }
            }
            else{
                if(L2->duration > L2->act->des_duration){       // pq ce if si le else fait exactement la meme chose ??
                    if(L1->utility - duration_Ut[L1->acity][L1->duration] <= L2->utility - duration_Ut[L2->acity][L2->duration]){
                        if(dom_mem_contains(L1,L2)){
                            return 2;
                        }
                    }
                }
                else{  // difference of the actual label U - U_duration of the current activity ine the label - 
                    if(L1->utility - duration_Ut[L1->acity][L1->duration] <= L2->utility - duration_Ut[L2->acity][L2->duration]){
                        if(dom_mem_contains(L1,L2)){
                            return 2;
                        }
                    }
                }
            }
        }
    }
    return 0;
};

// initializes a two-dimensional dynamic array named bucket of size a by b. Each element of this array is of type L_list
void create_bucket(int a, int b){
    // It allocates memory for a number of pointers to L_list
    // it's allocating memory for pointers, not for the actual L_list objects
    // (L_list**) is a type cast, which tells compiler to treat the returned pointer from malloc() as a pointer to a pointer to L_list
    bucket = (L_list**)malloc(a * sizeof(L_list*));                 
    for (int i = 0; i < a; i++) {
        // For each of those pointers, it allocates memory for b L_list objects
        bucket[i] = (L_list*)malloc(b * sizeof(L_list));
        for (int j = 0; j < b; j++){                            // It then initializes the properties of each L_list to NULL.
            bucket[i][j].element = NULL;
            bucket[i][j].previous = NULL;
            bucket[i][j].next = NULL;
        }
    } 
};

// recursively free memory associated with a given Group_mem and all its successors
void delete_group(Group_mem* L){
    if(L!=NULL){
        if(L->next!= NULL){
            delete_group(L->next);
        }
        free(L);
    }
};

// frees memory associated with a given L_list and all of its successors
void delete_list(L_list* L){
    if(L->next!= NULL){                                         // After reaching the last L_list in the list, it begins freeing memory.
        delete_list(L->next);
    }
    // checks if the L_list has a Label (L->element) associated with it. If so, it frees the memory of any Group_mem of the Label too
    if(L->element != NULL){
        if(L->element->mem != NULL){
            delete_group(L->element->mem);
        }
        free(L->element);
        L->element = NULL;
    }  
};

// frees up the memory occupied by the bucket
// d'abord free la memory de chaque L_list componenent, then of the bucket itself
void free_bucket(L_list** bucket, int h, int a){    
    for (int i = 0; i < h; i ++) {
        for(int j = 0; j < a; j ++){
            L_list* L = &bucket[i][j];
            delete_list(L);
            &bucket[i][j] == NULL;
        }
        free(bucket[i]);
        bucket[i]=NULL;
    }
    free(bucket);
    bucket = NULL;
};

// meme principe qu'au dessus
void free_activities(){
    for (int i = 0 ; i < num_activities; i++){
        delete_group(activities[i].memory);
    }
    free(activities);
};

Group_mem* createNode(int data) {
    /* Purpose: Allocates memory for and initializes a new Group_mem node with provided data */
    Group_mem* newNode = (Group_mem*)malloc(sizeof(Group_mem));
    newNode->g = data;
    newNode->next = NULL;
    newNode->previous = NULL;
    return newNode;
};

// Function to copy a linked list
Group_mem* copyLinkedList(Group_mem* head) {
    if (head == NULL) {
        return NULL;
    }

    // Create a new list head
    Group_mem* newHead = createNode(head->g);
    Group_mem* newCurr = newHead;
    Group_mem* curr = head->next;

    // Copy the remaining nodes
    while (curr != NULL) {
        Group_mem* newNode = createNode(curr->g);
        newCurr->next = newNode;
        newNode->previous = newCurr;
        newCurr = newCurr->next;
        curr = curr->next;
    }

    return newHead;
};

Group_mem* interLinkedLists(Group_mem* head1, Group_mem* head2, int pipi) {
    /* Creates a new linked list that contains nodes representing the union of head1 and head2 
    plus an additional node with g as pipi.*/
    int pp = 0;
    if (head1 == NULL || head2 == NULL) {
        Group_mem* newNode = createNode(pipi);
        return newNode;
    }
    Group_mem* newHead = NULL;
    Group_mem* newTail = NULL;
    Group_mem* curr1 = head1;
    
    while (curr1 != NULL) {
        Group_mem* curr2 = head2;
     
        while (curr2 != NULL) {
            
            if (curr1->g == curr2->g) {
                Group_mem* newNode = createNode(curr1->g);
                if (newHead == NULL) {
                    newHead = newNode;
                    newTail = newNode;
                } else {
                    newTail->next = newNode;
                    newNode->previous = newTail;
                    newTail = newTail->next;
                }
                break;  // Move to the next element in the first list
            }
            curr2 = curr2->next;
        }
        curr1 = curr1->next;
    }
    if(newHead == NULL){
        newHead = createNode(pipi);
        newTail = newHead;
    }else{
        newTail->next = createNode(pipi);
        newTail->next->previous = newTail;
    }
    return newHead;
};

Label* create_label(Activity* aa){
    /* Allocates memory for and initializes a new Label with the specified Activity */
    Label* L = malloc(sizeof(Label));
    L->acity  = 0;
    L->time = aa->min_duration;
    L->utility = 0;
    L->duration = aa->min_duration;
    L->previous = NULL;
    L->act = aa;
    L->mem = malloc(sizeof(Group_mem));
    L->mem->g = 0;
    L->mem->next = NULL;
    L->mem->previous = NULL;
    return L;
};

Label* label(Label* L0, Activity* a){
    /*  Generates a new label L based on an existing label L0 and an activity a */
    Label* L = malloc(sizeof(Label));
    L->acity = a->id;
    L->time = L0->time + time_x(L0->act, a);
    L->utility = L0->utility  + distance_x(L0->act ,a);                                  // UTILITY STUFF
    L->duration = L0->duration;
    
    // check whether the state remains in the same activity 
    if(a->id == L0->acity){ 
        L->time += 1; 
        L->duration += 1; 
        L->mem = copyLinkedList(L0->mem);
    }
    else{ 
        L->mem = interLinkedLists(L0->mem, a->memory, a->group);
        L->utility -= (time_Ut[L->acity][L->time]);                                  // UTILITY STUFF
        L->utility -= (duration_Ut[L0->acity][L0->duration]);                                 // UTILITY STUFF
        if(a->id == num_activities-1){
            L->duration = 0;
            L->time = horizon-1;
        }
        else{
            L->duration = a->min_duration;
            L->time += L->duration;
        }
    }

    L->previous = L0;
    L->act = a;

    return L;
};

L_list* remove_label(L_list* L){
    /* Removes the label from the provided list of label and adjusts the connections of adjacent labels. */
    free(L->element);
    L->element=NULL;
    L_list* L_re;
    if(L->previous != NULL && L->next != NULL){
        L->previous->next = L->next;
        L->next->previous = L->previous;
        L_re = L->next;
        free(L);
        return L_re;
    }
    if(L->previous != NULL && L->next == NULL){
        L->previous->next = NULL;
        L_re = NULL;
        free(L);
        return L_re;
    }
    if(L->previous == NULL && L->next != NULL){
        if(L->next->next != NULL){L->next->next->previous = L;}
        L_re = L->next;
        L->element = L_re->element;
        L->next = L->next->next;
        free(L_re);
        return L; //retunr L which has taken the values of L->next.
    }
    if(L->previous == NULL && L->next == NULL){
        return NULL;
    }
};


Label* find_best(L_list* B, int o){
    /* Finds the label with the minimum utility value from the list. 
    Returns the label with the minimum utility value. */
    double min = INFINITY;
    Label* bestL = NULL;
    L_list* li = NULL;
    li = B;
    while (li != NULL){
        if (li->element != NULL){
            if( li->element->utility < min){
                bestL = li->element;
                min = bestL->utility;
            }
        }
        li = li->next;
    }
    if(bestL == NULL){
        printf("%s", "Solution is not feasible, check parameters. ");
    }
    else{
        if(o){
            printf("Best solution value = %.2f \n" , min );
            printf("%s ", "[");
            recursive_print(bestL);
            printf("%s \n", "]");
        }
    }
    return bestL;
};

void add_memory(int at, int c){
    /* Adds memory (a Group_mem node) to an activity in the global activities array */
    if(activities[at].memory== NULL){                           // If the specified activity (indexed by at) doesn't already have memory, it initializes its memory with c.
        activities[at].memory = malloc(sizeof(Group_mem));
        activities[at].memory->g = c;
        activities[at].memory->previous = NULL;
        activities[at].memory->next = NULL;
    }
    else{                                                       // Otherwise, it finds the last node in the existing memory list and adds a new Group_mem node with g set to c at the end of the list.
        Group_mem* pp = activities[at].memory;
        while(pp->next != NULL){
            pp = pp->next;
        }
        pp->next = malloc(sizeof(Group_mem));
        pp->next->g = c;
        pp->next->previous = pp;
        pp->next->next = NULL;
    }
};

int DSSR(Label* L){
    /* To detect cycles based on the group of activities within a sequence of labels and, if a cycle is detected, update the memory of some labels in the sequence 
     "this combination has been done before" */
    double min = INFINITY;
    Label* p = L;
    int cycle = 0;
    int c_activity = 0;
    int group_activity = 0;

    while (p != NULL && cycle == 0){ // iterates through the labels starting from L in the reverse direction until it reaches the beginning or detects a cycle
        while(p != NULL && p->acity == num_activities-1){ // skips labels that correspond to the last activity
            p = p->previous;
        }
        Label* pp = p;
        while(pp != NULL && pp->acity == p->acity){ //  skips labels that have the same activity as p.
            pp = pp->previous;
        }
        while(pp != NULL && cycle == 0){ //  checks for a cycle by looking for a previous label with the same group as p. If found, records the activity and group,
            if (pp->act->group == p->act->group){
                cycle = 1;
                c_activity = p->acity;
                group_activity = p->act->group;
            }
            pp = pp->previous;
        }
        p = p->previous;
    }
    if(cycle){
        Label * pp = p;
        while(pp != NULL && pp->acity == c_activity){
            pp = pp->previous;
        }
        //printf(" >> %d \n", c_activity);
        while(pp != NULL && pp->acity != c_activity){
            //printf(" >> %d", pp->acity);
            //printf(" \n");
            add_memory(pp->acity, group_activity);
            pp = pp->previous;
        }
    }
    return cycle;
};

void DP (){
    if(bucket == NULL){
        printf(" BUCKET IS NULL %d", 0); 
    }

    Label * ll = create_label(&activities[0]);                  // starting label 
    bucket[ll->time][0].element = ll;                       // 2D data structure where the first dimension 
                                                            // represents time and the second represents activities.
   
    int count = 0;
    // les deux for imbriques vont explorer tous les schedules possibles pour chaque temps et chaque activite
    // iterates through each time unit from the start time of the initial label (ll->time) up to one unit before the horizon
    for(int h = ll->time; h < horizon-1; h++){
        for (int a0 = 0; a0 < num_activities; a0 ++){
            
            L_list* list = &bucket[h][a0];
            //if(list->element==NULL){continue;}
            while(list!=NULL)
            {
                Label* L = list->element;
                count+=1;
                for(int a1 = 0; a1 < num_activities; a1 ++){

                    // For the current label L, the function checks all possible next activities (a1). 
                    // If it's feasible to schedule the activity a1 after L, then further computations are carried out inside the loop
                    if(feasible(L, &activities[a1])){

                        //printf(" Minimum duration %d, %d, %d, %d \n", L->duration, L->act->min_duration, L->act->group, L->act->id);
                        Label* L1 = label(L, &activities[a1]);
                        int dom = 0;
                        L_list* list_1 = &bucket[L1->time][a1];
                        L_list* list_2 = &bucket[L1->time][a1];

                        while(list_1 != NULL){   

                            list_2 = list_1;

                            //if(list_1->element==NULL){break;}
                            // If a label in the bucket is dominated by L1, it's removed from the list. 
                            if(dominates(L1, list_1->element)){
                                list_1 = remove_label(list_1);
                            }
                            // Conversely, if L1 is dominated by a label in the bucket, L1 is discarded, 
                            // and no further comparison is needed for L1.
                            else{
                                if(dominates(list_1->element, L1)){
                                    free(L1);
                                    dom = 1;
                                    break;
                                }
                                list_1 = list_1->next;
                            };
                        }

                        if(!dom){
                            if(list_2->element == NULL){
                                list_2->element = L1;
                            }
                            else{
                                L_list* Ln = malloc(sizeof(L_list));
                                Ln->element = L1;
                                list_2->next = Ln;
                                Ln->next = NULL;
                                Ln->previous = list_1;
                            }
                        }
                    }
                }
                list = list->next;
            }
        }
    }
};

int main(int argc, char* argv[]){

    clock_t start_time, end_time;
    start_time = clock();
    
    horizon = 289;                                          // # de times horizons possibles en comptant 0

    // dynamic programming       
    // it's populating or updating the "bucket" with feasible solutions or labels
    create_bucket(horizon, num_activities);
    DP();                                            
    
    // This initializes li to point to the last element of the "bucket." 
    // It's presumably the final set of solutions or labels that the algorithm is interested in 
    L_list* li = &bucket[horizon-1][num_activities-1];  
    
    // This process will continue until no more cycles are detected in the best solution
    DSSR_count = 0;
    while(DSSR(find_best(li,0))){                       // detect cycles in the current best solution
        free_bucket(bucket, horizon, num_activities);
        create_bucket(horizon, num_activities);
        DP();
        DSSR_count++;
        // printf("%d", DSSR_count);
        li = &bucket[horizon-1][num_activities-1];
    };
    // printf("%d", DSSR_count);
    final_schedule = find_best(li,0); // change to 1 to print result                             //  some final action or determination is made on the best solution

    // if(li==NULL){
    //     printf( "%s","the list is null in the end ? " );
    // }
    // else if (li->element == NULL){
    //     printf( "%s","the element in list is null in the end ? " );
    // }
    // else {
    //     printf("%s, %d ", "The solution of the first element in list ", 9); // pq 9 ?
    // }

    free_bucket(bucket, horizon, num_activities);
    end_time = clock();  // Capture the ending time
    total_time = (double)(end_time - start_time) / CLOCKS_PER_SEC;
    return 0;
}
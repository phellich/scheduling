#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

int time_factor = 5;                                        // pour calculer la duree de trajet
int time_stepv= 5;
int num_activities;
int horizon;
double** duration_Ut;
double** time_Ut;

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
    int t1;
    int t2;
    int t3;
    int x;
    int y;
    int group;
    Group_mem* memory;
    int min_duration;
    double des_duration;
}Activity;

typedef struct Label Label;                                 // holds data about a particular state or decision at a certain step in the process
struct Label {                                              // like a tree
    int acity;                                              // additional activity identifier ? (faster than L->act->id)
    int time;                                               // current time 
    int duration;                                           // time since the start 
    double cost;                                            // cumulative cost
    double utility;                                         // cumulative 
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

Activity* activities;
L_list** bucket;

/////////////////////////////////////////////////////////////
/////////////////////// FUNCTIONS ///////////////////////////
/////////////////////////////////////////////////////////////

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

// NOT USED ? 
// int contains_2_cycle(Label* L, Activity* a){         
//     if(L->acity == a->id){ return 0;}
//     if(a->group == 0){return 0;}
//     if(L->act->group == a->group){return 2;}
    
//     int currentgroup = L->act->group;

//     while(L!= NULL){
//         if(L->act->group == a->group){
//             return 1;
//         }
//         if(L->act->group != currentgroup){
//             return 0;
//         }
//         L= L->previous;
//     }
//     return 0;
// };

// Recursively prints information about the given Label and all of its predecessors dans l'ordre du premier non null au dernier
void recursive_print(Label* L){
    if(L!=NULL){
        if(L->previous!=NULL){                                      
            recursive_print(L->previous);
        }
        printf(" act(a%d ,g%d , t%d), ", L->acity, L->act->group, L->time);
    }
};

// NOT USED ? 
// int contains_set(Label* L1, Label* L2){                      
//     //return 1;
//     int cont = 1;
//     Label* pp = L1;
//     while(L1->previous != NULL){
//         Label* p = L2;
//         cont = 0;
//         if(L1->act->group == L1->previous->act->group){cont =1; L1 = L1->previous; continue;}
//         if(L1->act->group !=0){
//             while (p->previous != NULL){
//                 if(L1->act->group == p->act->group){
//                     cont = 1;
//                     break;
//                 }
//                 p = p->previous;
//             }
//             if(cont == 0){
//                 return 0;
//             }
//         }else{
//             cont = 1;
//         }
//         L1 = L1->previous;
//     }
//     return cont;
// };

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
        if(L->time + time_x(L->act, a) < a->t1){
            return 0;
        }
        if(L->time + time_x(L->act, a) > a->t2){
            return 0;
        }
        //if(contains_2_cycle(L,a)){
        //    return 0; 
        //}
        if(mem_contains(L,a)){              // Checking if memory contains the group of the new activity
            return 0; 
        }
    }
    else{                                   // If the current activity in L is the same as a, check the duration
        if(L->duration + 1 > a->t3){        // sure that t3 is desired time to start ? ca serait pas le moment max de fin plutot ? 
            return 0;
        }
    }
    /*if(contains(L,a)){                    // utile ?
        return 0;
    }*/
    return 1;                               // si tout va bien
};

int dominates(Label* L1, Label* L2){
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

///////////////////////////////////////////////////////////////////
////////////////////////// CHATGPT CODE /////////////////////////// node ?
///////////////////////////////////////////////////////////////////

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

///////////////////////////////////////////////////////////////////
////////////////////// END CHATGPT CODE ///////////////////////////
///////////////////////////////////////////////////////////////////

Label* create_label(Activity* aa){
    /* Allocates memory for and initializes a new Label with the specified Activity */
    Label* L = malloc(sizeof(Label));
    L->acity  = 0;
    L->time = aa->min_duration;
    L->cost = 0;
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
    L->utility = L0->utility  + distance_x(L0->act ,a);
    L->duration = L0->duration;
    
    // check whether the state remains in the same activity 
    if(a->id == L0->acity){ 
        L->time += 1; 
        L->duration += 1; 
        L->mem = copyLinkedList(L0->mem);
    }
    else{ 
        L->mem = interLinkedLists(L0->mem, a->memory, a->group);
        L->utility -= (time_Ut[L->acity][L->time]); 
        L->utility -= (duration_Ut[L0->acity][L0->duration]);
        if(a->id == num_activities-1){
            L->duration = 0;
            L->time = horizon-1;
        }
        else{
            L->duration = a->min_duration;
            L->time += L->duration;
        }
    }

    L->cost = L0->cost + distance_x(L0->act, a);
    L->previous = L0;
    L->act = a;

    return L;
};

L_list* remove_label(L_list* L){
    /* Removes the label from the provided list node and adjusts the connections of adjacent nodes. */
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
            printf("Best solution value = %.2f , cost = %.2f\n" , min, bestL->cost );
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
    printf("\n LAUNCHING \n");
    /////// TIME THE FUNCTION ////////
    clock_t start_time, end_time;
    start_time = clock();
    double total_time;

    //////////////////////////////////////////////
    //int num_activities = atoi(argv[1]);/////////
    //int transportation_modes = atoi(argv[2]);///
    //////////////////////////////////////////////
    
    // A passer en argument, dans l'ordre des activites et groupees par type ? 
    int  x []= {84, 29, 1, 44, 71, 45, 70, 48, 3, 70, 1, 8, 79, 38, 14, 7, 75, 19, 75, 86, 46, 5, 53, 95, 22, 22, 4, 73, 20, 69, 46, 77, 29, 73, 31, 40, 91, 40, 23, 50, 90, 68, 81, 30, 68, 8, 86, 78, 85, 34, 88, 27, 57, 99, 2, 32, 19, 36, 10, 66, 41, 83, 90, 38, 99, 29, 85, 56, 15, 47, 30, 76, 17, 9, 6, 95, 80, 91, 12, 79, 51, 3, 23, 17, 43, 28, 49, 69, 51, 73, 64, 90, 29, 22, 91, 22, 66, 35, 60, 81, 92, 16, 26, 19, 6, 48, 15, 27, 28, 78, 95, 84, 29, 9, 87, 50, 12, 74, 44, 76, 49, 61, 59, 69, 21, 55, 41, 67, 55, 63, 9, 26, 4, 98, 91, 18, 79, 51, 6, 35, 81, 57, 52, 66, 51, 61, 82, 74, 74, 37};
	int  y []= {84, 37, 84, 71, 59, 90, 92, 40, 53, 2, 88, 13, 32, 68, 9, 30, 5, 68, 20, 21, 5, 25, 69, 89, 20, 48, 41, 92, 5, 93, 74, 40, 29, 3, 27, 12, 72, 98, 64, 53, 66, 14, 17, 28, 34, 82, 46, 95, 54, 78, 40, 37, 20, 42, 83, 70, 67, 22, 64, 71, 3, 85, 53, 70, 15, 53, 99, 87, 50, 35, 6, 39, 45, 73, 8, 48, 18, 1, 6, 11, 99, 45, 12, 97, 42, 66, 78, 86, 4, 99, 83, 81, 74, 99, 71, 37, 66, 61, 67, 7, 44, 48, 69, 74, 68, 33, 35, 89, 17, 2, 66, 12, 78, 43, 61, 14, 19, 73, 4, 10, 94, 84, 99, 62, 95, 61, 80, 83, 8, 25, 29, 48, 31, 85, 6, 12, 36, 62, 53, 14, 87, 11, 59, 88, 52, 40, 14, 64, 20, 40};
    
    num_activities = 60;                                    // # d'activites
    horizon = 289;                                          // # de times horizons possibles en comptant 0

    activities = malloc(num_activities*sizeof(Activity));   // reserve la memoire pour les activites
    
    for(int i = 0; i < num_activities; i++){                // initialise les parametres des activites
        activities[i].id = i;                             
        activities[i].x = x[i];
        activities[i].y = y[i];
        activities[i].t1 = 5;                               // earliest time to start
        activities[i].t2 = horizon-1;                       // latest time to start
        activities[i].t3 = horizon-1;                       // maximum duration
        activities[i].min_duration = 24;                    // en m je crois ou en time interval (2h)
        activities[i].des_duration = 30;                    // en m (ie 6*5m) ou en time inter ? 2h30
        activities[i].group = 0; // (i+1);                  // groupes initialises plus tard
    }
    
    // Traitement special pour dusk and dawn (home)
    activities[0].min_duration = 24;
    activities[0].t1 = 0;
    activities[num_activities -1].min_duration = 0;
    activities[num_activities -1].t1 = 0;
    activities[num_activities -1].t2 = horizon;
    //activities[num_activities-1].group = 9;               // HEIN ??
    //activities[num_activities-1].t1 = horizon - 100;
    
    //////////////////////////////////////////////////////////////////
    /////////////////// TIME DURATION MATRIX /////////////////////////
    //////////////////////////////////////////////////////////////////

    // Allouer l'espace memoire
    duration_Ut = (double **)malloc(num_activities * sizeof(double *)); 
    time_Ut = (double **)malloc(num_activities * sizeof(double *));
    
    // Initialiser les strating time et duration a 0 pour ttes les activites et a tout moment de la journee
    for (int i = 0; i < num_activities; i++) {
        duration_Ut[i] = (double *)malloc(horizon * sizeof(double));
        time_Ut[i] = (double *)malloc(horizon * sizeof(double));
        for (int j = 0; j < horizon; j++) {
            duration_Ut[i][j] = 0.0;
            time_Ut[i][j] = 0.0;    
        }
    }

    //////////////////////////////////////////////////////////////////
    
    // HYPER ARBITRAIRE ??
    duration_Ut[3][3] = 10; duration_Ut[3][4] = 11; duration_Ut[3][3] = 10;
    time_Ut[3][5] = 70; 
    for(int a = 0 ; a < num_activities; a++){           // BUT DE CETTE BOUCLE ?? definir les utilites de starting time ? 
        for(int i = 5; i < horizon; i++){
            time_Ut[a][i]= (1000/i);                    // pour chaque activite, de i = 5 a 289, 1000/i ? 
        }
    }


    for(int a = 1 ; a < 5; a++){                        // 
        activities[a].t1 = 24;                          // earliest time to start
        activities[a].t2 = 200;                         // desired time to start
        activities[a].group = 1;                        // group d'activite : correspondance group id et home, leisure ?
    }
    for(int a = 5 ; a < 11; a++){
        activities[a].t1 = 50;
        activities[a].t2 = 230;
        activities[a].group = 2;
    }
    for(int a = 11 ; a < 17; a++){
        activities[a].t1 = 0;
        activities[a].t2 = 255;
        activities[a].group = 3;
    }
    for(int a = 17 ; a < 24; a++){
        activities[a].t1 = 10;
        activities[a].t2 = 266;
        activities[a].group = 4;
    }
    for(int a = 24 ; a < num_activities-1; a++){
        activities[a].t1 = 40;
        activities[a].t2 = horizon;
        activities[a].group = 5;
    }
    activities[num_activities -1].group = 0;            // activities[0].group = 0 avant

    // dynamic programming       
    // it's populating or updating the "bucket" with feasible solutions or labels
    create_bucket(horizon, num_activities);
    DP();                                               
    
    // This initializes li to point to the last element of the "bucket." 
    // It's presumably the final set of solutions or labels that the algorithm is interested in 
    L_list* li = &bucket[horizon-1][num_activities-1];  
    
    // This process will continue until no more cycles are detected in the best solution
    // printf("Checkpoint 2 \n");
    int count = 0;
    while(DSSR(find_best(li,0))){                       // detect cycles in the current best solution
        free_bucket(bucket, horizon, num_activities);
        create_bucket(horizon, num_activities);
        DP();
        count++;
        li = &bucket[horizon-1][num_activities-1];
    };

    // printf("Checkpoint 3 \n");
    printf("Total DSSR iterations , %d \n", count);
    find_best(li,1);                                    //  some final action or determination is made on the best solution
    if(li==NULL){
        printf( "%s","the list is null in the end ? " );
    }
    else if (li->element == NULL){
        printf( "%s","the element in list is null in the end ? " );
    }
    else {
        printf("%s, %d ", "The solution of the first element in list ", 9); // pq 9 ?
    }
    
    // else{
    //     if(li->element==NULL){
    //         printf( "%s","the element in list is null in the end ? " );
    //     }else{
    //         printf("%s, %d ", "The solution of the first element in list ", 9);
    //     }
    // }
    //printf("%d",a);
    // printf("Checkpoint 4 \n");
    free_activities();
    free_bucket(bucket, horizon, num_activities);
    
    end_time = clock();  // Capture the ending time
    total_time = (double)(end_time - start_time) / CLOCKS_PER_SEC;
    printf("Total time used: %f seconds\n", total_time);
    return 0;
}
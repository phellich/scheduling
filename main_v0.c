#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>


/////////////////////////////////////////////////////////////
int time_factor = 5;
int time_stepv= 5;
int num_activities;
int horizon;
double** duration_Ut;
double** time_Ut;
/////////////////////////////////////////////////////////////

/////////////////////////////////////////////////////////////
///////////////////////// STRUCT ////////////////////////////
/////////////////////////////////////////////////////////////

typedef struct Group_mem Group_mem;
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

typedef struct Label Label;
struct Label {
    int acity;
    int time;
    int duration;
    double cost;
    double utility;
    Group_mem * mem;
    Label* previous;
    Activity* act;
};
typedef struct L_list L_list;
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
    double dist = dx * dx + dy * dy;
    dist = sqrt(dist);
    return dist; 
};

int time_x(Activity* a1, Activity* a2){
    double dx = (double)(a2->x - a1->x);
    double dy = (double)(a2->y - a1->y);
    double dist = dx * dx + dy * dy;
    dist = sqrt(dist);
    int bubu = ceil(dist/(time_factor*60));
    return bubu; 
};
int mem_contains(Label* L, Activity* a){
    if(a->group == 0){return 0;}
    Group_mem* gg = L->mem;
    while(gg!= NULL){
        
        if(gg->g == a->group){
            return 1;
        }
        gg=gg->next;
    }
    return 0;
};
int dom_mem_contains(Label* L1, Label* L2){
    //if(a->group == 0){return 0;}
    Group_mem* gg = L1->mem;
    while(gg!= NULL){
        Group_mem* gg2 = L2->mem;
        int contain = 0;
        while(gg2 != NULL){
            if(gg->g == gg2->g){
                contain = 1;
            }
            gg2 = gg2->next;
        }
        if(!contain){return 0;}
        gg=gg->next;
    }
    return 1;
};
int contains(Label* L, Activity* a){
    if(a->group == 0){return 0;}
    while(L != NULL){
        if( L->act->group == a->group ){
            return 1;
        }
        L= L->previous;
    }
    return 0;
};
int contains_2_cycle(Label* L, Activity* a){
    if(L->acity == a->id){ return 0;}
    if(a->group == 0){return 0;}
    if(L->act->group == a->group){return 2;}
    
    int currentgroup = L->act->group;

    while(L!= NULL){
        if(L->act->group == a->group){
            return 1;
        }
        if(L->act->group != currentgroup){
            return 0;
        }
        L= L->previous;
    }
    return 0;
};

void recursive_print(Label* L){
    if(L!=NULL){
        if(L->previous!=NULL){
            recursive_print(L->previous);
        }
        printf(" act(a%d ,g%d , t%d), ", L->acity, L->act->group, L->time);
    }
};

int contains_set(Label* L1, Label* L2){
    //return 1;
    int cont = 1;
    Label* pp = L1;
    while(L1->previous != NULL){
        Label* p = L2;
        cont = 0;
        if(L1->act->group == L1->previous->act->group){cont =1; L1 = L1->previous; continue;}
        if(L1->act->group !=0){
            while (p->previous != NULL){
                if(L1->act->group == p->act->group){
                    cont = 1;
                    break;
                }
                p = p->previous;
            }
            if(cont == 0){
                return 0;
            }
        }else{
            cont = 1;
        }
        L1 = L1->previous;
    }
    return cont;
};

int feasible(Label* L, Activity* a){
    
    if(L == NULL){return 0;}
    
    if(L->acity != 0 && a->id == 0){return 0;}
    
    if(L->acity != a->id){
        if(L->previous !=NULL && L->previous->acity == a->id ){return 0;}
        if(L->acity == num_activities -1){
            return 0;
        }
        if(L->duration <  L->act->min_duration){
            //printf(" Minimum duration %d, %d, %d, %d \n", L->duration, L->act->min_duration, L->acity, L->act->id);
            return 0;
        }
        if(L->time + time_x(L->act, a) + a->min_duration + time_x(a, &activities[num_activities-1]) >= horizon -1){
            return 0;
        }
        if(L->time + time_x(L->act, a) < a->t1){
            return 0;
        }
        if(L->time + time_x(L->act, a) > a->t2){
            return 0;
        }
        //if(contains_2_cycle(L,a)){
        //    return 0; 
        //}
        if(mem_contains(L,a)){
            return 0; 
        }
    }else{
        if(L->duration + 1 > a->t3){
            return 0;
        }
    }
    /*if(contains(L,a)){
        return 0;
    }*/
    return 1;
};

int dominates(Label* L1, Label* L2){
    if(L2 == NULL){return 1;}
    if(L1 == NULL){return 0;}
    if(L1->acity == L2->acity){
        if(L1->utility <= L2->utility){
            if(L1->duration == L2->duration){
                if(dom_mem_contains(L1,L2)){
                    return 2;
                }
            }else{
                if(L2->duration > L2->act->des_duration){
                    if(L1->utility - duration_Ut[L1->acity][L1->duration] <= L2->utility - duration_Ut[L2->acity][L2->duration]){
                        if(dom_mem_contains(L1,L2)){
                            return 2;
                        }
                    }
                }else{
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

void create_bucket(int a, int b){
    bucket = (L_list**)malloc(a * sizeof(L_list*));
    for (int i = 0; i < a; i++) {
        bucket[i] = (L_list*)malloc(b * sizeof(L_list));
        for (int j = 0; j < b; j++){
            bucket[i][j].element = NULL;bucket[i][j].previous = NULL;bucket[i][j].next = NULL;
        }
    } 
};

void delete_group(Group_mem* L){
    if(L!=NULL){
        if(L->next!= NULL){
            delete_group(L->next);
        }
        free(L);
    }
};

void delete_list(L_list* L){
    if(L->next!= NULL){
        delete_list(L->next);
    }
    if(L->element != NULL){
        if(L->element->mem != NULL){
            delete_group(L->element->mem);
        }
        free(L->element);
        L->element = NULL;
    }  
};
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

void free_activities(){
    for (int i = 0 ; i < num_activities; i++){
        delete_group(activities[i].memory);
    }
    free(activities);
};

///////////////////////////////////////////////////////////////////
////////////////////////// CHATGPT CODE ///////////////////////////
///////////////////////////////////////////////////////////////////

Group_mem* createNode(int data) {
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

Group_mem* unionLinkedLists(Group_mem* head1, Group_mem* head2, int pipi) {
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

Label* create_l(Activity* aa){
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
    Label* L = malloc(sizeof(Label));
    L->acity = a->id;
    L->time = L0->time + time_x(L0->act, a);
    L->utility = L0->utility  + distance_x(L0->act ,a);
    L->duration = L0->duration;
    
    ///////////////////////////////////////////////////////////////////////
    /////// check whether the state remains in the same activity //////////
    ///////////////////////////////////////////////////////////////////////

    if(a->id == L0->acity){ L->time += 1; L->duration += 1; L->mem = copyLinkedList(L0->mem);
    }else{ 
        L->mem = unionLinkedLists(L0->mem,a->memory, a->group);
        L->utility -= (time_Ut[L->acity][L->time]); 
        L->utility -= (duration_Ut[L0->acity][L0->duration]);
        if(a->id == num_activities-1){
            L->duration = 0;
            L->time = horizon-1;
        }else{
            L->duration = a->min_duration;
            L->time += L->duration;
        }
    }
    ////////////////////////////////////////////////////////////////////
    L->cost = L0->cost + distance_x(L0->act, a);
    L->previous = L0;
    L->act = a;
    return L;
};

L_list* l_remove(L_list* L){
    free(L->element);
    L->element=NULL;
    L_list* L_re;
    if(L->previous != NULL && L->next != NULL){
        L->previous->next = L->next;
        L->next->previous = L->previous;
        L_re = L->next;
        free(L);
        return L_re;
    }if(L->previous != NULL && L->next == NULL){
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
    }else{
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
    if(activities[at].memory== NULL){
        activities[at].memory = malloc(sizeof(Group_mem));
        activities[at].memory->g = c;
        activities[at].memory->previous = NULL;
        activities[at].memory->next = NULL;
    }else{
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
    double min = INFINITY;
    Label* p = L;
    int cycle = 0;
    int c_activity = 0;
    int group_activity = 0;
    while (p != NULL && cycle == 0){
        while(p != NULL && p->acity == num_activities-1){p = p->previous;}
        Label* pp = p;
        while(pp != NULL && pp->acity == p->acity){pp = pp->previous;}
        while(pp != NULL && cycle == 0){
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
        while(pp != NULL && pp->acity == c_activity){pp = pp->previous;}
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
    Label * ll = create_l(&activities[0]);
    
    bucket[ll->time][0].element = ll;
   
    int count = 0;
    for(int h = ll->time; h < horizon-1; h++){
        for (int a0 = 0; a0 < num_activities; a0 ++){
            
            L_list* list = &bucket[h][a0];
            //if(list->element==NULL){continue;}
            while(list!=NULL)
            {
                Label* L = list->element;
                count+=1;
                for(int a1 = 0; a1 < num_activities; a1 ++)
                {
                    if(feasible(L, &activities[a1])){

                        //printf(" Minimum duration %d, %d, %d, %d \n", L->duration, L->act->min_duration, L->act->group, L->act->id);
                        Label* L1 = label(L, &activities[a1]);
                        int dom = 0;
                        L_list* list_1 = &bucket[L1->time][a1];
                        L_list* list_2 = &bucket[L1->time][a1];
                        while(list_1 != NULL)
                        {   
                            list_2 = list_1;
                            //if(list_1->element==NULL){break;}
                            if(dominates(L1, list_1->element)){
                                list_1 = l_remove(list_1);
                            }else{
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
                            }else{
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

    /////// TIME THE FUNCTION ////////
    clock_t start_time, end_time;
    start_time = clock();
    double total_time;

    //////////////////////////////////////////////
    //int num_activities = atoi(argv[1]);/////////
    //int transportation_modes = atoi(argv[2]);///
    //////////////////////////////////////////////
    
    int  x []= {84, 29, 1, 44, 71, 45, 70, 48, 3, 70, 1, 8, 79, 38, 14, 7, 75, 19, 75, 86, 46, 5, 53, 95, 22, 22, 4, 73, 20, 69, 46, 77, 29, 73, 31, 40, 91, 40, 23, 50, 90, 68, 81, 30, 68, 8, 86, 78, 85, 34, 88, 27, 57, 99, 2, 32, 19, 36, 10, 66, 41, 83, 90, 38, 99, 29, 85, 56, 15, 47, 30, 76, 17, 9, 6, 95, 80, 91, 12, 79, 51, 3, 23, 17, 43, 28, 49, 69, 51, 73, 64, 90, 29, 22, 91, 22, 66, 35, 60, 81, 92, 16, 26, 19, 6, 48, 15, 27, 28, 78, 95, 84, 29, 9, 87, 50, 12, 74, 44, 76, 49, 61, 59, 69, 21, 55, 41, 67, 55, 63, 9, 26, 4, 98, 91, 18, 79, 51, 6, 35, 81, 57, 52, 66, 51, 61, 82, 74, 74, 37};
	int  y []= {84, 37, 84, 71, 59, 90, 92, 40, 53, 2, 88, 13, 32, 68, 9, 30, 5, 68, 20, 21, 5, 25, 69, 89, 20, 48, 41, 92, 5, 93, 74, 40, 29, 3, 27, 12, 72, 98, 64, 53, 66, 14, 17, 28, 34, 82, 46, 95, 54, 78, 40, 37, 20, 42, 83, 70, 67, 22, 64, 71, 3, 85, 53, 70, 15, 53, 99, 87, 50, 35, 6, 39, 45, 73, 8, 48, 18, 1, 6, 11, 99, 45, 12, 97, 42, 66, 78, 86, 4, 99, 83, 81, 74, 99, 71, 37, 66, 61, 67, 7, 44, 48, 69, 74, 68, 33, 35, 89, 17, 2, 66, 12, 78, 43, 61, 14, 19, 73, 4, 10, 94, 84, 99, 62, 95, 61, 80, 83, 8, 25, 29, 48, 31, 85, 6, 12, 36, 62, 53, 14, 87, 11, 59, 88, 52, 40, 14, 64, 20, 40};
    

    num_activities = 60;
    horizon = 289;

    activities = malloc(num_activities*sizeof(Activity));
    
    for(int i = 0; i < num_activities; i++){
        activities[i].id = i;
        activities[i].x = x[i];
        activities[i].y = y[i];
        activities[i].t1 = 5;
        activities[i].t2 = horizon-1;
        activities[i].t3 = horizon-1;
        activities[i].min_duration = 24;
        activities[i].des_duration = 30;
        activities[i].group = 0; // (i+1);
    }
    
    activities[0].min_duration = 24;
    activities[0].t1 = 0;
    activities[num_activities -1].min_duration = 0;
    activities[num_activities -1].t1 = 0;
    activities[num_activities -1].t2 = horizon;

    //activities[num_activities-1].group = 9;

    //activities[num_activities-1].t1 = horizon - 100;
    
    //////////////////////////////////////////////////////////////////
    /////////////////// TIME DURATION MATRIX /////////////////////////
    //////////////////////////////////////////////////////////////////

    duration_Ut = (double **)malloc(num_activities * sizeof(double *));
    time_Ut = (double **)malloc(num_activities * sizeof(double *));
    
    for (int i = 0; i < num_activities; i++) {
        duration_Ut[i] = (double *)malloc(horizon * sizeof(double));
        time_Ut[i] = (double *)malloc(horizon * sizeof(double));
        for (int j = 0; j < horizon; j++) {
            duration_Ut[i][j] = 0.0;
            time_Ut[i][j] = 0.0;    
        }
    }

    //////////////////////////////////////////////////////////////////
    
    duration_Ut[3][3] = 10; duration_Ut[3][4] = 11; duration_Ut[3][3] = 10;
    time_Ut[3][5] = 70; 
    for(int a = 0 ; a < num_activities; a++){
        for(int i = 5; i < horizon; i++){
            time_Ut[a][i]= (1000/i);
        }
    }
    for(int a = 1 ; a < 5; a++){
        activities[a].t1 = 24;
        activities[a].t2 = 200;
        activities[a].group = 1;
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
    activities[num_activities -1].group = 0;

    

    create_bucket(horizon, num_activities);
     
    DP();
    L_list* li = &bucket[horizon-1][num_activities-1];
    int count = 0;
    
    while(DSSR(find_best(li,0))){
        free_bucket(bucket, horizon, num_activities);
        create_bucket(horizon, num_activities);
        DP();
        count++;
        li = &bucket[horizon-1][num_activities-1];
    };
    printf("Total DSSR iterations , %d \n", count);
    find_best(li,1);
    if(li==NULL){printf( "%s","the list is null in the end ? " );
    }else{
        if(li->element==NULL){
            printf( "%s","the element in list is null in the end ? " );
        }else{
            printf("%s, %d ", "The solution of the first element in list ", 9);
        }
    }
    
    //printf("%d",a);
    
    free_activities();
    free_bucket(bucket, horizon, num_activities);
    end_time = clock();  // Capture the ending time
    total_time = (double)(end_time - start_time) / CLOCKS_PER_SEC;
    printf("Total time used: %f seconds\n", total_time);
    return 0;
}
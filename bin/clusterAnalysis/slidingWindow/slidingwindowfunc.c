#ifndef _SLIDINGWINDOWFUNC_C_
#define _SLIDINGWINDOWFUNC_C_

#include "structs.h"
#include "constants.h"
#include "slidingwindowfunc.h"



void UpdateCornerFile(struct corners *corners,
		      char *in_file) {

  FILE *corner_file = fopen(in_file, "w");
  if (corner_file) {
    int i;
    for (i=0; i<corners->num_corners; i++) {
      fprintf(corner_file, "%u %u\n", corners->x[i], corners->y[i]);
    }
  }
  fclose(corner_file);
}


struct cluster** RunSlidingWindowClustering(struct corners *corners,
					    unsigned int window_width,
					    unsigned int window_height) {

  struct cluster **clusters = (struct cluster **) malloc(sizeof(struct cluster)*corners->num_corners);
  if (clusters==NULL) {
    printf("Failed to allocate memory for clusters\n");
    exit(1);
  }

  unsigned int num_clusters = 0;

  struct dimensions *window = (struct dimensions *) malloc(sizeof(struct dimensions));
  if (window==NULL) {
    printf("Failed to allocate memory for window\n");
    exit(1);
  }

  unsigned int L,R,T,B;

  unsigned int *queue =(unsigned int *) malloc (sizeof(unsigned int) * corners->num_corners);
  if (queue==NULL) {
    printf("Failed to allocate memory for queue..\n");
    exit(1);
  }   
  unsigned int queue_count;
  
  unsigned int *assigned_corners = (unsigned int *) malloc(sizeof(unsigned int)*corners->num_corners);
  if (assigned_corners==NULL) {
    printf("Failed to allocate memory for assigned corners\n");
    exit(1);
  }
  unsigned int num_assigned = 0;
 
  unsigned int c1,c2,c3,c4,cl1, ac;
  unsigned int set;
  int join;
  
  //iterate over all corners
  for (c1=0; c1 < corners->num_corners; c1++) {

    set = 0;
    //then check against list of corners already in a cluster 
    for (ac=0; ac < num_assigned; ac++) {
      if (assigned_corners[ac] == c1) {
	//printf("corner %u is already assigned...\n",c1);
        set = 1;//already in cluster
        break;
      }
    }
    
    //if we didnt find a match we will make try to form a new cluster around it
    if (set==0) {
      //printf("trying to form cluster around corner %u \n", c1);
      InitWindow(window, 
		 window_width, 
		 window_height, 
		 corners, c1);
      queue_count = 0;
      queue[1] = c1;
      //check all corners against window
      for (c2=0; c2 < corners->num_corners; c2++) {   
	
	if (corners->y[c2] > window->b)
	  break;

	if (c2 != c1) {
	  if (CornerIsContainedByWindow(corners->x[c2], corners->y[c2], window)) {
	    //printf("adding corner %u to the queue\n", c2);
	    queue[queue_count] = c2;
	    queue_count++;
	  }
	}
      }
      
      //if we found more than one corner, we check to see if they are contained
      //in an already existing cluster. if they are we add everything in the current
      // queue to that cluster. if not we start a new cluster.
      if (queue_count > 1 ) {	  

	join = SearchClustersForQueuedCorners(clusters, 
					      num_clusters, 
					      queue, 
					      queue_count);
	//start a new cluster
	if (join == -1) {
	  clusters[ num_clusters ] = StartNewCluster(assigned_corners, 
						     &num_assigned,
						     queue, 
						     queue_count, 
						     &num_clusters); 
	} else {
	  //printf("Will try adding %u corners (%u) to cluster %u (total:%u)...\n", 
	  //queue_count, corners->num_corners, join, clusters[join]->size);
	  AddToCluster(assigned_corners, 
	  	       &num_assigned,
		       clusters[join], 
		       queue, 
	  	       queue_count);
	}  
      }
 
    }

  }

  /*
  free(queue);    
  queue = NULL;
  free(window);
  window = NULL;

  free(assigned_corners);
  assigned_corners = NULL;
  */

  return AmalgamateClusters(clusters,
			    &num_clusters,
			    corners,
			    window_width,
			    window_height);    
  
}



struct cluster* StartNewCluster(unsigned int *assigned,
				unsigned int *num_assigned,
				unsigned int *queue,
				unsigned int queue_count,
				unsigned int *num_clusters) {
  
  //printf("Starting new cluster %u...\n", *num_clusters);
  
  struct cluster *cluster = (struct cluster *) malloc(sizeof(struct cluster));
  if (cluster==NULL) {
    printf("Failed to allocate memory for cluster %u\n", *num_clusters);
    exit(1);
  }
  cluster->corners = (unsigned int *) malloc(sizeof(unsigned int)*queue_count);
  if (cluster->corners==NULL) {
    printf("Failed to allocate memory for cluster corners\n");
    exit(1);
  }

  cluster->size = 0;
  cluster->num = *num_clusters;
  unsigned int c, a, exists;
  for (c=0; c < queue_count; c++) {    
    cluster->corners[c] = queue[c];
    //printf("added %u\n", queue[c]);
    cluster->size+=1;

    for (a=0; a < *num_assigned; a++) {
      exists = 0;
      if (assigned[a] == queue[c]) {
	exists = 1;
	break;
      }
      if (exists==0) {
	assigned[*num_assigned] = queue[c];
	*num_assigned+=1;
      }
    }
  }

  *num_clusters+=1;
  return cluster;
}



void AddToCluster(unsigned int *assigned,
		  unsigned int *num_assigned,
		  struct cluster *cluster,
		  unsigned int *queue,
		  unsigned int queue_count) {

  unsigned int *queue2 = (unsigned int *) malloc(sizeof(unsigned int)*queue_count);
  if (queue2 == NULL) {
    printf("Failed to allocate memory for queue2...\n");
    exit(1);
  }
  
  unsigned int queue2_count = 0;

  unsigned int c1, c2, exists;
  for (c1=0; c1 < queue_count; c1++) {
    exists = 0;
    for (c2=0; c2 < cluster->size; c2++) {      
      if (queue[c1] == cluster->corners[c2]) { 
	//printf("%u exists\n", c1);
	exists = 1;
	break;
      }
    }
    if (exists == 0) {
      //printf("will add %u of %u\n",c1,queue_count);
      queue2[queue2_count] = queue[c1];
      queue2_count++;
    }       
  }

  //printf("%x\n", *cluster);  

  if (queue2_count>0) {
    unsigned int *tmp = NULL;
    tmp = realloc(cluster->corners, sizeof(unsigned int)*(queue2_count+cluster->size));				
    if (tmp==NULL) {
      printf("Failed to reallocate cluster\n");
      exit(1);
    }
    
    cluster->corners = tmp;
    tmp = NULL;

    unsigned int c ,a ,exists;;
    for(c=0; c<queue2_count; c++) {
      cluster->corners[ cluster->size ] = queue2[c];
      cluster->size+=1;    
      //printf("added %u\n", queue2[i]);
      //printf("add| num assigned %u\n", *num_assigned);
      //printf("num assigned: %u\n", *num_assigned);
      
      for (a=0; a < *num_assigned; a++) {
	exists = 0;
	if (assigned[a] == queue2[c]) {
	  exists = 1;
	  break;
	}
	if (exists==0) {
	  assigned[*num_assigned] = queue2[c];
	  *num_assigned+=1;
	}
      }
      
    }
  }
  
  free(queue2);
  queue2 = NULL;
}




void InitWindow(struct dimensions *window,
		unsigned int window_width,
		unsigned int window_height,
		struct corners *corners,
		unsigned int c) {
  
  if ((corners->x[c] - window_width) < 0)
    window->l = 0;
  else
    window->l = corners->x[c] - window_width;
  
  if ((corners->y[c] - window_height) < 0)
    window->t = 0;
  else
    window->t = corners->y[c] - window_height;
  
  window->r = corners->x[c] + window_width;
  window->b = corners->y[c] + window_height;

}



unsigned int CornerIsContainedByWindow(unsigned int x,unsigned int y,
				       struct dimensions *window) {

  if (((x >= window->l) && (x <= window->r)) && 
      ((y >= window->t) && (y <= window->b)))         
    return 1;
  else
    return 0;  
}



int SearchClustersForQueuedCorners(struct cluster **clusters,
				   unsigned int num_clusters,
				   unsigned int *queue,
				   unsigned int queue_count) {
  
  unsigned int c1,c2,cl;
  int join = -1;
  if (num_clusters > 0)
    for (c1=0; c1 < queue_count; c1++) {
      //printf("EVALUATING CORNER %u...\n",queue[c1]);
      for (cl=0; cl < num_clusters; cl++) {
	//printf("checking in cluster %u  size:%u...\n",cl, clusters[cl]->size);
	for (c2=0; c2 < clusters[cl]->size; c2++) {
	  //printf("Does corner |%u| match cluster %u value |%u|?\n", queue[c1],cl,clusters[cl]->corners[c2]);
	  if (queue[c1] == clusters[cl]->corners[c2]) {
	    //if (cl==2)
	    //printf("\nFound Match in corner %u..joining to cluster %u\n",queue[c1], cl);
	    join = cl;
	    break;
	  }
	  if (join != -1)
	    break;
	}
	if (join != -1)
	  break;
      }
      if (join != -1)
	break;
    }

  return join;
}





struct cluster ** AmalgamateClusters(struct cluster **clusters,
				     unsigned int *num_clusters,
				     struct corners *corners,
				     unsigned int window_width,
				     unsigned int window_height) {

  unsigned int *taken_clusters = (unsigned int *) malloc (sizeof(unsigned int) * *num_clusters);
  if (taken_clusters==NULL) {
    printf("Failed to allocate memory for taken clusters\n");
    exit(1);
  }
  unsigned int taken_count = 0;

  unsigned int *assigned_corners = (unsigned int *) malloc(sizeof(unsigned int)*corners->num_corners);
  if (assigned_corners==NULL) {
    printf("Failed to allocate memory for assigned corners\n");
    exit(1);
  }
  unsigned int num_assigned = 0;

  unsigned int cl1, cl2, cl3, set, exists, c, c2;

  struct dimensions *min = (struct dimensions *) malloc(sizeof(struct dimensions));
  struct dimensions *max = (struct dimensions *) malloc(sizeof(struct dimensions));

  struct dimensions *window1 = (struct dimensions *) malloc(sizeof(struct dimensions));
  struct dimensions *window2 = (struct dimensions *) malloc(sizeof(struct dimensions));


  unsigned int *queue = (unsigned int *) malloc(sizeof(unsigned int)*corners->num_corners);
  if (queue == NULL) {
    printf("Failed to allocate memory for queue...\n");
    exit(1);
  }
  unsigned int queue_count = 0;

  int total_restart_count = 0;
  int restart_count = 0;

  //if (0) {

  //loop 1... test against this cluster (primary), then injest secondary cluster if applicable
  for (cl1=0; cl1 < *num_clusters; cl1++) {

    num_assigned = 0;
    
    set = 0;
    for (cl2=0;cl2 < taken_count; cl2++)
      if (cl1 == taken_clusters[cl2]) {   
        set = 1;
        break;
      } 

    if (set == 0) {

      min->x = '\0';
      min->y = '\0';
      max->x = '\0';
      max->y = '\0';
      
      for(c=0; c < clusters[cl1]->size; c++) {      
        
	if (min->x == '\0' && min->y == '\0' && max->x == '\0' && max->y == '\0') {
	  min->x = corners->x[ clusters[cl1]->corners[c] ];
	  min->y = corners->y[ clusters[cl1]->corners[c] ];
	  max->x = corners->x[ clusters[cl1]->corners[c] ];
	  max->y = corners->y[ clusters[cl1]->corners[c] ];
	} else {
	  
	  if (corners->x[ clusters[cl1]->corners[c] ] < min->x)
	    min->x = corners->x[ clusters[cl1]->corners[c] ];
	  if (corners->y[ clusters[cl1]->corners[c] ] < min->y)
	    min->y = corners->y[ clusters[cl1]->corners[c] ];
	  if (corners->x[ clusters[cl1]->corners[c] ] > max->x)
	    max->x = corners->x[ clusters[cl1]->corners[c] ];
	  if (corners->y[ clusters[cl1]->corners[c] ] > max->y)
	    max->y = corners->y[ clusters[cl1]->corners[c] ];
	}
      }
                  
      if (min->x - window_width < 0)
        window1->l = 0;
      else
        window1->l = min->x - window_width;
      
      if (min->y - window_height < 0)
        window1->t = 0;
      else
        window1->t = min->y - window_height;
      
      window1->r = max->x + window_width;
      window1->b = max->y + window_height;
            
      //loop 2...secondary cluster to be checked/injested
      for (cl2=0; cl2 < *num_clusters; cl2++) {
        if (cl2 != cl1) {
          set = 0;
          for (cl3=0; cl3 < taken_count; cl3++)
            if (cl2 == taken_clusters[cl3]) { 
              set = 1;
              break;
            } 

	  if (set == 0) {
		
	    min->x = '\0';
	    min->y = '\0';
	    max->x = '\0';
	    max->y = '\0';
	    
	    for(c=0; c < clusters[cl2]->size; c++) {      
	      if (min->x == '\0' && min->y == '\0' && max->x == '\0' && max->y == '\0') {
		min->x = corners->x[ clusters[cl2]->corners[c] ];
		min->y = corners->y[ clusters[cl2]->corners[c] ];
		max->x = corners->x[ clusters[cl2]->corners[c] ];
		max->y = corners->y[ clusters[cl2]->corners[c] ];
	      } else {
		
		if (corners->x[ clusters[cl2]->corners[c] ] < min->x)
		  min->x = corners->x[ clusters[cl2]->corners[c] ];
		if (corners->y[ clusters[cl2]->corners[c] ] < min->y)
		  min->y = corners->y[ clusters[cl2]->corners[c] ];
		if (corners->x[ clusters[cl2]->corners[c] ] > max->x)
		  max->x = corners->x[ clusters[cl2]->corners[c] ];
		if (corners->y[ clusters[cl2]->corners[c] ] > max->y)
		  max->y = corners->y[ clusters[cl2]->corners[c] ];
	      }
	    }
            	                      
	    if (min->x - window_width < 0)
	      window2->l = 0;
	    else
	      window2->l = min->x - window_width;
	    
	    if (min->y - window_height < 0)
	      window2->t = 0;
	    else
	      window2->t = min->y - window_height;
	    
	    window2->r = max->x + window_width;
	    window2->b = max->y + window_height;

	    
	    //if the two clusters touch/overlap, lets merge secondary into primary, then start the check over 
            
	    if (((((window1->l >= window2->l) && (window1->l <= window2->r)) && 
		  (((window1->t >= window2->t) && (window1->t <= window2->b)) || 
		   (window1->t <= window2->t) && (window1->b >= window2->t))) ||
		 (((window1->l <= window2->l) && (window1->r >= window2->l)) && 
		  (((window1->t >= window2->t) && (window1->t <= window2->b)) || 
		   ((window1->t <= window2->t) && (window1->b >= window2->t))))) ||
		
		((((window2->l >= window1->l) && (window2->l <= window1->r)) && 
		  (((window2->t >= window1->t) && (window2->t <= window1->b)) || 
		   (window2->t <= window1->t) && (window2->b >= window1->t))) ||
		 (((window2->l <= window1->l) && (window2->r >= window1->l)) && 
		  (((window2->t >= window1->t) && (window2->t <= window1->b)) || 
		   ((window2->t <= window1->t) && (window2->b >= window1->t))))) ||
		
		( (((window1->l >= window2->l)&&(window1->l <= window2->r)) && 
		   (((window1->t >= window2->t)&&(window1->t <= window2->b)) || 
		    ((window1->t <= window2->t)&&(window1->b >= window2->b)))) || 
		  (((window1->l <= window2->l)&&(window1->r >= window2->l)) && 
		   (((window1->t >= window2->t)&&(window1->t <= window2->b)) || 
		    ((window1->b >= window2->t)&&(window1->b <= window2->b)) || 
		    ((window1->t < window2->t)&&(window1->b > window2->b)))) ))
	      {                
	    
		/*
		total_restart_count++;
		restart_count++;
		if (restart_count == 2000) {
		  //printf("w:%d  h:%d\n", window_width, window_height);
		  window_width *= 5;
		  window_height *= 5;
		  restart_count = 0;
		}
		*/

		//printf("cluster %u size:%u  overlaps   cluster %u size:%u\n", 
	      	//     cl1, clusters[cl1]->size,
	      	//     cl2, clusters[cl2]->size);
		queue_count=0;
	      for (c2=0; c2 < clusters[cl2]->size; c2++) {
		exists = 0;
		for (c=0; c < clusters[cl1]->size; c++) {
		  if (clusters[cl1]->corners[c] == clusters[cl2]->corners[c2]) {
		    exists = 1;
		    break;
		  }
		}

		if (exists==0) {
		  queue[ queue_count ] = clusters[cl2]->corners[c2]; 
		  queue_count++;
		}    
	      }
	      
	      if (queue_count > 0) {
		//printf("adding %u to cluster %u\n",queue_count, cl1);
		AddToCluster(assigned_corners, 
			     &num_assigned,
			     clusters[cl1], 
			     queue, 
			     queue_count);
		//printf("cluster %u size:%u  overlaps   cluster %u size:%u\n", 
		//       cl1, clusters[cl1]->size,
		//       cl2, clusters[cl2]->size);
		min->x = '\0';
		min->y = '\0';
		max->x = '\0';
		max->y = '\0';

		for (c=0; c < clusters[cl1]->size; c++) {      
		  if (min->x == '\0' && min->y == '\0' && max->x == '\0' && max->y == '\0') {
		    min->x = corners->x[ clusters[cl1]->corners[c] ];
		    min->y = corners->y[ clusters[cl1]->corners[c] ];
		    max->x = corners->x[ clusters[cl1]->corners[c] ];
		    max->y = corners->y[ clusters[cl1]->corners[c] ];
		  } else {
		    if (corners->x[ clusters[cl1]->corners[c] ] < min->x)
		      min->x = corners->x[ clusters[cl1]->corners[c] ];
		    if (corners->y[ clusters[cl1]->corners[c] ] < min->y)
		      min->y = corners->y[ clusters[cl1]->corners[c] ];
		    if (corners->x[ clusters[cl1]->corners[c] ] > max->x)
		      max->x = corners->x[ clusters[cl1]->corners[c] ];
		    if (corners->y[ clusters[cl1]->corners[c] ] > max->y)
		      max->y = corners->y[ clusters[cl1]->corners[c] ];
		  }
		}
		
		if (min->x - window_width < 0)
		  window1->l = 0;
		else
		  window1->l = min->x - window_width;
		
		if (min->y - window_height < 0)
		  window1->t = 0;
		else
		  window1->t = min->y - window_height;
		
		window1->r = max->x + window_width;
		window1->b = max->y + window_height;
		
		//blacklist/free secondary cluster, then reset loop 2 position            
                //clusters->cluster[p2] = '\0';
                //free(clusters[cl2]->corners);
		//clusters[cl2]->corners = NULL;
		//free(clusters[cl2]);
		//clusters[cl2] = NULL;
                taken_clusters[taken_count] = cl2;
                taken_count++;
                cl2 = -1; 
	      }
	    } 
	  }
	  
	}
      }
    }

  }

  //printf("restart_count: %d\n", total_restart_count);  

  //  }
  struct dimensions *tmp = (struct dimensions *) malloc(sizeof(struct dimensions));
  
  unsigned int cl, j = 0;
  //unsigned int j = 0;
  for (cl=0; cl < *num_clusters; cl++) {
    set = 0;
    for(cl2=0; cl2 < taken_count; cl2++) {
      if (cl == taken_clusters[cl2]) {
	set = 1;
	break;
      }      
    }

    if (set==0) {
      tmp->l = '\0';
      tmp->t = '\0';
      tmp->r = '\0';
      tmp->b = '\0';
    
      for (c=0; c < clusters[cl]->size; c++) {
	
	if (tmp->l=='\0' && tmp->r=='\0' && tmp->t=='\0' && tmp->b=='\0') {

	  tmp->l = corners->x [ clusters[cl]->corners[c] ];
	  tmp->t = corners->y [ clusters[cl]->corners[c] ];
	  tmp->r = corners->x [ clusters[cl]->corners[c] ];
	  tmp->b = corners->y [ clusters[cl]->corners[c] ];            

	} else {
	  if (corners->x [ clusters[cl]->corners[c] ] < tmp->l)
	    tmp->l = corners->x [ clusters[cl]->corners[c] ];
	  if (corners->y [ clusters[cl]->corners[c] ] < tmp->t)
	    tmp->t = corners->y [ clusters[cl]->corners[c] ];
	  if (corners->x [ clusters[cl]->corners[c] ] > tmp->r)
	    tmp->r = corners->x [ clusters[cl]->corners[c] ];
	  if (corners->y [ clusters[cl]->corners[c] ] > tmp->b)
	    tmp->b = corners->y [ clusters[cl]->corners[c] ];     
	}
      }
      
#if !DESKEW_OUT      
      clusters[j]->dimensions.l = tmp->l;
      clusters[j]->dimensions.t = tmp->t;
      clusters[j]->dimensions.r = tmp->r;
      clusters[j]->dimensions.b = tmp->b;
      clusters[j]->dimensions.size = clusters[cl]->size;
#endif
      
#if DESKEW_OUT

      unsigned int mx = corners->mx;
      unsigned int my = corners->my;
      float deskew_angle = 0 - corners->skew_angle;
      
      clusters[j]->dimensions.l = ((( (int)tmp->l - (int)mx) * cosf(DEG2RAD(deskew_angle))) - 
				   (( (int)tmp->t - (int)my) * sinf(DEG2RAD(deskew_angle))) + (int)mx);
      
      clusters[j]->dimensions.t = ((( (int)tmp->l - (int)mx) * sinf(DEG2RAD(deskew_angle))) + 
				   (( (int)tmp->t - (int)my) * cosf(DEG2RAD(deskew_angle))) + (int)my);
      
      clusters[j]->dimensions.r = ((( (int)tmp->r - (int)mx) * cosf(DEG2RAD(deskew_angle))) - 
				   (( (int)tmp->b - (int)my) * sinf(DEG2RAD(deskew_angle)) ) + (int)mx);
      
      clusters[j]->dimensions.b = ((( (int)tmp->r - (int)mx) * sinf(DEG2RAD(deskew_angle))) + 
				   (( (int)tmp->b - (int)my) * cosf(DEG2RAD(deskew_angle)) ) + (int)my);

      clusters[j]->dimensions.size = clusters[cl]->size;
#endif
      j++;
    } 
  }
  
  *num_clusters = j;
  
  clusters[0]->num_clusters = *num_clusters;


  free(taken_clusters);
  taken_clusters = NULL;
  
  free(assigned_corners);
  assigned_corners = NULL;

  free(min);
  min = NULL;

  free(max);
  max = NULL;

  free(window1);
  window1 = NULL;

  free(window2);
  window2 = NULL;
  
  free(tmp);
  tmp=NULL;

  free(queue);
  queue=NULL;

  return clusters;

}




void WriteClusters(char *out_file,
		   struct cluster **clusters) {

  int cl;
  if (strcmp("stdout", out_file)==0) 
    for (cl=0; cl < clusters[0]->num_clusters; cl++)
      fprintf(stdout,"%u %u %u %u %u\n",
	      clusters[cl]->dimensions.l,
	      clusters[cl]->dimensions.t,
	      clusters[cl]->dimensions.r,
	      clusters[cl]->dimensions.b,
	      clusters[cl]->dimensions.size);  
  else {
    FILE *out = fopen(out_file, "w");
    for (cl=0; cl < clusters[0]->num_clusters; cl++) {
      fprintf(out,"%u %u %u %u %u\n",
	      clusters[cl]->dimensions.l,
	      clusters[cl]->dimensions.t,
	      clusters[cl]->dimensions.r,
	      clusters[cl]->dimensions.b,
	      clusters[cl]->dimensions.size);  
    }
    fclose(out);
  }    
}
	  







#endif



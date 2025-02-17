#ifndef _STRUCTS_H_
#define _STRUCTS_H_

struct regions {
  struct segment *segments;
};

struct segment {
  int numElements,start,end,init;
};

struct dimensions {
  unsigned int l,r,t,b,x,y,w,h,size;
};

struct stats {
  double mean,sd,min,max;
};

typedef struct { int x, y; } xy; 

struct corners {
  unsigned int *x;
  //unsigned int *x_key;
  unsigned int *y;
  //unsigned int *y_key;
  //unsigned int *assigned;
  unsigned int num_corners;
  unsigned int mx, my;
  float skew_angle;
};


/*
struct clusters {
  unsigned int **cluster;
  unsigned int *cluster_size;
  unsigned int num_clusters;
  unsigned int mx, my;
  unsigned int window_width, window_height;
  float skew_angle;
  struct dimensions *dimensions;
};
*/


struct OPTICS_OBJECT {
  int x,y;
  int num;
  float reachability_distance;
  float core_distance;
};


struct cluster {
  unsigned int *corners;
  unsigned int size;
  unsigned int num;
  unsigned int num_clusters;
  //unsigned int mx, my;
  //unsigned int window_width, window_height;
  //float skew_angle;
  struct dimensions dimensions;
};


struct fouriercomponents {
  double **signals,signal_size,signal_count,
    **real,**imag,**freq,**magnitude,**phase;
  unsigned int scan_mode;
}; 

struct bandfilter {
  double **freqcomb,*peak_magnitudes,
    *_1hz_magnitudes;
  unsigned int sig_start_freq,sig_bandwidth,
    ref_start_freq,ref_bandwidth,
    *peaks,peak_count,
    scan_mode;
};


#endif

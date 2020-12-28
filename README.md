# RASR
---
Re-entry Analyses from Serendipitous Radar data
ver 3.0

Benjamin Miller <benjamin.g.miller@utexas.edu>  
Yash Sarda <ysarda@utexas.edu>  
Robby Keh <robbykeh@utexas.edu>  

Computational Astronautical Sciences and Technologies (CAST), @ The University of Texas at Austin
12/26/2020

## 1. SUMMARY
---
This algorithm searches the NOAA NEXRAD Level II Doppler Radar archive for phenomena indicating meteoroid falls.  For a given set of dates, archive files from across all available radar sites are retrieved \[1] and unwrapped using the Python ARM Radar Toolkit by \[2].  Latitude/longitude/altitude data is returned for all detections.  The original problem was motivated by \[3], and was developed using the [ARES](https://ares.jsc.nasa.gov/meteorite-falls/) database.  The current algorithm uses a PyTorch convolutional neural network object detection algorithm to identify fall velocity signatures, based on the Detecto framework. Tested on Ubuntu 20.04 locally.

> \[1] Staniewicz, S., Keh, R. (2018). Maual_Input_Scraper.py. The University of Texas at Austin
>
> \[2] Helmus, J.J. & Collis, S.M., (2016). The Python ARM Radar Toolkit (Py-ART), a Library for Working with Weather Radar Data in the Python Programming Language. Journal of Open Research Software. 4(1), p.e25. DOI: http://doi.org/10.5334/jors.119
>
> \[3] Fries, M. & Fries, J., (2010). Doppler Weather Radar as a Meteorite Recovery Tool. Meteoritics & Planetary Sciences 45, Nr. 9, 1476-1487. DOI: 10.1111/j.1945-5100.2010.01115.x


## 2. REQUIREMENTS
---
Python (3.8)  
arm_pyart (1.11)  
beautifulsoup4 (4.9.3)  
detecto (1.2.0)  
matplotlib (3.2.3)
netCDF4 (1.5.3)    
numpy (1.19.2)  
pip (20.3.3)  
requests (2.24.0)  
torch (1.7.1)  
tqdm (4.54.1)  

Check envs/ for conda environment file:
~~~
cd envs
conda env create --file rasrenv.yml
~~~


## 3. TRAINING
---
For training on full size images, add them and their respective labels to 2500/train and 2500/test. Aim for anywhere between a 70/30 to 90/10  train-to-test split. Otherwise, adjust the learning rate, epochs, and directories as needed. Run the training script as below:
~~~
conda activate rasr
cd training
python torchtrain.py
conda deactivate
~~~

## 4. TEST
---
To test if your environment is set up properly, run the following:
~~~
conda activate rasr
python get/rasr_get_test.py
python detect/torchdetect_test.py
conda deactivate
~~~
You should get example detection images and a json file with relevant data in test/.

## 5. OPERATION
---
RASR should be run daily, either manually with a bash file (I don't recommend this) or as part of a cron job. The commands are as follows:
~~~
conda activate rasr
python get/rasr_get.py x
python detect/torchdetect.py x
conda deactivate
~~~
**Include x to specify the number of processes, useful for running with parallel computing capable machines. If you omit x, RASR will automatically detect how many CPUs you have available and proceed from there.

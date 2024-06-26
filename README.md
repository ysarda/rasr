# RASR
---
Re-entry Analyses from Serendipitous Radar data
ver 4.0

Benjamin Miller <benjamin.g.miller@utexas.edu>  
Yash Sarda <ysarda@utexas.edu>  
Carson Lansdowne <carson.l@utexas.edu>   
Robby Keh <robbykeh@utexas.edu>  

Computational Astronautical Sciences and Technologies (CAST), @ The University of Texas at Austin
12/26/2020

## 1. SUMMARY
---
This algorithm searches the NOAA NEXRAD Level II Doppler Radar archive for phenomena indicating meteoroid falls.  For a given set of dates, archive files from across all available radar sites are retrieved \[1] and unwrapped using the Python ARM Radar Toolkit by \[2].  Latitude/longitude/altitude data is returned for all detections.  The original problem was motivated by \[3], and was developed using the [ARES](https://ares.jsc.nasa.gov/meteorite-falls/) database.  The current algorithm uses a PyTorch convolutional neural network object detection algorithm to identify fall velocity signatures, based on the Detecto framework. Tested on Ubuntu 20.04 locally.

Ver. 4.0 includes experimental CNN classifiers as well an experimental CNN LSTM recurrent neural network that incorporates data from a single series of radar sweeps in order to identify a detection. Additionally, the branch rasr_TACC runs on the Texas Advanced Computing Center compute hardware, for training and daily runs of the RASR Process.

> \[1] Staniewicz, S., Keh, R. (2018). Maual_Input_Scraper.py. The University of Texas at Austin
>
> \[2] Helmus, J.J. & Collis, S.M., (2016). The Python ARM Radar Toolkit (Py-ART), a Library for Working with Weather Radar Data in the Python Programming Language. Journal of Open Research Software. 4(1), p.e25. DOI: http://doi.org/10.5334/jors.119
>
> \[3] Fries, M. & Fries, J., (2010). Doppler Weather Radar as a Meteorite Recovery Tool. Meteoritics & Planetary Sciences 45, Nr. 9, 1476-1487. DOI: 10.1111/j.1945-5100.2010.01115.x


## 2. REQUIREMENTS & SETUP
---
Python (3.8)  
arm_pyart (1.11)  
beautifulsoup4 (4.9.3)  
detecto (1.2.0)     
geojson (2.5.0)  
matplotlib (3.2.3)  
netCDF4 (1.5.3)    
numpy (1.19.2)  
pip (20.3.3)    
pymap3d (2.4.3)     
requests (2.24.0)  
torch (1.7.1)  
tqdm (4.54.1)  

In order to setup the RASR Process, follow the steps below from the main rasr directory:
~~~
cd envs
conda env create --file rasrenv.yml
conda activate rasr
pip install -e .
~~~

Ensure that the arm_pyart library has installed correctly. It may need to be installed manually here, you must download arm-pyart/pyart from their GitHub: https://arm-doe.github.io/pyart/userguide/INSTALL.html


## 3. TRAINING
---
For training on full size images of radar velocity data, add them and their respective labels to training/2500/train and training/2500/test. Aim for anywhere between a 70/30 to 90/10  train-to-test split. Otherwise, adjust the learning rate, epochs, and directories as needed. To train on the basic radar velocity dataset, run the training script as below:
~~~
conda activate rasr
python scripts/torch_train.py
conda deactivate
~~~

For training on other data fields such as reflectivity, labelled data can be found in training/all_fields. Additionally, data for Time Series models (CRNN) can be found in training/Time_Series and is sorted into test and train datasets.

## 4. TEST
---
To test if your environment is set up properly, run the following:
~~~
conda activate rasr
python scripts/rasr_get_test.py
python scripts/rasr_detect_test.py
conda deactivate
~~~
You should get example detection images and a json file with relevant data in test/. Similarly, you can test the full code:
~~~
conda activate rasr
python scripts/rasr_get.py x
python scripts/rasr_detect.py x
conda deactivate
~~~
**Include x to specify the number of processes, useful for running with parallel computing capable machines. If you omit x, RASR will automatically detect how many CPUs you have available and proceed from there.

## 5. OPERATION ON TACC
---
The full entry analysis algorithm is intended to run automatically and is programmed for use on TACC. In order to do this, first ensure that the proper environment is activated by adding the following to your .bashrc file after conda setup:
~~~
conda activate rasr
~~~
Jobs will be submitted under rasr_TACC files which call the following python scripts from the main repo:
~~~
python scripts/rasr_get.py
python scripts/rasr_detect.py
python scripts/rasr_pipeline.py
~~~
These commands will scrape data from NOAA repositories online, run the loaded model for detections, and flag daily detections placing the detection and the raw file in an archive in the rasr repository.

RASR should be run daily, either manually with a bash file (not recommended) or as part of a cron job. Note that the radar sweeps this is run on everyday can easily be edited in the rasr_get.py file.

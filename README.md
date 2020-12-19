# rasr
Re-entry Analyses from Serendipitous Radar data
ver 2.0

Benjamin Miller <benjamin.g.miller@utexas.edu>  
Yash Sarda <ysarda@utexas.edu>

The University of Texas at Austin
08/05/2020

---

## 1. SUMMARY

This algorithm searches the NOAA NEXRAD Level II Doppler Radar archive for phenomena indicating meteoroid falls.  For a given set of dates, archive files from across all available radar sites are retrieved \[1] and unwrapped using the Python ARM Radar Toolkit by \[2].  Latitude/longitude/altitude data is returned for all detections.  The original problem was motivated by \[3], and was developed using NEXRAD data for West, TX on 15 Feb, 2009.  The current algorithm uses a convolutional neural network to identify fall velocity signatures.

> \[1] Staniewicz, S., Keh, R. (2018). Maual_Input_Scraper.py. The University of Texas at Austin
>
> \[2] Helmus, J.J. & Collis, S.M., (2016). The Python ARM Radar Toolkit (Py-ART), a Library for Working with Weather Radar Data in the Python Programming Language. Journal of Open Research Software. 4(1), p.e25. DOI: http://doi.org/10.5334/jors.119
>
> \[3] Fries, M. & Fries, J., (2010). Doppler Weather Radar as a Meteorite Recovery Tool. Meteoritics & Planetary Sciences 45, Nr. 9, 1476-1487. DOI: 10.1111/j.1945-5100.2010.01115.x


---

## 2. REQUIREMENTS

(env file attached, but just in case)

Python (3.7)  
Py-ART (1.11)  
NumPy (1.18.5)  
SciPy (1.5.0)  
matplotlib (3.2.2)  
netCDF4 (1.5.3)  
beautifulsoup4 (4.9.1)
requests (2.24.0)
Tensorflow (2.1.0)

Tested on Ubuntu 20.04 locally
---

## 3. VERSION NOTES



---

## 4. OPERATION
---
BASH File:
#!/bin/bash
cd ~
cd Research/rasr
conda activate rasr
python get/rasr_get.py
python detect/tf_detect.py
conda deactivate
cd ~

## 5. Training
---
Generating training/testing records:
>cd RASR/tf/scripts
>
>python generate_tfrecord.py -x ../images/train -l ../images/annotations/label_map.pbtxt -o ../images/annotations/train.record
>
>python generate_tfrecord.py -x ../images/test -l ../images/annotations/label_map.pbtxt -o ../images/annotations/test.record

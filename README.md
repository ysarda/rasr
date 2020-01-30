# rasr
Re-entry Analyses from Serendipitous Radar data
ver 1.0
(Previously "MeteorFinder")

Benjamin Miller <benjamin.g.miller@utexas.edu>  
The University of Texas at Austin 

01/21/2020

---

## 1. SUMMARY

This algorithm searches the NOAA NEXRAD Level II Doppler Radar archive for phenomena indicating meteoroid falls.  For a given set of dates, archive files from across all available radar sites are retrieved \[1] and unwrapped using the Python ARM Radar Toolkit by \[2].  Latitude/longitude/altitude data is returned for all detections.  The original problem was motivated by \[3], and was developed using NEXRAD data for West, TX on 15 Feb, 2009.  The current algorithm uses radial velocity and spectral width data, with edge detection software in *Locator.py* by \[4].

> \[1] Staniewicz, S., Keh, R. (2018). Maual_Input_Scraper.py. The University of Texas at Austin
>
> \[2] Helmus, J.J. & Collis, S.M., (2016). The Python ARM Radar Toolkit (Py-ART), a Library for Working with Weather Radar Data in the Python Programming Language. Journal of Open Research Software. 4(1), p.e25. DOI: http://doi.org/10.5334/jors.119
>
> \[3] Fries, M. & Fries, J., (2010). Doppler Weather Radar as a Meteorite Recovery Tool. Meteoritics & Planetary Sciences 45, Nr. 9, 1476-1487. DOI: 10.1111/j.1945-5100.2010.01115.x 
>
> \[4] Henriques, J., (2010). Fast Edges of a Color Image: coloredges.m v.1.1.0.0. Mathworks File Exchange

---

## 2. REQUIREMENTS

Python (3.6.6)  
Py-ART (1.9.2)  
NumPy (1.15.4)  
SciPy (1.1.0)  
matplotlib (3.0.2)  
netCDF4 (1.4.2)  
opencv (3.4.4)  
bs4 (4.7.1) 
requests (2.21.0)

Tested on Windows 7
Tested on Spyder IDE; known issues with PyCharm

---

## 3. VERSION NOTES

v0.1: Initial release.  KFWS fall confirmed with 1 ID at 16:53:32, no false positves over the full date 2/15/2009.

v0.2: KLRX fall confirmed in KnownFalls.txt, 2 ID's identified for previously known KFWS event.  Outputs include latitude/longitude/altitude for each ID. 

---

## 4. OPERATION

The "Master_MeteorFinder.py" function provides a simple interface for selecting the following variables.  For a demonstration, please see the *Files* folder 

- "dates": Interval of start/end dates as an int array \[yyyy,m,d,yyyy,m,d] \(default \[2009, 2, 15, 2009, 2, 16]).  Options: 1992-present  
- "times": Interval of start/end times for each day as an int array \[hhmmss, hhmmss] \(default \[000000,245960]).  Note that zeros cannot precede numbers, and thus may be excluded.  
- "stations": String list of 4-letter codes or 'all' \(default \['KFWS']).  Options: see FullStationList.txt.  
- "colorCutoff": Uint8 cutoff for valid color-coded measurements \(default 100)   
- "edgeIntensity": Float cutoff for intesity of velocity edges \(default 15)   
- "sizeFilter": Scalar ratio of image area to blob area for trimming small bodies  \(default 1e-4)  
- "circularityFilter": Scalar ratio of blob area to enclosing circle area for trimming anomolous bodies \(default 0.3)  
- "fillFilter": Precentage of velocity phenomena which must contain high velocity gradients, filtering out trivial phenomena.  \(default 50) 

When running the program, the algorithm will fetch the NEXRAD data corresponding to the selected dates, times, and WGS-88D sites.  The console will display a record of the current data and site, followed by updates on the current time.  For each time instant, the console will display the unwrapped altitude cut for reasurrance.  An alert will be displayed whenever a fall phenomena is detected, indicating the altitude cut of interest, and the respective data images will be saved for manual analysis in the site code folder.  See the *Example Detection* folder for the results of the West, TX event (KFWS 02/15/2009 16:53:32).  Other known falls are stored in the *KnownFalls.txt* file.  

---

## 5. SUBPROCESSES

### GetArchive.py 
This primary subprocess controls the retrieval of the NEXRAD archive files via the bs4 package.  The main function organizes folder instantiation and sorting.  The called subfunctions "save_links" records the entire archive contents for calling by "download_link", which will filter relevent times before calling the Unwrapper.  Additional subfunctions download the respective files from the recorded links and format date ranges.  The colormaps for the Unwrapper are also instantiated for optimization.         

### Unwrapper.py
This secondary subprocess opens the retrieved radar image set and formats the relevant data by scan order for further analysis.  The private graphing methods of the py-art package are modified and passed into custom matplotlib figures for high resolution image-format data, and these data are handed to the Locator as bgr image lists.  This subprocess runs for each time-specific archive retrieved by the parent process, and the level of scans will change based on the operation of the local radar station at any given time.  If falls are identified, the latitude/longitude/altitude positions are calculated by Py-ART's azimuthal equidistant projection.        

### Locator.py
This tertiary subprocess finally looks for phenomena of interest within the retrieved data.  In this process, velocity images are analyzed first as they are robust to false-positives.  The color content and radial distance from the station are used as preliminary image masks.  Then, color gradients are calculated and trivial solutions are removed.  Using contour-based object detection, remaining gradient data is filtered based on area, shape, and edge density.  The altidude cuts are collapsed prior to identification, exluding the lowermost quarter cuts.  Valid targets are added to a candidate list, and the spectrum width algorithm runs.  For spectrum width processing, the preliminary filtering is followed directly by object detection, applying area, shape, and density filters.  If the two data type algorithms result in a single matching scan level candidate, the algorithm loosens detection restrictions and captures all markers present in the spectrum width data.  The respective unprocessed images are saved, and the user is alerted of the altitudes and LLA positions through the Unwrapper.            

	
pwrasrGet:
	Setup:
		cd <directory/rasrGet>
		#check for awskeys.txt file
		pipenv shell
		#only do install for initial setup
		pipenv install --ignore-pipfile
	Test:
		python rasr_get_test 1
		#Will store file KFWS20090215_165332 to /tmp
	Run:
		python rasr_get <processes to run>
		#processes defaults to number of CPUs
		#retrieved data stored to /tmp


rasrDetect:

	Setup: 
		cd <directory/rasrDetect>
		#move all files of interest to /tmp 
		pipenv shell 
		#only do install for initial setup
		pipenv install --ignore-pipfile 
	Test: 
		python rasr_detect_test.py 1 False
		#Will output 2 lines to the /out/out.txt file using /tmptest file
	Run:
		python rasr_detect.py <processes to run> False
		#processes defaults to number of CPUs
		#see /out/out.txt for any detections, no output in general

	BASH:
		dos2unix rasr_detect.job
		sbatch rasr_detect.job

misc:
	set Path="%PATH%;ProgramFiles%\putty"
	cd C:/Program Files/putty
	pscp c:\Users\Ben\Desktop\foo.txt bgmiller@stampede2.tacc.utexas.edu:/work/xxx/bgmiller/stampede2/rasrDetect
	
	cd $WORK 
	pwd
	<install to /work/xxx/bgmiller/stampede2>
	tar xvzf rasrDetect.tar.gz
	cd $WORK/rasrDetect
	module load python3
	pip3 install --user pipenv
	python3 -m site --user-base
	export PATH=$PATH:/home1/06582/bgmiller/.local/bin
	<proceed with setup>
	squeue -u bgmiller 
	ls -1 [/scratch/06582/bgmiller/gpfs/corral3/repl/utexas/MOST/NOAA_Data_Collection] | wc -l
	find $SCRATCH/ -type d -empty [-print OR -delete] | wc -l
	

	tar -zcvf NOAA_Data_Collection.tar.gz /gpfs/corral3/repl/utexas/MOST/NOAA_Data_Collection
	cp /gpfs/corral3/repl/utexas/MOST/NOAA_Data_Collection.tar.gz $SCRATCH/
	cds
	tar -zxvf NOAA_Data_Collection.tar.gz

new directory /scratch/06582/bgmiller/gpfs/corral3/repl/utexas/MOST/NOAA_Data_Collection
	
job is slurm-4101382.out ran out, 48mm not 48hh
job slurm-4101911.out run with 100, not 16, canceled at 5 hrs cuz we need Nodes=1
job slurm-4104194.out , 

if our time runs out, we'll reduce to running just one of the sub folders to check processing, and then repete that step

4153./160 = 25,26 runs 
just upload noew rasr_detect.py and run, will need to watch email to ensure I have quick turn around
slurm-4112874.out - memory error, fix typo on join -> semaphore leak and memory
4112937 - somehow i now have 20.5 not 21.3 GB...check at 8:30, no progress
4113295 - cant use getcontext spawn with threadpool
4113308 - no immediate errors, not necessarily fast but should close if i give it time.  Ideally, i can instantiate 1 thread per CPU and the system wont get as confused as regular pooling 
	am running cores/4 threads (68 cores/node = 17 processes).  
	160/17 = 10 runs.  160/34 = 5 processes, ob. double 
	assume 5 minutes/process for overhead.  [50, 25] min check.
	shaved .1gB in 45 min as expected.  Hoping to get 10-15 min for .1gB now   
	some error with multiple plots open, due to multithread?

4113834 starts at 20.4G
	still slow.  NEED the processes, but they were thread-hungry, which makes no sense 
4114453 - retry spawn.pool with 1/4 cpu and imap.  last time we got "could not spawn"ls -l
	got to 19.6, so it's working, but still think it hangs
4114511 - hits 169 thread error, not 270... so better?  if i do /8... 19.5G
4114587 - actually encountered MORE threading errors, tied to external memory?
4114645 - hit the 270 thread error again, even when I used the routine close :(
	19.3 memory, so another close out thankfully, but cant yet do everything...
4114738 - maxtasksperchild=1... same issu fuck.  Now we're at 19.0G (1.3 down)
	now at 18.7
4114972, redoing the size=4, batches=8 thing... been running 11 min, which is disturbingly long, should have crashed by now with that threading error 
	with single processes, we took 45 min.  I am going have the speed as 1/4 but should kill .3GB in 45, so triple speed?  If i don't terminate 
	160 total in 20 size chunks exploiting 17 cores... so, slowest that's 
	10 iterations still, with a routine cleanup.
	Given 30 minutes, 3 minutes per iteration across 17 cores
		That still should be 3min/radar, not 12sec/radar linearly... 
	Hanging at 18.7 last i checked, would like to see 18.4, would still take 	2.5 days tho, really do need 3.8gB, or 18.3 / 18.35 reduction
	2hrs no progress, setting to run a bit less and update me

4117164 - updates user for debug and runs 6 batch in 6 cores
	that for loop with imap wouldnt work.  May change back to regular map
4117769 - use imap without iteration... what could be causing us to stall?  Is it child task limit? - confirmed.  Potential workarounds, but I'll see if using 6 cores helps first. I should at least hit an overflow after 5 minutes, which is better than a hangup. 
	frozen again.  
4117882 - more debug print - 60 cores hit overhill in about 5-6 minutes, delete their .3GB, but don't actually exit map to close 
4117964 - attempt to print worker returns and maxtasksperchild w/ sleep
4118402 - have unwrapper and getData yeild a return, hopefully that helps
	starts at 18.2GB - STUCK ON MAPPING AGAIN GODDAMN
Brute force time 


at worst its 5 hours of repeted termination and restart, pritting that overflow :/
18.2 ot 18.1
				
launch 3 at once from 15.3, seeking to break 15, ideally 14.4, which will give me some faster results at the expense of making people mad
only 15.2?  well yeah, they'd be deleting the same thing... But if i randomize the list... 
15.2 -> 14.7.  That IS indeed a higher rate of return.  Sample again to validate 
14.7-> 14.2 ... so we got .5 and .5 again, rather than .2 or .3, 2x speed.  Letts scale to 5! 
14.2->13.6, that's ... .6gB, i like
13.6->11.7 HOT FUCK THATS 1.9 GIGS 
lets retry that 
11.7->10.1 oh fuck that's... that's like 1.6GB that's flying 
10.1->8.6 =1.5GB.  will only need 6 more runs or so 
7.7, = .9GB, still progress lol 

several data cannot be opened, likely due to py-ART errror,4% of data
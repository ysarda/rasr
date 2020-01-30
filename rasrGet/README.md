rasrGet:
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


				
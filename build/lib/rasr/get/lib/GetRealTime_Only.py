# -*- coding: utf-8 -*-
"""
Created on Fri Jun 28 12:03:53 2019

@author: Ben
"""
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore",category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    import boto3

    from Unwrapper import runFunction as filterFile 
    import numpy as np
    import tempfile
    import matplotlib.colors as color
    import datetime
    import sys
    import os

def runFunction(site, cutoff, edgeFilter, areaFraction, colorIntensity, circRatio, fillFilt):    
    velMap,spwMap = getMaps()
    getData(site, velMap, spwMap, cutoff, edgeFilter, areaFraction, colorIntensity, circRatio, fillFilt)
    
def getData(site, velMap, spwMap, cutoff, edgeFilter, areaFraction, colorIntensity, circRatio, fillFilt):
    #https://www.nsstc.uah.edu/users/brian.freitag/AWS_Radar_with_Python.html
    #Set up Amazon AWS connections for client and environment
    s3conn = boto3.client(
        's3',
        aws_access_key_id= 'AKIAIF53QVV4DJHMYRXA',
        aws_secret_access_key='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'
    )
    os.environ["AWS_ACCESS_KEY_ID"] = "AKIAIF53QVV4DJHMYRXA"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "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"
    
    #use boto to connect to the immediate AWS nexrad bucket list for the current date
    now = datetime.datetime.utcnow()
    date = ("{:4d}".format(now.year) + '/' + "{:02d}".format(now.month) + '/' +
            "{:02d}".format(now.day) + '/'+str(site[0])+'/')
    
    #get the most recent data for the selected site (if site exists)
    objs = s3conn.list_objects_v2(Bucket='noaa-nexrad-level2',Prefix=date,Delimiter='/')
    if 'Contents' in objs:
        last_added=max(objs['Contents'],key=lambda x: x['LastModified'])
        #check that we dont use _MDM files 
        if not last_added['Key'].endswith("_MDM"):
            fname = last_added['Key']
            #print(fname)
        else:
            #safely terminate
            sys.exit()
    else:
        sys.exit()
        
    #Uncomment to control time of access for archived data
    #fname = '2009/02/15/KFWS/KFWS20090215_165332_V03.gz'

    #get file and store to temporary file for analysis (cannot direct load in current version)
    obj = boto3.resource('s3').Bucket('noaa-nexrad-level2').Object(fname)
    localfile = tempfile.NamedTemporaryFile(delete=False)
    with open(localfile.name,'wb') as data:
        obj.download_fileobj(data)
    filename = localfile.name
    printname = fname.split('/')[-1]
    printname = printname[0:19]
    
    #use the read_nexrad_archive function from PyART to read in NEXRAD file, then remove data
    #filterFile(filename, printname, velMap, spwMap, cutoff, edgeFilter, areaFraction, colorIntensity, circRatio, fillFilt)
    localfile.close()
    #os.remove(localfile.name)
    
def getMaps():
    #Set velocity colormap 
    cmaplist = np.array([[255,0,0],#-70
                         [255,0,0],#-60
                         [210,0,0],#-50
                         [180,0,0],#-40
                         [150,0,0],#-30
                         [115,0,0],#-20
                         [70,40,40],#-10
                         [70,70,70],#0
                         [40,70,40],#10
                         [0,115,0],#20
                         [0,150,0],#30
                         [0,180,0],#40
                         [0,210,0],#50
                         [0,255,0],#60
                         [0,255,0]])/255#70
    cmaplist = np.flip(cmaplist,axis=0)
    velMap = color.LinearSegmentedColormap.from_list('velMap',cmaplist,N=256)
    
    #Set spectrum width colormap
    cmaplist = np.array([[20,20,20],#0
                         [40,40,40],#6
                         [40,150,40],#12 40 150
                         [150,40,40],#18 150 40
                         [150,70,0],#24
                         [255,255,0]])/255#30
    spwMap = color.LinearSegmentedColormap.from_list('spwMap',cmaplist,N=256)
    return velMap, spwMap
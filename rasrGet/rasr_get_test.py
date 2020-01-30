# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 12:58:28 2019
ver 1.0 as of Feb 01, 2019

See README for details

@author: Benjamin Miller 
"""
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore",category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)
    import os
    import sys
    from multiprocessing import Pool, cpu_count 
    import boto3
    import datetime
    from functools import partial

def getData(site, keylist):
    #https://www.nsstc.uah.edu/users/brian.freitag/AWS_Radar_with_Python.html
    #Set up Amazon AWS connections for client and environment
    
    s3conn = boto3.client(
        's3',
        aws_access_key_id= str(keylist[0]),
        aws_secret_access_key=str(keylist[1])
    )
    #use boto to connect to the immediate AWS nexrad bucket list for the current date
    #now = datetime.datetime.utcnow()
    #date = ("{:4d}".format(now.year) + '/' + "{:02d}".format(now.month) + '/' +
    #        "{:02d}".format(now.day) + '/'+str(site)+'/')
    date = '2009/02/15/KFWS/'

    #get the most recent data for the selected site (if site exists)
    objs = s3conn.list_objects_v2(Bucket='noaa-nexrad-level2',Prefix=date,Delimiter='/')
    if 'Contents' in objs:
        last_added=max(objs['Contents'],key=lambda x: x['LastModified'])
        #check that we dont use _MDM files 
        if not last_added['Key'].endswith("_MDM"):
            #Get name
            fname = '2009/02/15/KFWS/KFWS20090215_165332_V03.gz'
            #fname = last_added['Key']
            printname = fname.split('/')[-1]
            printname = printname[0:19]
            localfile = os.getcwd()+"/tmp/"+printname
            #Confirm new file
            if not os.path.exists(localfile):
                #get file and store to temporary file for analysis (cannot direct load in current version)
                obj = boto3.resource('s3').Bucket('noaa-nexrad-level2').Object(fname)
                with open(localfile,'wb') as data:
                    obj.download_fileobj(data)    
                #localfile.close() is implicit with "with" structure
                #os.remove(localfile.name)

if __name__== '__main__':
    #optional spec for num pool workers, else num cpu
    if len(sys.argv)>1:
        runnum = sys.argv[1]
    else:
        runnum = cpu_count()
        
    sites = ['KCRP']
    #sites = ['KABR' ,'KENX','KABX','KAMA','PAHG','PGUA','KFFC','KBBX','PABC','KBLX','KBGM','PACG','KBMX','KBIS','KFCX','KCBX','KBOX',
#         'KBRO','KBUF','KCXX','RKSG','KFDX','KCBW','KICX','KGRK','KCLX','KRLX','KCYS','KLOT','KILN','KCLE','KCAE','KGWX',
#         'KCRP','KFTG','KDMX','KDTX','KDDC','KDOX','KDLH','KDYX','KEYX','KEPZ','KLRX','KBHX','KVWX','PAPD','KFSX','KSRX',
#         'KFDR','KHPX','KPOE','KEOX','KFWS','KAPX','KGGW','KGLD','KMVX','KGJX','KGRR','KTFX','KGRB','KGSP','KUEX','KHDX',
#         'KHGX','KHTX','KIND','KJKL','KDGX','KJAX','RODN','PHKM','KEAX','KBYX','PAKC','KMRX','RKJK','KARX','KLCH','KLGX',
#         'KESX','KDFX','KILX','KLZK','KVTX','KLVX','KLBB','KMQT','KMXX','KMAX','KMLB','KNQA','KAMX','PAIH','KMAF','KMKX',
#         'KMPX','KMBX','KMSX','KMOB','PHMO','KTYX','KVAX','KMHX','KOHX','KLIX','KOKX','PAEC','KLNX','KIWX','KEVX','KTLX',
#         'KOAX','KPAH','KPDT','KDIX','KIWA','KPBZ','KSFX','KGYX','KRTX','KPUX','KDVN','KRAX','KUDX','KRGX','KRIW','KJGX',
#         'KDAX','KMTX','KSJT','KEWX','KNKX','KMUX','KHNX','TJUA','KSOX','KATX','KSHV','KFSD','PHKI','PHWA','KOTX','KSGF',
#         'KLSX','KCCX','KLWX','KTLH','KTBW','KTWX','KEMX','KINX','KVNX','KVBX','KAKQ','KICT','KLTX','KYUX']

    
    #Create storage directory 
    dirname = os.getcwd()+"/tmp"
    if not os.path.exists(dirname):                 
        try:
                os.mkdir(dirname)
        except FileExistsError:
                pass
        
    with open("awskeys.txt","r") as keyfile:
        lines = keyfile.read().splitlines()
    #lines = file.readlines()
    keyfile.close()
    os.environ["AWS_ACCESS_KEY_ID"] = str(lines[0])
    os.environ["AWS_SECRET_ACCESS_KEY"] = str(lines[1])
    
    
    pool = Pool(processes=int(runnum)) #Pool(processes=#)
    getDataPart = partial(getData, keylist=lines)
    pool.map(getDataPart, sites)










#!/usr/bin/python
# querySafariDownloadsPlist.py
# look through safari browser download history to attempt to identify malware
# csv output in the current working directory
# output fields: 
# 	Path where files was downloaded to,
#	URL of the download,
#	Size of the download (not always accurate due to plist updating),
# 	Date of the download,
# 	Hash of the download (if it is still in the location it was downloaded to)	
#			 
# Last Edited: 7/30/18

### IMPORTS
import os
import glob
import time
import shutil
import hashlib
import plistlib
import subprocess

### VARIABLES
volPath = ''
userList = ''
resultsFile = 'Safari-Downloads-Plist-Contents.csv'

### FUNCTIONS
''' function to write results line by line '''
def write_to_file(filepath, contents):
	with open(filepath, 'a') as f:
		f.write(contents + os.linesep)
		
''' function to write list items to a file '''
def write_list(filepath, list):
	for i in range(len(list)):
		write_to_file(resultsFile, list[i])

''' take a sha256 hash of found files '''
def hash_file(filename):
	bufferSize = 65536
	sha256Hash = hashlib.sha256()
	with open(filename, 'rb') as f:
		while True:
			data = f.read(bufferSize)
			if not data: 
				break
			sha256Hash.update(data)
	hashResult = "{0}".format(sha256Hash.hexdigest())
	return(hashResult)
	
''' prompt for volume to query '''
def ask_volume():
	global userList
	global volPath
	subprocess.call(['diskutil', 'list'])
	prompt = raw_input('Query which volume? (ex. Macintosh HD)\n -> ')
	target = os.path.join('/Volumes', prompt)
	# check if passed in volume exists
	if os.path.exists(str(target)):
		volPath = target
		print('Querying ' + volPath)
		userList = glob.glob(volPath + '/Users/*')
	else:
		print('Invalid input.')
		exit()


''' Query the Downloads.plist for each user recorded by Safari '''
def query_safari(list):
	# initialize results list to store info strings
	results = []
	# check for each user
	for i in range(len(list)):
		fp = os.path.join(list[i], 'Library/Safari/Downloads.plist')
		userHome = list[i]
		if os.path.exists(fp):		
			# copy the plist to /tmp so we can convert it using plutil ->
			#<https://stackoverflow.com/questions/22211674/plistlib-cant-read-safaris-plist-file>
			shutil.copy(fp, '/tmp/dl.plist')
			
			# shell out to plutil
			subprocess.call(['plutil', '-convert', 'xml1', '/tmp/dl.plist'])
			time.sleep(2)
			
			# parse the plist
			pl = plistlib.readPlist('/tmp/dl.plist')
			all_dl_hist = pl['DownloadHistory']
			# each download generates a new dictionary with the top-most entry being the most recent
			for i in range(len(all_dl_hist)):
				dl_hist = pl['DownloadHistory'][i]
				''' 
				Query these keys
				DownloadEntryDateAddedKey (not using DownloadEntryDateFinishedKey because it may not have finished)
				DownloadEntryPath
				DownloadEntryProgressTotalToLoad
				DownloadEntryURL
				'''
				dl_date = dl_hist['DownloadEntryDateAddedKey']
				dl_path = dl_hist['DownloadEntryPath']
				dl_size = dl_hist['DownloadEntryProgressTotalToLoad']
				dl_url = dl_hist['DownloadEntryURL']
			
				# generate an actual path for the entry path
				check_path = ''
				s = dl_path.split("/")
				if s[0] == '~':
					s = s[1:]
					j = "/".join(s)
					check_path = os.path.join(userHome, j)
				else:
					check_path = dl_path
				
				# check if download is still at DownloadEntryPath
				if os.path.exists(check_path):
					# if it is, take the sha256 hash
					dl_hash = hash_file(check_path)
					resultString = str(dl_path + ',' + dl_url + ',' + str(dl_size) + ',' + str(dl_date) + ',' + dl_hash)
					# append the results to the result list
					results.append(resultString)
				else:
					resultString = str(dl_path + ',' + dl_url + ',' + str(dl_size) + ',' + str(dl_date) + ',')
					results.append(resultString)
			if os.path.exists('/tmp/dl.plist'):
				os.remove('/tmp/dl.plist')
		
		# write the results to an output file
		write_list(resultsFile, results)
	
			
### SCRIPT
ask_volume()
query_safari(userList)

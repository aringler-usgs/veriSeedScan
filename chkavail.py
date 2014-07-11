#!/usr/bin/env python

import glob
import os
import argparse

from obspy import UTCDateTime, read
from time import gmtime, strftime
from obspy.fdsn import Client
from obspy.neic import Client as ClientGCWB
from obspy.neic import Client as ClientPCWB
from multiprocessing import Pool

###################################################################################################
#chkavail.py
#
#This program checks the availability of data from various sources
#
#Methods
#args()
#checkAvail()
#nptsSum()
#
###################################################################################################

print 'Scan started on', strftime("%Y-%m-%d %H:%M:%S", gmtime()), 'UTC'

client = Client("IRIS")
chan = '*[BL]H*'



def args():
#This function parses the command line arguments
	parser = argparse.ArgumentParser(description='Code to compare data availability')

	parser.add_argument('-n', action = "store",dest="net", \
		default = "*", help="Network to check: NN", type = str, required = True)

	parser.add_argument('-s', action = "store",dest="sta", \
		default = "*", help="Station to check: SSSS", type = str, required = False)

	parser.add_argument('-y', action = "store",dest="year", \
		default = 2014, help="Year to check: YYYY", type = int, required = True)

	parser.add_argument('-sd', action = "store",dest="sday", \
		default = 1, help="Start day: DDD", type = int, required = True)

	parser.add_argument('-ed', action = "store",dest="eday", \
		default = 1, help="End day: DDD", type = int)

#Here is verbose mode
	parser.add_argument('-d','--debug',action = "store_true",dest="debug", \
		default = False, help="Run in debug mode")

#Here is the NEIC CWB
	parser.add_argument('-GCWB',action = "store_true",dest="gcwb", \
		default = False, help="Check the NEIC CWB (GCWB)")

#Here is the PCWB
	parser.add_argument('-PCWB',action = "store_true",dest="pcwb", \
		default = False, help="Check the NEIC internal CWB (PCWB)")

#Here is the ASL CWB
	parser.add_argument('-ASL',action = "store_true",dest="asl", \
		default = False, help="Check the ASL CWB (ASLCWB)")

#Here is the quality flag for Tyler
	parser.add_argument('-q',action = "store",dest = "quality", \
		default = "M", help = "Data quality type: D,Q,...")

	parserval = parser.parse_args()
	return parserval


def checkAvail(string):
#Here is the heart of the program where the availability gets checked

#Setup a path to decide if it is on /xs1 or /xs0	
	if net in set(["IU","IC","CU"]):
		netpath = "xs0"
	else:
		netpath = "xs1"

	allAvailString=[]

#Here we parse the function arguments
	string = string.split(",")
	year = int(string[0])
	jday = int(string[1])
	print 'On day ' + str(jday).zfill(3) + ' ' + str(year)

	startTime = UTCDateTime(str(year) + str(jday).zfill(3) + "T00:00:00.000")
	endTime = startTime + 24*60*60

#Setup the /tr1 string and glob it
	globString = '/tr1/telemetry_days/' + net + '_' + sta +'/' + str(year) + '/' + \
		str(year) + '_' + str(jday).zfill(3) + '/' + chan
	dataOnTr1 = glob.glob(globString)

	if len(dataOnTr1) == 0:
		#If there is no data on /tr1/ then it checks /xs0/ or /xs1/ accordingly
		if net in set(["IU","IC","CU"]):
			globString = '/xs0/seed/' + net + '_' + sta +'/' + str(year) + '/' + \
				str(year) + '_' + str(jday).zfill(3) + '_' + net + '_' + sta + '/' + chan
			dataOnTr1 = glob.glob(globString)
		else:
			globString = '/xs1/seed/' + net + '_' + sta +'/' + str(year) + '/' + \
				str(year) + '_' + str(jday).zfill(3) + '_' + net + '_' + sta + '/' + chan
			dataOnTr1 = glob.glob(globString)
	
	if debug:
		print(globString)
		print(dataOnTr1)


	for index, dataTrace in enumerate(dataOnTr1):
		#if True:
		try:
			if debug:
				#To visually separate the channel location scans from one another
				print '\n' + '*' * 80 + '\n' + '*' * 80
#tr1 availability
			if 'tr1' in dataTrace:
				trtr1 = read(dataTrace)
				if debug:
					nptsBefore = nptsSum(trtr1)
					print '\ntrTR1 points:', nptsBefore, '\n', trtr1
				availtr1 = 0
				for tr in trtr1:
					availtr1 += tr.stats.npts / (24*60*60*tr.stats.sampling_rate)
				if debug:
					print 'tr1 avialability:', str(availtr1 * 100) + '%'
			else:
				availtr1 = 0
		
#Here is the xs0 availability
			if 'tr1' in dataTrace:
				#If data exists on /tr1/, replace its dataTrace to now look at /xs0/
				trxs0 = dataTrace.replace('/tr1/telemetry_days','/' + netpath + '/seed')
				trxs0 = trxs0.replace(str(year) + '_' + str(jday).zfill(3), \
					str(year) + '_' + str(jday).zfill(3) + '_' + net + '_' + sta)
				trxs0 = read(trxs0)
			else:
				trxs0 = read(dataTrace)
			if debug:
				nptsBefore = nptsSum(trxs0)
				print '\ntrXS0 points:', nptsBefore, '\n', trxs0
			availxs0 = 0
			for tr in trxs0:
				availxs0 += tr.stats.npts / (24*60*60*tr.stats.sampling_rate)
			if debug:
				print netpath + ' avail: ' + str(availxs0*100) + '%'

#Here is the IRIS availability
			if availxs0 < 0.999 or availtr1 < 0.999:
				try:
					trIRIS = client.get_waveforms(net,trxs0[0].stats.station, \
						trxs0[0].stats.location, trxs0[0].stats.channel, \
						startTime,endTime,quality=qualval)
					if debug:
						nptsBefore = nptsSum(trIRIS)
						print '\ntrIRIS points:', nptsBefore, '\n', trIRIS
					availIRIS = 0
					for tr in trIRIS:
						availIRIS += tr.stats.npts / (24*60*60*tr.stats.sampling_rate)
				except:
					availIRIS = 0
				if debug:
					print 'IRIS availability: ' + str(availIRIS*100) + '%'


#Here we check the GCWB availability
				availIRIS = round(availIRIS,3)
				availxs0 = round(availxs0,3)
				availtr1 = round(availtr1,3)
				availString = trIRIS[0].stats.station + ',' + trIRIS[0].stats.location + \
							',' + trIRIS[0].stats.channel + ',' + str(year) + ',' + \
							str(jday).zfill(3) + ',' + str(availIRIS*100) + \
							','  + str(availxs0*100) + ',' + str(availtr1*100)


				if parserval.pcwb:
					try:
						trPCWB = clientPCWB.getWaveform(net,trxs0[0].stats.station, \
							trxs0[0].stats.location, trxs0[0].stats.channel, \
							startTime,endTime)
						if debug:
							nptsBefore = nptsSum(trPCWB)
							print '\ntrPCWB points:', nptsBefore, '\n', trPCWB
						availPCWB = 0
						for tr in trPCWB:
							availPCWB += tr.stats.npts / (24*60*60*tr.stats.sampling_rate)
						availPCWB = round(availPCWB,3)
					except:
						print 'Unable to access PCWB'
						availPCWB = 0
					if debug:
						print 'PCWB avialability:', availPCWB * 100
					if availIRIS != availxs0 or availIRIS != availtr1 or availPCWB != availtr1:
						availString += ',' + str(availPCWB*100)
						allAvailString.append(availString)
						print availString
				if parserval.gcwb and not parserval.asl:
					try:
						trGCWB = clientGCWB.getWaveform(net,trxs0[0].stats.station, \
							trxs0[0].stats.location, trxs0[0].stats.channel, \
							startTime,endTime)
						if debug:
							nptsBefore = nptsSum(trGCWB)
							print '\ntrGCWB points:', nptsBefore, '\n', trGCWB
						availGCWB = 0
						for tr in trGCWB:
							availGCWB += tr.stats.npts / (24*60*60*tr.stats.sampling_rate)
						availGCWB = round(availGCWB,3)
					except:
						availGCWB = 0
					if debug:
						print 'GCWB avialability:', availGCWB * 100
					if availIRIS != availxs0 or availIRIS != availtr1 or availGCWB != availtr1:
						availString += ',' + str(availGCWB*100) 
						allAvailString.append(availString)
						print availString
				elif parserval.asl and not parserval.gcwb:
					try:
						trASL = clientASL.getWaveform(net,trxs0[0].stats.station, \
							trxs0[0].stats.location, trxs0[0].stats.channel, \
							startTime,endTime)
						if debug:
							nptsBefore = nptsSum(trASL)
							print '\ntrASL points:', nptsBefore, '\n', trASL
						availASL = 0
						for tr in trASL:
							availASL += tr.stats.npts / (24*60*60*tr.stats.sampling_rate)
						availASL = round(availASL,3)
					except:
						availASL = 0
					if debug:
						print 'ASLCWB avialability:', availASL * 100
					if availIRIS != availxs0 or availIRIS != availtr1 or availASL != availtr1:
						availString += ',' + str(availASL*100) 
						allAvailString.append(availString)
						print availString

				elif parserval.asl and parserval.gcwb:
					trASL = clientASL.getWaveform(net,trxs0[0].stats.station, \
						trxs0[0].stats.location, trxs0[0].stats.channel, \
						startTime,endTime)
					if debug:
						nptsBefore = nptsSum(trASL)
						print '\ntrASL points:', nptsBefore, '\n', trASL
					availASL = 0
					for tr in trASL:
						availASL += tr.stats.npts / (24*60*60*tr.stats.sampling_rate)
					if debug:
						print 'ASLCWB avialability:', availASL * 100
					availASL = round(availASL,3)
					
					trGCWB = clientGCWB.getWaveform(net,trxs0[0].stats.station, \
						trxs0[0].stats.location, trxs0[0].stats.channel, \
						startTime,endTime)
					if debug:
						nptsBefore = nptsSum(trGCWB)
						print '\ntrGCWB points:', nptsBefore, '\n', trGCWB
					availGCWB = 0
					for tr in trGCWB:
						availGCWB += tr.stats.npts / (24*60*60*tr.stats.sampling_rate)
					if debug:
						print 'GCWB avialability:', availGCWB * 100
					availGCWB = round(availGCWB,3)
					
					if availIRIS != availxs0 or availIRIS != availtr1 or availGCWB != availtr1 or availASL != availtr1:
						availString += ',' + str(availGCWB*100) + ',' + str(availASL*100)
						allAvailString.append(availString)
						print availString




				else:
					if availIRIS != availxs0 or availIRIS != availtr1:
						allAvailString.append(availString)
						print availString

		except:
			print 'Problem with: ' + dataTrace
	f = open("avail" + str(year) + net + '.csv',"a")
	for curavail in allAvailString:
		print 'Writing to file'
		f.write(curavail + "\n")
	f.close()
	
	return

def nptsSum(traces):
	npts = 0
	for index in range(len(traces)):
		npts += traces[index].stats.npts
	return npts




#Here are the parser value arguments
#We make the global to get them in the function
parserval = args()
net = parserval.net
year = parserval.year
sta = parserval.sta
debug = parserval.debug
sday = parserval.sday
if parserval.eday != 1:
	#If eday flag was parsed, set eday
	eday = parserval.eday
else:
	#If eday has default value, set eday equal to sday
	#This allows for one-day scans
	eday = sday
qualval = parserval.quality
if parserval.gcwb:
	print 'GCWB selected', parserval.gcwb
	clientGCWB = ClientGCWB()

if parserval.asl:
	print 'ASLCWB selected', parserval.asl
	clientASL = ClientGCWB(host='136.177.121.27')

if parserval.pcwb:
	print 'PCWB selected', parserval.pcwb
	clientPCWB = ClientGCWB(host='136.177.24.70')


#Lets write the header to the csv file
if os.path.isfile("avail" + str(year) + net):
	os.remove("avail" + str(year) + net)

f = open("avail" + str(year) + net + '.csv',"w")
header = "Sta,Loc,Chan,Year,Day,IRIS,xs,tr1"
if parserval.pcwb:
	header += ",PCWB"
if parserval.gcwb:
	header += ",GCWB"
if parserval.asl:
	header += ",ASLCWB"
header += '\n'
f.write(header)
f.close()

#Here we loop over the days
sendToavail=[]
for day in xrange(sday, eday + 1, 1):
	sendToavail.append(str(year) + "," + str(day).zfill(3))

#Hwere we run everything as a multi-process
pool = Pool()
pool.map(checkAvail,sendToavail)

print 'Scan ended on', strftime("%Y-%m-%d %H:%M:%S", gmtime()), 'UTC'
"""
parses the SensorReadings from dexecom7 sensor export
designed to run in the iPython Terminal
%run process.py
requires lxml
requires pandas ( scipy )
"""

from lxml import etree
import json
import datetime, math
from CoreUtils import Utils

def getTree(path):
	tree = etree.parse(path)
	root = tree.getroot()
	sr = root.find("SensorReadings")
	return sr

def prettyPrint(sr):
	for s in sr:
    		print s.tag

def _(key,node):
	return node.get(key)

def parseDate(passedDate):
	'''parse year, month, day, 24hr, min, sec '''
	dBits = passedDate.split()
	yearBits = dBits[0]

	yBits = yearBits.split('-')

	YY = int(yBits[0])
	MM = int(yBits[1])
	DD = int(yBits[2])

	timeBits = dBits[1]
	tBits = timeBits.split(':')
	HH = int(tBits[0])
	mm = int(tBits[1])

	pBits = tBits[2].split('.')
	ss = int(pBits[0])
	ms = int(pBits[1])

	dObj = datetime.datetime( YY,MM,DD,HH,mm,ss,ms)

	return dObj
	
def mmlToMgDl(i):
	''' convert mmol/l to mg/dl '''
	K = 18.0182
	#http://bit.ly/jIaF8g
	i = float(i)
	return int(math.floor( i * K))


def dexComm7_2csv(nodelist):
	'''dexComm7 xml form of the sensor readings to csv '''	
	csvLine = []
	items = []
	
	headerList = ['localDateTime','offsetGMT','timezoneDesc','year','weekOfYear','dayOfWeek','hourOfDay','value','units','eventType','owner']
	items.append( headerList )
	headerLine = ", ".join(headerList)
	csvLine.append( headerLine)

	for node in nodelist:
		dt = _("DisplayTime",node)
		tmpDt = parseDate(dt)
		isocal = tmpDt.isocalendar() #(Year,WeekOfYear,DayOfWeek)
		mv = float(_("Value",node))
		mgdl = mmlToMgDl( mv )

		csvLine.append( "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10}".format( 
			dt,"-0400","(Eastern Standard Time)",isocal[0],isocal[1],isocal[2],tmpDt.hour,mgdl,"mg_dl","glucose-sensor","GS001"
			))

		itemList = [dt,"-0400","(Eastern Standard Time)",isocal[0],isocal[1],isocal[2],tmpDt.hour,mgdl,"mg_dl","glucose-sensor","GS001"]
		items.append(itemList)
	
	return csvLine, items


def prepForPanda(items):
	''' and for d3! '''
	headerLine = items[0]
	hold = []
	data = {}

	d3 = []

	#prepare holder list of lists
	for header in headerLine:
		hold.append([])

	#procedurally transform the lists
	#is there a list comprehension way to do this?
	itemIndex = 0
	for item in items:
		itemIndex = itemIndex + 1

		if( itemIndex == 1): continue #ignore header line

		subItemIndex = 0
		tmpD3 = {}
		for subItem in item:
			hold[subItemIndex].append( subItem )
			
			idx = headerLine[subItemIndex]
			tmpD3[idx]  = subItem
			subItemIndex = subItemIndex + 1

		d3.append(tmpD3)
		
			
	#add to data dictionary
	headerIndex = 0
	for header in headerLine:
		data[header] = hold[headerIndex]
		headerIndex = headerIndex + 1

	# could also return hold ( lists prepped )
	return data, d3



def getDataFrame(inputXML = "./cgm.xml"):
	'''returns a dataframe'''
	a,itemz = outCsv( inputXML)
	data = prepForPanda(itemz)
	from pandas import DataFrame
	df = DataFrame( data )
	return df


def uploadCouch(numRecords = 8,
	inputXML = "./cgm.xml",
	couchHost = "www.agentidea.com:5984"):
	''' via python Command, http / json interface '''
	a,itemz = outCsv( inputXML)
	sub = itemz[0:numRecords]
	data, d3data = prepForPanda(sub)

	for elem in d3data:

		tmpJSON = json.dumps( elem )
		tmpJSON = Utils().pack( tmpJSON)

		url = '''http://www.agentidea.com'''

		path = '''/rest?command=AddJSON&destinationTable=timedata_grantsteinfeld'''
		path += '''&json64='''
		path += tmpJSON
		path += '''&kreds=YWRtaW5fOGMzMTlmMjhkODFkMTUyN2E5NDI4ZTlhNWMyMTk1ZjU%3D'''


		import urllib
		response = urllib.urlopen( url + path)
		print response


def uploadCouchLocal(numRecords = 8,
	destinationDB = 'gs001_timedata',
	inputXML = "./cgm.xml",
	couchHost = "localhost:5984"):
	
	'''a post to couchHost via http directly ... '''

	a,itemz = outCsv( inputXML)
	sub = itemz[0:numRecords]
	print sub
	data, d3data = prepForPanda(sub)

	import httplib
	url = 'localhost'
	port = 5984
	path = '/{0}/'.format(destinationDB)

	
 	headers = {"Content-Type": "application/json"}

 	uri = "http://rhada:pup@{0}:{1}{2}".format( url, port,path)
 	print uri
	for elem in d3data:
		print elem
		try:
			j = json.dumps( elem)
			c = httplib.HTTPConnection(url, port) 
			c.request('POST', uri, j	, headers)
			#c.getresponse()
			c.close()
		except:
			print "err:"





def saveD3json(numRecords = 8,inputXML = "./cgm.xml",outputJSON = './d3.json'):
	a,itemz = outCsv( inputXML)
	sub = itemz[0:numRecords]
	data, d3data = prepForPanda(sub)
	jsonRez = json.dumps( d3data )
	with open(outputJSON,'w+') as f:
		f.write( jsonRez )
		
	print "saved JSON for D3"	
	

def convertXML2CSV(outputCSV = './default.csv',inputXML = "./cgm.xml"):
	a,b = outCsv( inputXML)

	saveCsv(a , outputCSV)

def outCsv(inputXML = "./cgm.xml"):
	tree = getTree(inputXML)
	return dexComm7_2csv(tree)

def saveCsv(csvLines,pathToWrite = './default.csv'):
	counter = 0
	with open(pathToWrite,'w+') as f:
		for line in csvLines:
			f.write( "{0},\r\n".format(str( line )))
			counter = counter + 1

	print "wrote {0} results to file {1}".format( counter, pathToWrite)




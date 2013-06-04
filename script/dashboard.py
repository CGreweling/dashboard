#!/usr/bin/python

import os, sys, glob
import datetime
import subprocess
import ConfigParser
import urllib, urllib2, cookielib
import json
import codecs
import argparse

#TODO
# 1. Calendar
# 2. NCast
# 3. Agents devices

class MatterhornClient:
	def __init__(self, url, username, passwd):
		self.server_url = url
		self.username = username
		self.passwd=passwd
		self.contents = ''

	def getAgentOnline(self, agentName):
		
		cj = cookielib.CookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
		login_data = urllib.urlencode({'j_username' : self.username, 'j_password' : self.passwd})
		resp = opener.open(self.server_url + '/j_spring_security_check', login_data)
		
		resp = opener.open(self.server_url + '/capture-admin/agents/' + agentName + '.xml')
		
		return (resp.code == 200)


	def getAgentsInfo(self):
		
		cj = cookielib.CookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
		login_data = urllib.urlencode({'j_username' : self.username, 'j_password' : self.passwd})
		resp = opener.open(self.server_url + '/j_spring_security_check', login_data)

		resp = opener.open(self.server_url + '/capture-admin/agents.json')
		
		return (resp.code, resp.read())
		
	# TODO test 
	# von heute 7 Tage
	# xml fuer alle holen http://mh-admin.virtuos.uos.de:8080/capture-admin/recordings
	# parsen und filtern
	def getCalendar(self, date_from, date_to):
		
		cj = cookielib.CookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
		login_data = urllib.urlencode({'j_username' : self.username, 'j_password' : self.passwd})
		resp = opener.open(self.server_url + '/j_spring_security_check', login_data)
		
		d_from = "%04d-%02d-%02dT00:00:00Z" % (date_from.year, date_from.month, date_from.day)
		d_to = "%04d-%02d-%02dT00:00:00Z" % (date_to.year, date_to.month, date_to.day)
		

		resp = opener.open(self.server_url + "/recordings/recordings.json?sort=CREATED&startsfrom="+d_from+"&endsto="+d_to)	
		
		return (resp.code, resp.read())
		




def md5_for_file(filename):
	try:
		md5 = hashlib.md5()
		with open(filename,'rb') as f: 
			for chunk in iter(lambda: f.read(8192), b''): 
				md5.update(chunk)
		ret = md5.hexdigest()
	except:
		ret = ""
	return ret

def write_file(filename, str):
	fout = codecs.open(filename,"w", "utf-8-sig")
	fout.write(str)
	fout.close()

#TODO
def getAgentDevices(ip, agent_username, agent_passwd):
	
	#cj = cookielib.CookieJar()
	#opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	#login_data = urllib.urlencode({'j_username' : agent_username, 'j_password' : agent_passwd})
	#resp = opener.open(ip + '/j_spring_security_check', login_data)
	
	#resp = opener.open(ip + "/confidence/devices")
	
	#print resp.read()
	
	return ("vga", "dozent")

def generateAgentScreenShoot(ip, agent_username, agent_passwd, snapshotFolder, agentSection, devices):
	
	for device in devices:
		
		img = snapshotFolder + agentSection + device
		outimg = img + ".jpg"

		cj = cookielib.CookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
		login_data = urllib.urlencode({'j_username' : agent_username, 'j_password' : agent_passwd})
		resp = opener.open(ip + '/j_spring_security_check', login_data)

		resp = opener.open(ip + "/confidence/" + device)

		f = open(outimg, 'w')
		f.write(resp.read())
		f.close()
		resp.close() 

	return 1

def getMatterHornInfo(MHAgentsInfo, agentName):
	for a in MHAgentsInfo:
		if (a["name"] == agentName):		
			return a	
	return {}


def getMatterHornAgentsInfo(config):
	MH_server = config.get("dashboard-config", "MHServer")
	MH_user = config.get("dashboard-config", "MHuser")
	MH_passwd = config.get("dashboard-config", "MHPassword")
	
	MH = MatterhornClient(MH_server, MH_user, MH_passwd)
	info = MH.getAgentsInfo()
	if info[0] != 200:
		return []
	else:		
		jj = json.loads(info[1])
		return jj["agents"]["agent"]

# TODO
def getMatterHornCalendarInfo(config):
	MH_server = config.get("dashboard-config", "MHServer")
	MH_user = config.get("dashboard-config", "MHuser")
	MH_passwd = config.get("dashboard-config", "MHPassword")
	
	MH = MatterhornClient(MH_server, MH_user, MH_passwd)
	calendar = MH.getCalendar(datetime.datetime.utcnow().date(), datetime.datetime.utcnow().date()+datetime.timedelta(days=7))
	ret = {}
	if calendar[0] == 200:
		catalogs =  json.loads(calendar[1])
		for c in catalogs["catalogs"]:
			try:
				agent = c["http://purl.org/dc/terms/"]["spatial"][0]["value"]
				title = c["http://purl.org/dc/terms/"]["title"][0]["value"]
				spatial = c["http://purl.org/dc/terms/"]["temporal"][0]["value"]
				ss = spatial.split(";")
				start=ss[0].split("=")[1]
				end=ss[1].split("=")[1]
				if (ret.has_key(agent) == False):
					ret[agent] = []
				ret[agent].append({"title":title, "start":start, "end":end})
			except:
				pass
			
	return ret

def getJSONitems(config, agentSection):
	json_items = ""
	try:
		items = config.items(agentSection)
	except:
		items = {}
	for k,v in items:
		uv = v.decode("utf8","ignore")
		uk = k.decode("utf8","ignore")
		json_items += "\"" + uk + "\": \"" + uv + "\",\t"
	return json_items[:-2]


#TODO
def generateAgentJSON(config, MHAgentsInfo, MHCalendarInfo, agentSection):
	MHinfo = getMatterHornInfo(MHAgentsInfo, agentSection)
	agent_url = getConfigOption(config, agentSection, "url")
	
	if (agent_url == None):
		try:
			agent_url = MHinfo["url"]
		except:
			pass
		
	snapshotFolder = getConfigOption(config, "dashboard-config", "snapShotFolder")	

	agent_state = MHinfo["state"]
	MH_server = config.get("dashboard-config", "MHServer")
	MH_user = config.get("dashboard-config", "MHuser")
	MH_passwd = config.get("dashboard-config", "MHPassword")
	
	MH = MatterhornClient(MH_server, MH_user, MH_passwd)
	agent_online = MH.getAgentOnline(agentSection)

	filenameshot = ""
	
	images = {}

	if (agent_online):	
		if (agent_state == "capturing"):
			devices = getAgentDevices(agent_url, MH_user, MH_passwd) 
			generateAgentScreenShoot(agent_url, MH_user, MH_passwd, snapshotFolder, agentSection, devices)
			
			for device in devices:
				images[device]= agentSection+device+".jpg"
			
		MHinfo = getMatterHornInfo(MHAgentsInfo, agentSection)	
	else:
		MHinfo = {}
				
	json_items = getJSONitems(config, agentSection)	
	

#TODO calendar
	calendar = []
	#if MHCalendarInfo.has_key(agentSection):
	#	calendar = MHCalendarInfo[agentSection]
	
	line_str = "{ "
	line_str += "\"agentname\": \"" + agentSection +"\",\t"
	line_str += "\"agenturl\": \"" + agent_url +"\",\t"
	line_str += "\"online\": \"" + str(agent_online) +"\",\t"
	line_str += "\"images\": " + json.dumps(images) + ",\t"
	line_str += "\"enrich\": {" + json_items + "},\t" 
	line_str += "\"mhinfo\": " + json.dumps(MHinfo) + ", \t"
	line_str += "\"calendar\": " + json.dumps(calendar) + " \t"
	line_str += " }"
		
	return line_str

def getAgentsNames(config, MHAgentsInfo):
	agents = {}
	for a in MHAgentsInfo:
		name = str(a["name"])
		agents[name]=name		
	
	sections = config.sections()
	sections.remove("dashboard-config")
	sections.remove("ncast-boxes")
	for s in sections:
		if (agents.has_key(s)==False):
			agents[s]=s
	ret = agents.keys()
	
	try:
		ret.remove("demo_capture_agent")
	except:
		pass
	ret.sort()		
	return ret


def generateAllAgentsJSON(config, datetime_str):
	MHAgentsInfo = getMatterHornAgentsInfo(config)
	MHCalendarInfo = 0#getMatterHornCalendarInfo(config)
	agentNames = getAgentsNames(config, MHAgentsInfo)	
	
	json_agents=""
	for a in agentNames:
		a_out = generateAgentJSON(config, MHAgentsInfo, MHCalendarInfo, a)
		json_agents += "\t"+a_out +",\n"
	json_agents = json_agents[:-2]
	
	ncast_agents = generateAllNCastBoxesJSON(config)
	
	json="{\n"
	json+="\"datetime\": \""+datetime_str+"\",\n"
	json+="\"agents\": [\n"
	json+= json_agents + "\n"
	json+= "],\n"
	json+="\"ncast_agents\": [\n"
	json+= ncast_agents + "\n"
	json+="]}\n"

	return json

##################### NCast Boxes Begin ####################################

def generateAllNCastBoxesJSON(config):
	
	agents = config.items("ncast-boxes")

	json_agents=""
	for agent in agents:
		a_out = generateNCastBoxJson(config, agent[0], agent[1])
		json_agents += "\t"+a_out +",\n"
	json_agents = json_agents[:-2]

	return json_agents

def generateNCastBoxJson(config, agent_name, agent_url):
	snapshotFolder = getConfigOption(config, "dashboard-config", "snapShotFolder")	

	user = config.get("dashboard-config", "MHuser")
	passwd = config.get("dashboard-config", "MHPassword")
	
	#TODO read state, online from info ?	
	ncast_info = getNCastBoxInfo(agent_url, user, passwd)

	agent_state = "capturing"
	agent_online = 1

	if (agent_online):	
		if (agent_state == "capturing"):
			generateNCastBoxScreenShoot(agent_url, user, passwd, snapshotFolder, agent_name)
			image = agent_name+".jpg"
			
		
	line_str = "{ "
	line_str += "\"agentname\": \"" + agent_name +"\",\t"
	line_str += "\"agenturl\": \"" + agent_url +"\",\t"
	line_str += "\"online\": \"" + str(agent_online) +"\",\t"
	line_str += "\"ncastinfo\": " + ncast_info + ", \t"
	line_str += "\"image\":  \"" + image + "\"\t"
	line_str += " }"
		
	return line_str

def generateNCastBoxScreenShoot(agent_url, user, passwd, snapshotFolder, agent_name):

	img = snapshotFolder + agent_name
	outimg = img + ".jpg"

	authhandler = urllib2.HTTPDigestAuthHandler()
	authhandler.add_password("Presentation Recorder", agent_url, user, passwd)
	opener = urllib2.build_opener(authhandler)
	
	resp = opener.open(agent_url + "/rest/files/preview.jpg")
	
	f = open(outimg, 'w')
	f.write(resp.read())
	f.close()
	resp.close() 

	return 1


def getNCastBoxInfo(agent_url, user, passwd):

	authhandler = urllib2.HTTPDigestAuthHandler()
	authhandler.add_password("Presentation Recorder", agent_url, user, passwd)
	opener = urllib2.build_opener(authhandler)
	
	resp = opener.open(agent_url + "/rest/status/status")
	info = resp.read()
	resp.close() 
	
	return info


##################### NCast Boxes End   ####################################


def readAgentsConfig(config, configAgentsFolder):	
	for r,d,f in os.walk(configAgentsFolder):		
		for files in f:
			if files.endswith(".conf"):
				fileconf = os.path.join(r,files)				
				config.read(fileconf)

def getConfigOption(config, section, option):
	try:
		ret = config.get(section, option)	
	except ConfigParser.NoOptionError:
		ret = None
	except ConfigParser.NoSectionError:
		ret = None
		
	return ret;


def process(conf_file):	
	config = ConfigParser.RawConfigParser()
	config.read(conf_file)
	snapshotFolder = getConfigOption(config, "dashboard-config", "snapShotFolder")	
	outputJSONFile = getConfigOption(config, "dashboard-config", "outputJSONFile")
	configAgentsFolder = getConfigOption(config, "dashboard-config", "configAgentsFolder")

	if (snapshotFolder == None):
		print "Error: snapShotFolder not defined in config file!"
		sys.exit(1)
	if (outputJSONFile == None):
		print "Error: outputJSONFile not defined in config file!"
		sys.exit(1)
	if (configAgentsFolder != None):
		readAgentsConfig(config, configAgentsFolder)
		
	utcnow = datetime.datetime.utcnow()
	datetime_str = "%04d-%02d-%02dT%02d:%02d:%02dZ" % (utcnow.year, utcnow.month, utcnow.day, utcnow.hour, utcnow.minute, utcnow.second)
	sys.stdout.write("Writting JSON file (" + datetime_str + ")... ")
	sys.stdout.flush()
	json = generateAllAgentsJSON(config, datetime_str)		
	write_file(outputJSONFile, json)
	print "Done."
	
	
def main():
	parser = argparse.ArgumentParser(
		description='Generates the necessary files for MH-DashBoard.')
		
	parser.add_argument('-c', '--config-file', dest='config_file',
		action='store', default="/etc/mh-dashboard/dashboard.conf", 
		help='confgiguration file')
		
	args = parser.parse_args()
	if (os.path.isfile(args.config_file) == True):
		process(args.config_file)
	else:		
		print parser.format_help()
		exit(1)

if __name__ == "__main__":
	main()


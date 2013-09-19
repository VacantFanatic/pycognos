#Aran Gillmore 03/2013
#!/usr/bin/env python
#required packages requests, requests-ntlm, python-ntlm
import xml.etree.ElementTree as etree
import sys, os, getopt, requests, io, argparse, re
from datetime import datetime
from requests_ntlm import HttpNtlmAuth
from bs4 import BeautifulSoup
 
class Authentication:
   
    def __init__(self, root):
        self.domain = root.find('{manifest}config').find('{manifest}domain').text
        self.UID = root.find('{manifest}config').find('{manifest}user').text
        self.password = root.find('{manifest}config').find('{manifest}password').text
        self.server = root.find('{manifest}config').find('{manifest}server').text
        self.namespace = root.find('{manifest}config').find('{manifest}namespace').text
        self.cogdir = root.find('{manifest}config').find('{manifest}cogdir').text
        return
   
    def setUser(self, user):
        self.UID = user
        return
   
    def setPassword(self, password):
        self.password = password
        return
   
    def setDomain(self, domain):
        self.domain = domain
        return
   
    def setServer(self, server):
        self.server = server
        return
   
    def setNamespace(self, namespace):
        self.namespace = namespace
        return
   
    def getCogDir(self):
        return self.cogdir
   
    def getUser(self):
        return self.UID
   
    def getPassword(self):
        return self.password
   
    def getDomain(self):
        return self.domain
   
    def getServer(self):
        return self.server
   
    def getNamespace(self):
        return self.namespace
   
class Prompt:
   
    def __init__(self, name, value, display):
        self.name = name
        self.value = value
        self.display = display
        return
   
    def getName(self):
        return self.name
   
    def getValue(self):
        return self.value
   
    def getDisplay(self):
        return self.display

class TestCase:
   
    def __init__(self, name, caseID, searchP):
        self.name = name
        self.id = caseID
        self.searchPath = searchP
        self.params = {}
        return
   
    def setPrompt(self, paramName, paramVal):
        self.params[paramName] = paramVal
        return
   
    def setDesc(self, desc):
        self.description = desc
        return
   
    def getID(self):
        return self.id
   
    def getName(self):
        return self.name
   
    def getReportPath(self):
        return self.searchPath
   
    def getPrompt(self, pName):
        return self.params[pName]
   
    def getAllPrompts(self):
        return self.params
   
class Cases:
   
    def __init__(self, p1):
        self.cases = {}
        self.readCases(p1)
        return
   
    def readCases(self, root):
        for case in root[1].findall('{manifest}test'):
            ident = case.get('id')
            name = case.find('{manifest}testname').text
            if case.find('{manifest}testdescription') == None:
                desc = "None"
            else:
                desc = case.find('{manifest}testdescription').text
            spath = case.find('{manifest}searchPath').text
            c = TestCase(name, ident, spath)
            c.setDesc(desc)
            for param in case.findall('{manifest}prompts'):
                for prompt in param.findall('{manifest}prompt'):
                    name = prompt.find('{manifest}name').text
                    value = prompt.find('{manifest}value').text
                    display = prompt.find('{manifest}displayValue').text
                    p = Prompt(name, value, display)
                    c.setPrompt(name, p)
            self.cases[c.getID()] = c
        return
   
    def getCase(self, key):
        return self.cases[key]
   
    def getAllCases(self):
        return self.cases

class CmsNetwork:
    def __init__(self, auth, tcs):
        self.auth = auth
        self.cases = tcs
        self.authURL = "http://"+auth.getServer()+"/"+auth.getCogDir()+"/cgi-bin/cognos.cgi/rds/auth/logon"
        self.logOffURL = "http://"+auth.getServer()+"/"+auth.getCogDir()+"/cgi-bin/cognos.cgi/rds/auth/logoff"
        self.s = requests.Session()
        self.s.stream = False
        #self.s.headers = {'Content-Type': 'text/html'}
        self.creds = {}
        self.dt = datetime.now()
        self.outfolder = self.dt.strftime("%m%d%y%H%M%S")
        if os.path.isdir("H:/cogtests/"):
            pass
        else:
            os.makedirs("H:/cogtests/")
        os.makedirs("H:/cogtests/"+ self.outfolder)
        sys.stdout = open("H:/cogtests/"+ self.outfolder+".log", 'w')
        sys.stderr = open("H:/cogtests/cog_error.log", 'a')
        sys.stderr.write('\n---'+self.dt.strftime("%m/%d/%y %H:%M:%S")+"---\n\n")
        return
   
    def setAuth(self):
        xmlCreds = "<credentials><credentialElements><name>CAMNamespace</name><label>Namespace:</label><value><actualValue>"+auth.getNamespace()+"</actualValue></value></credentialElements><credentialElements><name>CAMUsername</name><label>User ID:</label><value><actualValue>"+auth.getUser()+"</actualValue></value></credentialElements><credentialElements><name>CAMPassword</name><label>Password:</label><value><actualValue>"+auth.getPassword()+"</actualValue></value></credentialElements></credentials>"
        self.creds['xmlData'] = xmlCreds
        return
   
    def logOn(self):
        self.usr = auth.getDomain()+'\\'+auth.getUser()
        self.s.auth = HttpNtlmAuth(self.usr, auth.getPassword())
        r1 = self.s.post(self.authURL, data = self.creds)
        sc =  r1.status_code
        if sc == 401:
            print 'Invalid log on credentials. Please review the credentials provided in the manifest file.'
            sys.exit('Invalid log on credentials.')
        elif sc == 403:
            print 'Not Authorized. Please review the credentials provided in the manifest file.'
            sys.exit('Not authorized.')
        elif sc == 404:
            print 'Page not found. Please modify the server values in your manifest.'
            sys.exit('Page not found')
        elif sc == 400:
            print 'Bad request.'
            sys.exit('Bad request.')
        else:
            return r1
   
    def logOff(self):
        r2 = self.s.get(self.logOffURL)
        return r2
   
    def callCMS(self, case):
        "This function calls the Mash-up Service via the REST API"
        xmlData = ""
        payload = {'async':'OFF', 'fmt':'html'}
        reportURL = "http://"+auth.getServer()+"/"+auth.getCogDir()+"/cgi-bin/cognos.cgi/rds/reportData/searchPath/"+case.getReportPath()
        if case.getAllPrompts():
            xmlData = "xmlData=<promptAnswers><promptValues>"
            for key in case.getAllPrompts():
                name = key
                value = case.getPrompt(key).getValue()
                display = case.getPrompt(key).getDisplay()
                xmlData = xmlData + "<name>"+key+"</name><values><item><SimplePValue><inclusive>true</inclusive><useValue>"+value+"</useValue><displayValue>"+display+"</displayValue></SimplePValue></item></values>"
            xmlData = xmlData + "</promptValues></promptAnswers>"
        if xmlData:
            r = self.s.post(reportURL, data = xmlData, params=payload)
            path = self.renderResults(r, case.getID())
        else:
            r = self.s.get(reportURL, params=payload)
            path = self.renderResults(r, case.getID())
        hp = HtmlParser(r)
        result = hp.isSuccess()
        print "Test case: "+case.getID()+" "+ result
        if result == 'Passed':
            images = hp.findImgs(path)
            for img in images:
                r2 = self.s.get(images[img])
                path = "H:/cogtests/"+self.outfolder+"/"+case.getID()+"_"+img+".png"
                outfile = open(path,'wb')
                outfile.write(r2.content)
                outfile.close()
        return
   
    def runTests(self):
        self.setAuth()
        self.logOn()
        for key in self.cases.getAllCases():
            self.callCMS(self.cases.getCase(key))
        print "Done tests!"
        sys.stderr.write('No errors encountered.\n')
        return
    def renderResults(self, response, out):
        path = "H:/cogtests/"+self.outfolder+"/"+out+".html"
        outfile = open(path,'wb')
        outfile.write(response.text)
        outfile.close()
        return path

class HtmlParser:
   
    def __init__(self, response):
        self.r = response
        self.images = {}
        return
   
    def findImgs(self, path):
        soup = BeautifulSoup(open(path))
        for img in soup.find_all('img'):
            #print img
            imgid = img['id']
            imgsrc = img['src']
            #print imgsrc
            self.images[imgid] = imgsrc
        return self.images
   
    def isSuccess(self):
        p = re.compile('<rds:error.*')
        m = p.match( self.r.text)
        if m:
           return 'Failed'
        else:
            return 'Passed'

#start main script

#-------------parse command line args--------------------------------
parser = argparse.ArgumentParser(description= "Execute Cognos test cases contained in an XML manifest file")
parser.add_argument("manifest_file", nargs='?', default = 'h:/manifest.xml', help = "Path to the XML manifest of test cases")
args = parser.parse_args()

#-------------parse XML manifest file-------------------------------
tree = etree.parse(args.manifest_file)
root = tree.getroot()
auth = Authentication(root)
tcs = Cases(root)

#------------execute test cases-------------------------------------
cms = CmsNetwork(auth, tcs)
cms.runTests()

#------------clean up------------------------------------------------
cms.logOff()

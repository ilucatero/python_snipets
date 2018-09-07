#!/usr/bin/python

import glob, os, time, difflib, smtplib
from datetime import datetime,date,timedelta
from bs4 import BeautifulSoup
from shutil import copyfile
from email.mime.text import MIMEText

baseDir = '/opt/client/'
baseDirKO = baseDir + 'ko/'

#GLOBAL VARS
report = ""

#print file date
def PrintFilesStat(file):
    print(time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(file))), file)

#print all file date in the passed array
def PrintFiles(files):
    for file in files:
        PrintFilesStat(file)

#load in a list all the files found in the Old Application Directory
def loadOldAppFiles():
    oldAppFilesDir = "/mnt/templates/"
    oldAppFiles = glob.glob(oldAppFilesDir + "temp1/data/xml/*.html") 
    oldAppFiles = oldAppFiles + glob.glob(oldAppFilesDir + "temp2/data/xml/*.html")
    oldAppFiles = oldAppFiles + glob.glob(oldAppFilesDir + "temp3/data/xml/*.html")
    oldAppFiles.sort(key=lambda file: os.path.getmtime(file))
    return oldAppFiles

#load last time in seconds when this application was launched
def getLastLaunchingFile():
    with open(baseDir+'lastlaunch.date', "r") as dateFile:  
        line = dateFile.readline()
    if not line:
        print('USING TIME:' + line + ', AND WRITING TIME : ' + str(time.time()))
        return line
    else:
        print('NO DATE FOUND, USING : ' + str(time.time()) )
        return  float((datetime.now() - timedelta(hours=1)).strftime("%s"))

#set the last time in seconds (time() obj passed in parameter) when this application was launched
def updateLastLaunchingFile(time):
    with open(baseDir+'lastlaunch.date', "w") as dateFile:  
        dateFile.write(str(time))

#remove files where date is before last launched time
def FilterFiles(files, lastDate):
    newArray = []
    for file in files:
        #if file is older than last time it run
        if float(lastDate) < os.path.getmtime(file):
            #PrintFilesStat(file)
            newArray = newArray + [file]
    return newArray

# Map the files that where found in both the old and new App version directoreis.
# Also set the result in the report glboal variable
# This result in a list of arrays containing the old and new file obj
def MapExistence(oldfarray, newfarray):
    lst = list()
    global report
    for newf in newfarray:
        foundInOld = False
        for oldf in oldfarray:
            if os.path.basename(newf).find(os.path.basename(oldf)) != -1:
                lst.append([oldf, newf])
                foundInOld = True
        if not foundInOld:
                report = report + '\n------->FILE WAS ON NEW BUT NOT ON OLD : ' + newf
    if not report:
        report = '\n------->ALL FILES WERE FOUND ON OLD<-------'
    return lst

#print the mapped values in a list passed by parameter
def PrintExistence(list):
    for arr in list:
        print('1 - ' + arr[0])
        print('2 - ' + arr[1])


# remove all attributes except some tags in the passed whitelist
def _remove_all_attrs_except(soup, whitelist):
    for tag in soup.find_all(True):
        if tag.name not in whitelist:
            tag.attrs = {}
    return soup

#load the html file, pettify it, and clean it removing/transforming : 
#   - some passed array of tags, AND br tags
#   - all attributes
#   - tranform client commenttemplate* into div tag
def removeTagsInHtmlFile(filename, tags):
    with open(filename) as file: 
        data = file.read()
        soup = BeautifulSoup(data, 'html.parser')
        #remove some tags
        for m in soup.find_all(tags):
            m.replaceWithChildren()
        #remove attributes
        soup = _remove_all_attrs_except(soup, tags)
        #prettify and transform/remove some unwanted elements
        data = soup.prettify()
        data = data.replace('commenttemplatebegin','div')
        data = data.replace('commenttemplateend','div')
        data = data.replace('<br/>','')
    return data

#remove enclosed spaces, car return, and shrik double spaces
def cleanDiff(text):
    s = text.strip().replace('\n','').replace('  ',' ')
    return s

#compare two strings and  return a report of differences
def getDiff(text, n_text):
    seqm = difflib.SequenceMatcher(None, text, n_text)
    output= []
    for opcode, a0, a1, b0, b1 in seqm.get_opcodes():
        if opcode == 'equal':
            continue
        elif opcode == 'insert':
            s = cleanDiff(seqm.b[b0:b1])
            if s:
                output.append("\ninsert NEW:" + s)
        elif opcode == 'delete':
            s = cleanDiff(seqm.a[a0:a1])
            if s:
                output.append("\ndelete OLD:" + s)
        elif opcode == 'replace':
            s = cleanDiff(seqm.b[b0:b1])
            if s:
                output.append("\nreplace OLD:" + s)
        else:
            raise RuntimeError, "unexpected opcode"
    return ''.join(output)

# analyse the passed list of mapped files and return a report with all the differences found
def checkDifferences(listToProcess):
    innerReport = ''
    for arr in listToProcess:
        #remove anchors <a>
        oldPrettyContent = removeTagsInHtmlFile(arr[0], ['a','img']).encode('utf-8')
        newPrettyContent = removeTagsInHtmlFile(arr[1], ['a','img']).encode('utf-8')
        if oldPrettyContent is newPrettyContent: #if exactly the same
            #copyfile(arr[1], baseDirOK+os.path.basename(arr[1]))
            print('OLD AND NEW FILES ARE EQUALS FOR: ' + arr[1])
        else:
            differences = getDiff(oldPrettyContent, newPrettyContent)
            if differences:
                headFound = '\n*** FOUND DIFFERENCES ON:\n\t' + arr[0] + '\n\t' + arr[1] 
                bodyFound = '\n\tDIFFERENCES:'+differences 
                print(headFound)
                print(bodyFound)
                baseFileName = baseDirKO + os.path.basename(arr[0])
                #save differneces
                diffFileToSave = open(baseFileName+'.diff', "w+")
                diffFileToSave.write(differences)
                diffFileToSave.close()
                #save comapared content
                oldFileToSave = open(baseFileName, "w+")
                newFileToSave = open(baseFileName+'_new', "w+")
                oldFileToSave.write(oldPrettyContent)
                newFileToSave.write(newPrettyContent)
                oldFileToSave.close()
                newFileToSave.close()
                innerReport = innerReport + headFound + bodyFound + differences
    return innerReport

# the the passed plain text in a email as a processing report
def send_mail(text):
    sender_user = 'template-noreply@client.com'  
    recipients = ['myMail@client.com', 'myMail2@client.com']
    #define mail content
    msg = MIMEText(text)
    msg['Subject'] = 'REPORT OLD AND NEW NL VERSIONS'
    msg['From'] = sender_user
    msg['To'] =  ','.join(recipients) 
    mailBody = msg.as_string()
    try:
        #define smpt server
        serverAddr = '10.66.24.113' #mailserver / 10.66.24.113
        smtp = smtplib.SMTP(serverAddr, 25)
        smtp.ehlo()
        #do send mail
        smtp.sendmail(sender_user, recipients, mailBody)
        smtp.close()
        print('Email sent!')
    except ValueError:
        print('Something went wrong...' + ValueError)

# MAIN function
def main():
    global report
    report = '' #always initialize it
    print('RUNNING AT : ' + datetime.now().strftime('%Y-%m-%d %H:%m:%s') )
    now = time.time()
    lastDate = getLastLaunchingFile()
    oldAppFiles = FilterFiles(loadOldAppFiles(), lastDate)
    newAppFiles = FilterFiles(glob.glob("/data/xml/*.html"), lastDate)
    listToProcess = MapExistence(oldAppFiles,newAppFiles)
    report = report + checkDifferences(listToProcess)
    updateLastLaunchingFile(now)
    #print('----------------------------------------\n\n'+report)
    send_mail(report)
    print('FINISH AT : ' + datetime.now().strftime('%Y-%m-%d %H:%m:%s') )


# run only if is run (not imported)
if __name__ == '__main__':
    main()

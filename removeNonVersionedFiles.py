#!/usr/bin/python

import glob, os
from shutil import copyfile
from bs4 import BeautifulSoup
import requests
from requests.auth import HTTPBasicAuth


url = 'https://svn.client.com/client/applications/trunk/data/'
ext = 'html'

baseTemplatePath = "/mnt/templates/data/"
templateBackupDir = '/opt/client/cleanCustomTemplates/templateBackup/'


user = 'SvnUser'
password = 'XXXXXX'

# From a given url, get an array of strins : 'data/<File_NAME>.xsl'
def get_svn_files(url, ext=''):
    page = requests.get(url, auth=HTTPBasicAuth(user, password), verify=False).text.encode('utf-8')
    soup = BeautifulSoup(page, 'html.parser')
    return [node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]


def load_files_to_compare(baseTemplatePath, ext=''):
    templateFiles = glob.glob(baseTemplatePath + "*."+ext) 
    templateFiles.sort(key=lambda file: os.path.getmtime(file))
    return [os.path.basename(file) for file in templateFiles]


def get_non_versioned_files(svnList, templateList):
    nonVersionedFiles = list()
    for tempalteFile in templateList:
        if tempalteFile not in svnList:
            nonVersionedFiles.append(tempalteFile)
    return nonVersionedFiles


def backup_templates(filesToBackup):
    for filename in filesToBackup:
        copyfile(baseTemplatePath+filename, templateBackupDir+filename)

def remove_files(filesToRemove):
    for filename in filesToRemove:
        fileN = baseTemplatePath+filename
        if os.path.exists(fileN):
            print('Removing file: ' + fileN)
#            os.remove(fileN)
        else:
            print('Cannot remove non existing file: ' + fileN)


def main():
    svnFiles = get_svn_files(url, ext)
    templateFiles = load_files_to_compare(baseTemplatePath, ext)
    nonVersionedFiles = get_non_versioned_files(svnFiles, templateFiles)
    backup_templates(nonVersionedFiles)
#    print nonVersionedFiles
    remove_files(nonVersionedFiles)


# run only if is run (not imported)
if __name__ == '__main__':
    main()
    
#main()

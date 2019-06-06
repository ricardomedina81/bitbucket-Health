import requests
import json
from nested_lookup import nested_lookup
import datetime
import argparse
import sys
import base64
import re

ap = argparse.ArgumentParser()
ap.add_argument("-url", "--baseurl", required=True, help="Provide git repository base url")
ap.add_argument("-u", "--user", required=True, help="User")
ap.add_argument("-p", "--password", required=True, help="Password")
ap.add_argument("-pr", "--project", required=True, help="Project name")
ap.add_argument("-r", "--repo", required=False, help="Repository name")

args = vars(ap.parse_args())

class activity:
    def __init__(self, id, kind, repo=None, branch=None, date=None):
        self.id     = id
        self.kind   = kind
        self.repo   = repo
        self.branch = branch
        self.date   = date 

class user:
    def __init__(self, userID):
        self.userID = userID
        self.activities = []

    def addActivity(self, activity):
        self.activities.append(activity)

    def printActivities(self):
        for thisActivity in self.activities:
            print(str(thisActivity.date) + ':' + str(thisActivity.repo) + ':' + str(thisActivity.branch) + ':' + str(thisActivity.id) + ':' + thisActivity.kind)

    def printUserDetails(self):
        print(self.userID)
        self.printActivities()

def findUserInList(userID, usersList):
    for thisUser in usersList:
        if thisUserEmail in thisUser.userID:
            return thisUser

    return None 

def bitbucketDate(bitbucketDate):
    strDate = bitbucketDate/1000 # remove last 3 zeros from timestamp value
    return datetime.date.fromtimestamp(strDate)

headers = {
    'Authorization': 'Basic ' + base64.b64encode(args['user'] + ':' + args['password']),
    'Content-Type': 'application/json',
}

params = (
    ('limit', '100'),
)

reponame =''
usersList =[]

try:
    print('>>> git Health Check <<<') 
    if args['repo']:
        print('>> Analizing project :' + args['project'] + ' | repo: ' + args['repo']) 
        reponame = args['repo']
    else:
        print('>> Analizing all repositories in project :' + args['project']) 

    response = requests.get(args['baseurl'] + 'rest/api/1.0/projects/' + args['project'] + '/repos/' + reponame, headers=headers, params=params)
    response_jsondata = json.loads(response.content, encoding=None)
    repos_list = nested_lookup('slug', response_jsondata)

    if len(repos_list) == 0:
        print(':( Sorry no repository foung with that name :' + args['project'] + '/' + args['repo'])
         
    for repo in repos_list: 
        response = requests.get(args['baseurl'] + 'rest/api/1.0/projects/' + args['project'] + '/repos/' + repo + '/branches', headers=headers, params=(('limit', '100'),('details', 'true'),))
        print('\n repo: *' + repo + '*') 
        response_jsondata = json.loads(response.content, encoding=None)
        #print(response.content)

        branches = response_jsondata['values']
        for branch in branches:

            #print(branch['metadata'])
            ageDays = (datetime.date.today() - bitbucketDate(branch['metadata']['com.atlassian.bitbucket.server.bitbucket-branch:latest-commit-metadata']['authorTimestamp'])).days
            print('    branch: *' + branch['displayId'] + '* updated ' + str(ageDays) + ' days ago)')

            message = ""

            # Check Branch Naming conventions
            if branch['displayId'].upper() == 'MASTER':
                message = "        + You have a master" 
                if str(branch['isDefault']) == "True":
                    message+= " and is set as default branch :thumbsup: "
                else:
                    message+= "but is NOT your default branch :rage: "
            
            elif branch['displayId'].upper() == 'DEVELOPMENT' or branch['displayId'].upper() == 'RELEASE' or branch['displayId'].upper() == 'INTEGRATION':
                message = "        Hummm... you shouldn't be using this branch name :broken_heart: "
            else:
                pattern = 'feature/[A-Z]\w+-[0-9]\w+'
                if not(re.match(pattern, branch['displayId'])):
                    message += "        Don't like your branch name that much  :thumbsdown:"
            
            # Add branch age information 
            if ageDays > 365:
                message += ". Think about deleting this bro!  :skull:"
            elif ageDays > 180:
                message += ". I see some spiderwebs, 6 months and you have not worked on this, take a look.  :("
            elif ageDays > 90:
                message += ". Forgot about this? 3 months ago it was important, how about now?  :("
            else:
                message += ". I see you're active on this. "
            print(message)

            # Review associated Pull Requests status
            try: 
                thisPullRequest = branch['metadata']['com.atlassian.bitbucket.server.bitbucket-ref-metadata:outgoing-pull-request-metadata']['pullRequest']
                #print(thisPullRequest)
                thisUserEmail = thisPullRequest['author']['user']['emailAddress']
                
                thisUser = findUserInList(thisUserEmail, usersList)
                if  thisUser == None:
                    usersList.append(user(thisUserEmail))
                    usersList[len(usersList) - 1].addActivity(activity(thisPullRequest["id"],"Pull Request Creator", repo, branch['displayId'], bitbucketDate(thisPullRequest["createdDate"])))
                else:
                    thisUser.addActivity(activity(thisPullRequest["id"],"Pull Request Creator", repo, branch['displayId'], bitbucketDate(thisPullRequest["createdDate"])))
        
                if branch['metadata']['com.atlassian.bitbucket.server.bitbucket-ref-metadata:outgoing-pull-request-metadata']['pullRequest']['state'].upper() == 'MERGED':
                    print('        @' + thisUserEmail +' Merged branches *MUST* be deleted :rage: ')
            except KeyError:
                pass

            # Review users commits activity in branch
            response = requests.get(args['baseurl'] + 'rest/api/1.0/projects/' + args['project'] + '/repos/' + repo + '/branches', headers=headers, params=(('limit', '100'),('details', 'true'),))
            print('\n repo: *' + repo + '*') 
            response_jsondata = json.loads(response.content, encoding=None)

    for user in usersList:
        user.printUserDetails()

except requests.exceptions.RequestException as e: 
    print e
    sys.exit(1)


        
        

    

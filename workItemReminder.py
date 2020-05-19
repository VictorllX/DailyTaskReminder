from vsts.vss_connection import VssConnection
from msrest.authentication import BasicAuthentication
import vsts.work.v4_1.models as models
from vsts.work_item_tracking.v4_1.models.wiql import Wiql
from pprint import pprint
import itertools
import re
import smtplib
import os
from datetime import date




def choice(prompt, choices, representation):
    print(prompt)
    for id, choice in enumerate(choices):
        print("[{}] {}".format(id+1, representation(choice)))
    print("")

    choice = int(input(">> ")) - 1
    while choice < 0 or choice > len(choices):
        print("{} is not a valid choice".format(choice+1))
        choice = int(input(">> ")) - 1

    print("")
    return choice


# TODO I am not sure this function will be working whenever we reach some query limit. Although since there is a team context, it should only be limited by the ids within the team
# As far as I am aware the limit is 20k results. I am not sure if this will cause an exception or silently fail.
def get_max_id(work_tracking_client, team_context):
    wiql_query = Wiql(query='SELECT ID FROM workitems')
    query_results = work_tracking_client.query_by_wiql(wiql_query, team_context=team_context)

    return max([id.id for id in query_results.work_items])


def get_work_items_upto(work_tracking_client, team_context, max_id):
    MAX_AMOUNT = 200
    result = []
    # Azure DevOps limits the amount that can be retrieved to 200 at once
    for i in range(int(max_id / MAX_AMOUNT)):
        work_items = work_tracking_client.get_work_items(range(1+(MAX_AMOUNT * i), 1 + MAX_AMOUNT + (MAX_AMOUNT * i)))
        result.extend(work_items)
    return result
  




# Fill in with your personal access token and org URL
# get token: https://dev.azure.com/cbts-internal/_usersSettings/tokens
personal_access_token = 'examplevexas5qopscl6xbv6g7o5ay23h7a'
organization_url = 'https://example:dev.azure.com/Internal'

# Create a connection to the org
credentials = BasicAuthentication('', personal_access_token)
connection = VssConnection(base_url=organization_url, creds=credentials)

# Get a client (the "core" client provides access to projects, teams, etc)
core_client = connection.get_client('vsts.core.v4_0.core_client.CoreClient')

# Get the list of projects in the org
projects = core_client.get_projects()

# Project choice that the program will be looking inside and working with
##working_project = choice("Choose project:", projects, lambda project: project.name)
working_project = projects[0]


teams = core_client.get_teams(project_id=working_project.id)


#working_team = choice("Choose team:", teams, lambda team: team.name)
working_team = teams[0]


# Get work client for access to boards
work_client = connection.get_client('vsts.work.v4_1.work_client.WorkClient')
work_tracking_client = connection.get_client('vsts.work_item_tracking.v4_1.work_item_tracking_client.WorkItemTrackingClient')
team_context = models.TeamContext(project_id=working_project.id, team_id=working_team.id)


# Creates a query
#Used to get a list of team members
past30 = Wiql(query="SELECT [Changed Date] FROM workitems WHERE [Changed Date] >= @StartOfDay-15 OR [System.State] = 'Active'  " )
result = work_tracking_client.query_by_wiql(past30, team_context=team_context)
#
wiql_query = Wiql(query="SELECT [Changed Date] FROM workitems WHERE [Changed Date] >= @StartOfDay" )
# Obtains work item information
query_results = work_tracking_client.query_by_wiql(wiql_query, team_context=team_context)


# start a list to parse the work items data into
work_items = []
userUpdated = []
allUser = []
#Gets a list of all team members
for y in result.work_items:

    try:
        y = work_tracking_client.get_work_item(y.id)
        user = y.fields['System.AssignedTo']
        parts = user.split('<')
        email = parts[1].strip('>') 
        allUser.append(email)
        allUser = list(dict.fromkeys(allUser))
        
    except KeyError:
        continue
print("\nList of team members: ")        
print(allUser)

# loop through each work itme
for x in query_results.work_items:
    
    #try/except block to catch keyerror message and continue
    try:
        y=work_tracking_client.get_work_item(x.id)
        
    # break the azure devops data into simpler bits
        user = y.fields['System.AssignedTo']
        parts = user.split('<')
        name = parts[0].strip()
        #Gets only email from list
        email = parts[1].strip('>')
        #removes duplicate emails
        userUpdated.append(email)
        userUpdated = list(dict.fromkeys(userUpdated))
    
    # setting data into the main dict
        tmp = {
        
            'Name': name,
            'Email': email,
            
        }

        work_items.append(dict(tmp))
    except KeyError:
         continue
    print("\nUser(s) who updated work item(s) today: ")
    print(userUpdated)
#Compares both lists and remove team members who have updated their tasks    
for x in allUser:
    for y in userUpdated:
        if x == y:
            allUser.remove(x)
            userUpdated.remove(y)

print("\nTeam member(s) who need to be reminded to update the board")            
print(str(allUser) + "\n")

#Outputs the day of the week on the console
x = date.today().weekday()
if x == 0:
    print("Day of the week: Monday\n")
elif x ==1:
    print("Day of the week: Tuesday\n")    
elif x ==2: 
    print("Day of the week: Wednesday\n") 
elif x ==3: 
    print("Day of the week: Thursday\n") 
elif x ==4:  
    print("Day of the week: Friday\n")        
else:
    (print("Emails not sent out on Saturday and Sunday "))

#Formats email
# if mon - thurs
# send email to USER here    
count = 0
for emails in allUser:
    count = count + 1
    #print(emails)
    print("Email #" + str(count) + " sent to " + emails )
    msg = "This is a reminder to update your to do list on the teams daily standup dashboard. This can be done simply by editing or adding a work item.\n\n In order to stop receiving these emails, please remember to do this before 2 pm Monday-Friday.\n\n Daily Standup Dashboard:\nhttps://dev.azure.com/CBTS-Internal/Cloud-Transformation/_dashboards/dashboard/4c3f9381-aaa4-4723-a840-7cb4c5ceebef"

    if date.today().weekday() < 5:
            def send_email(subject, msg):
                try:
                   

                    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
                    #CHANGE
                    server.login("your email", "password")
                    message = 'Subject: {}\n\n{}'.format(subject, msg)
                    #CHANGE
                    #Use emails variable to begin sending to team member emails
                    server.sendmail("your email", emails, message)    
                    server.quit()
                    print("Email sent successfully!!!!!!")
                except:
                    print("Email failed to send!")   
                    
            subject = "Daily task reminder"
            
            send_email(subject, msg)
            
      

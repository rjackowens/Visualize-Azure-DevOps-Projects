import requests
import urllib3
import logging
import re
import subprocess
import json
import base64
from itertools import zip_longest
from datetime import datetime
from config import server, organization, username, PAT, project

outputFile = (str(project) + ".wsd")

now = datetime.now()
log_date = now.strftime("%m%d%Y")

logging.basicConfig(
    filename=f".\\logs\\{log_date}.log",
    level=logging.DEBUG,
    format='%(asctime)s:%(levelname)s: %(message)s',
    datefmt='%I:%M:%S'
    )

log = logging.getLogger()
log.info("START")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def createUrl(*args):
    base = server + organization
    return base + "".join(args)

def getRequest(*args):
    url = createUrl(*args)
    response = requests.get(url, auth=(username, PAT), verify=False)
    return response.json()

def postRequest(*args, **kwargs):
    url = createUrl(*args)
    response = requests.post(url, auth=(username, PAT), verify=False, **kwargs)

    if response.status_code == 409:
        log.info(f"Wiki for {project} already exists")

    return response.json()

def putRequest(*args, **kwargs):
    url = createUrl(*args)
    response = requests.put(url, auth=(username, PAT), verify=False, **kwargs)
    return response.json()

def deleteRequest(*args, **kwargs):
    url = createUrl(*args)
    response = requests.delete(url, auth=(username, PAT), verify=False, **kwargs)
    return response.json()


all_repos = getRequest(project, "/_apis/git/repositories")

list_of_repos = []
for repo in all_repos["value"] or []:
    list_of_repos.append(repo["name"])

buildDefinitions = getRequest(project, "/_apis/build/definitions/")

build_definition_IDs = []
build_pipeline_names = []
for build in buildDefinitions["value"]:
    if build["queueStatus"] == "enabled":  # Skip over disabled builds
        build_definition_IDs.append(build["id"])
        build_pipeline_names.append(build["name"])

associated_build_repos = []  # Repos containing an associated build pipeline
for ID in build_definition_IDs:
    buildDefinition = getRequest(project, "/_apis/build/definitions/", str(ID))
    log.debug(buildDefinition["repository"].get("name"), "has pipeline")
    try:
        associated_build_repos.append(buildDefinition["repository"].get("name"))
    except KeyError as e:
        log.error(e)

with open(".\\templates\\wbsHeader.txt") as file:
    wbsHeader = file.read()
log.info("Opened wbsHeader.txt template")

wbsFooter = "@endwbs"

org = "+ ORGANIZATION: " + re.sub('[/]', '', organization)

def writeProject(project):
    _project = f"++ PROJECT: {project}"
    log.info(f"Writing project {project} to outputFile")
    return _project

def writeRepo(repo):
    _repo = f"+++ REPO: {repo}"
    log.info(f"Writing repo {repo} to outputFile")
    return _repo

def writePipeline(name):
    _name = f"++++ PIPELINE: {name}"
    log.info(f"Writing pipeline {name} to outputFile")
    return _name


class PlantUML():
    def __init__(self, fileName):
        self.fileName = ".\\models\\" + fileName

    def eraseFile(self):
        open(self.fileName, "w").close()
        log.info(f"Erasing {self.fileName}")

    def writeToFile(self, _string):
        with open(self.fileName, "a") as file:
            file.write("\n" + str(_string))

    def generateModelFile(self):
        subprocess.check_output(['plantuml', self.fileName])
        log.info(f"Generating {self.fileName} file")

    def generatePlantUML(self):
        self.eraseFile()
        self.writeToFile(wbsHeader)
        self.writeToFile(org)
        self.writeToFile(writeProject(project))

        for repo, name in zip_longest(list_of_repos, build_pipeline_names):
            self.writeToFile(writeRepo(repo))
            if repo in associated_build_repos:
                self.writeToFile(writePipeline(name))
        self.writeToFile(wbsFooter)

        # Writing Image to File
        self.generateModelFile()
        log.info("Generated image model to local folder")


model = PlantUML(outputFile)

model.generatePlantUML() # Outputs file as {project}.png to .\models

# Create Project Wiki
def createWiki(_project):
    wiki_name = {
        "name": f"{_project}.wiki"
    }

    wiki_headers = {
        'Content-Type': 'application/json'
    }

    print(postRequest(_project, "/_apis/wiki/wikis", "?api-version=5.1-preview.1", data=json.dumps(wiki_name), headers=wiki_headers))
    log.info("Created project wiki")


createWiki(project)


# Convert Image Model to Base64
def convertImageBase64(_imageModel):
    with open (f".\\models\\{_imageModel}.png", "rb") as file:
        _image = base64.b64encode(file.read())
        return _image
    log.info("Converted image model to base64")


base64_image = convertImageBase64(project)

# Creates Date Suffix in Format of -HourMinute-Month-Day
unique_date = now.strftime("-%H%M-%m-%d")

# Attaching Image to Wiki Attachments (https://dev.azure.com/{organization}/{project}/_git/{project}.wiki?version=GBwikiMaster)
def attachImageToWiki(_project):
    image_content_type = {
        'Content-Type': 'application/octet-stream'
    }

    print(
        putRequest(
            _project,
            "/_apis/wiki/wikis/",
            f"{_project}.wiki/attachments",
            f"?name={project}{unique_date}.png",
            "&api-version=5.1",
            data=base64_image,
            headers=image_content_type
            )
        )
    log.info("Attached Image to Wiki Attachments")


attachImageToWiki(project)

# Deleting Existing Wiki Page
def deleteWikiPage():
    deleteRequest(project, "/_apis/wiki/wikis/", f"{project}.wiki/pages", "?path=Project-Structure&api-version=5.1")
    log.info("Deleted existing wiki page")


deleteWikiPage()

# Creating New Wiki Page With Inline Image 
def createWikiPage(_project):
    image_path = {
        "content": f"![{project}{unique_date}.png](/.attachments/{project}{unique_date}.png)"
    }

    json_content_type = {
        'Content-Type': 'application/json',
        'Accept': 'text/plain'
    }

    print(
        putRequest(
            _project,
            "/_apis/wiki/wikis/",
            f"{_project}.wiki/pages",
            "?path=Project-Structure&api-version=5.1",
            data=json.dumps(image_path),
            headers=json_content_type
        )
    )
    log.info("Created new wiki page")


createWikiPage(project)

log.info("EXIT 0")

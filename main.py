import logging
import re
import subprocess
import json
import base64
import requests
import urllib3
from datetime import datetime
from pathlib import Path
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from config import organization, organization_url, username, PAT

now = datetime.now()
log_date = now.strftime("%m%d%Y")

logging.basicConfig(
    filename=f".\\logs\\{log_date}.log",
    level=logging.DEBUG,
    format='%(asctime)s:%(levelname)s: %(message)s',
    datefmt='%I:%M:%S'
    )

log = logging.getLogger(__name__)
log.info("START")

try:
    Path(".\\logs").mkdir(exist_ok=True)
    Path(".\\models").mkdir(exist_ok=True)
    assert Path(".\\templates\\wbsHeader.txt").exists()
    log.debug("Folder check passed")
except (IOError, AssertionError) as e:
    log.error(e, exc_info=True)
    raise

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def makeRequest(*args, **kwargs):
    """Sends HTTP requests to Azure DevOps API"""
    url = organization_url + "".join(args)

    if kwargs.get("request_method") == "get":
        handler = requests.get
    elif kwargs.get("request_method") == "post":
        handler = requests.post
    elif kwargs.get("request_method") == "put":
        handler = requests.put
    elif kwargs.get("request_method") == "delete":
        handler = requests.delete
    else:
        log.error("No requests method selected")
        raise LookupError

    try:
        response = handler(url, auth=(username, PAT), verify=False, data=kwargs.get("data"), headers=kwargs.get("headers"))
        if response.status_code == 409:
            log.warning(f"Wiki for {project} already exists")
    except requests.exceptions.HTTPError as e:
        log.error(f"HTTP exception {e} has occurred")
        raise
    return response.json()

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
    def __init__(self, fileName, project):
        self.fileName = ".\\models\\" + fileName
        self.project = project

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
        """Outputs file as {project}.png to models"""
        self.eraseFile()
        self.writeToFile(wbsHeader)
        self.writeToFile(org)
        self.writeToFile(writeProject(self.project))

        for repo in list_of_repos:
            self.writeToFile(writeRepo(repo))
            for group in associated_build_repos:
                associated_repos = group.get("associated_repo")
                associated_builds = group.get("associated_build")
                if repo in associated_repos:
                    self.writeToFile(writePipeline(associated_builds))
        self.writeToFile(wbsFooter)

        # Writing Image to File
        self.generateModelFile()
        log.info("Generated image model to local folder")

def createWiki(_project):
    """Creates New Wiki Page With Inline Image"""
    wiki_name = {
        "name": f"{_project}.wiki"
    }

    wiki_headers = {
        'Content-Type': 'application/json'
    }

    log.debug(
        makeRequest(
            _project,
            "/_apis/wiki/wikis",
            "?api-version=5.1-preview.1",
            request_method="post",
            data=json.dumps(wiki_name),
            headers=wiki_headers
            )
        )
    log.info(f"Created {_project} project wiki")

def convertImageBase64(_imageModel):
    with open (f".\\models\\{_imageModel}.png", "rb") as file:
        _image = base64.b64encode(file.read())
        return _image
    log.info(f"Converted {_imageModel} image model to base64")

# Creates Date Suffix in Format of -HourMinute-Month-Day
unique_date = now.strftime("-%H%M-%m-%d")

def attachImageToWiki(_project):
    """Attaches Image to Wiki Attachments (https://dev.azure.com/{organization}/{project}/_git/{project}.wiki?version=GBwikiMaster)"""
    image_content_type = {
        'Content-Type': 'application/octet-stream'
    }

    log.debug(
        makeRequest(
            _project,
            "/_apis/wiki/wikis/",
            f"{_project}.wiki/attachments",
            f"?name={_project}{unique_date}.png",
            "&api-version=5.1",
            request_method="put",
            data=base64_image,
            headers=image_content_type
            )
        )
    log.info(f"Attached Image to {_project} Wiki Attachments")

def deleteWikiPage(_project):
    makeRequest(_project, "/_apis/wiki/wikis/", f"{_project}.wiki/pages", "?path=Project-Structure&api-version=5.1", request_method="delete")
    log.info(f"Deleted existing {_project} wiki page")

def createWikiPage(_project):
    image_path = {
        "content": f"![{_project}{unique_date}.png](/.attachments/{_project}{unique_date}.png)"
    }

    json_content_type = {
        'Content-Type': 'application/json',
        'Accept': 'text/plain'
    }

    log.debug(
        makeRequest(
            _project,
            "/_apis/wiki/wikis/",
            f"{_project}.wiki/pages",
            "?path=Project-Structure&api-version=5.1",
            request_method="put",
            data=json.dumps(image_path),
            headers=json_content_type
        )
    )
    log.info(f"Created new {_project} wiki page")


with open(".\\templates\\wbsHeader.txt") as file:
    wbsHeader = file.read()
log.info("Opened wbsHeader.txt template")

wbsFooter = "@endwbs"

org = "+ ORGANIZATION: " + re.sub('[/]', '', organization)

# Creating Python Client Library Connection
credentials = BasicAuthentication('', PAT)
connection = Connection(base_url=organization_url, creds=credentials)

# Get a client (the "core" client provides access to projects, teams, etc)
core_client = connection.clients.get_core_client()

# Getting All Projects
get_projects_response = core_client.get_projects()
all_projects = []
# Get the first page of projects
while get_projects_response is not None:
    for project in get_projects_response.value:
        log.info(f"Getting project {project.name}")
        all_projects.append(project.name)
    if get_projects_response.continuation_token is not None and get_projects_response.continuation_token != "":
        # Get the next page of projects
        get_projects_response = core_client.get_projects(continuation_token=get_projects_response.continuation_token)
    else:
        # All projects have been retrieved
        assert get_projects_response.continuation_token is None
        get_projects_response = None

for project in all_projects:
    outputFile = (str(project) + ".wsd")

    all_repos = makeRequest(project, "/_apis/git/repositories", request_method="get")

    list_of_repos = []
    for repo in all_repos["value"] or []:
        list_of_repos.append(repo["name"])

    buildDefinitions = makeRequest(project, "/_apis/build/definitions/", request_method="get")

    build_definition_IDs = []
    build_pipeline_names = []
    for build in buildDefinitions["value"]:
        if build["queueStatus"] == "enabled":  # Skip over disabled builds
            build_definition_IDs.append(build["id"])
            build_pipeline_names.append(build["name"])

    associated_build_repos = []  # Repos containing an associated build pipeline
    for ID in build_definition_IDs:
        buildDefinition = makeRequest(project, "/_apis/build/definitions/", str(ID), request_method="get")
        log.debug(buildDefinition["repository"].get("name"), "has pipeline")
        try:
            group = {
                'associated_repo': buildDefinition["repository"].get("name"),
                'associated_build': buildDefinition.get("name")
                }
            associated_build_repos.append(group)
        except KeyError as e:
            log.error(e, exc_info=True)
            raise

    model = PlantUML(outputFile, project)

    model.generatePlantUML()

    createWiki(project)

    base64_image = convertImageBase64(project)

    attachImageToWiki(project)

    deleteWikiPage(project)
 
    createWikiPage(project)

log.info("EXIT 0")

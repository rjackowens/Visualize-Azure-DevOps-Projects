# Summary
Creates PlantUML WBS model of Azure DevOps Project repositories and associated pipelines and uploads the model image to the project Wiki.

# Project Requirements
Install contents of `requirements.txt` via pip.

Enter values for `server`, `organization`, `username`, `PAT`, and `project` in `config.py`.

# Azure DevOps Requirements
1. PAT must have access to Read/Write/Manage Build, Release, Code, and Wiki.

2. No spaces must exist in Azure DevOps project name.
 
3. Pipeline names must begin with the repository it is associated with.

# Usage
WBS model header containing theme settings is stored in `.\templates` .

Model files are stored in `.\models`.
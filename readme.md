# Summary
Creates PlantUML WBS model of all Azure DevOps Project repositories and associated pipelines and uploads the model image to the project Wiki.

# Requirements
Install contents of `requirements.txt` via pip.

Enter values for `server`, `organization`, `username`, and `PAT` in `config.py`.

# Azure DevOps Requirements
1. PAT must have access to Read/Write/Manage Build, Release, Code, and Wiki.

2. No spaces must exist in Azure DevOps project name.
 
3. Pipeline names must begin with the repository it is associated with.

# Usage
Run `main.py` to generate models for all projects.

WBS header containing customizable theme settings is stored in `.\templates` .

Model files are stored locally in `.\models`.

#!/usr/bin/env python
import sys
sys.path.insert(0, './backend')

from app.db.session import engine
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import ResourceModel, ProjectMemberModel, ProjectModel

# Connect to database
with Session(engine) as db:
    # Find the skill resource
    skill = db.scalar(select(ResourceModel).where(
        ResourceModel.id == "5c674e39-2a1e-42d0-9fa6-35146c4df709"
    ))
    
    if skill:
        print(f"Skill: {skill.name}")
        print(f"Project ID: {skill.project_id}")
        print(f"Owner ID: {skill.owner_id}")
        
        # Get project details
        project = db.scalar(select(ProjectModel).where(
            ProjectModel.id == skill.project_id
        ))
        if project:
            print(f"Project Name: {project.name}")
        
        # Check if hljtest2 is a member of this project
        membership = db.scalar(select(ProjectMemberModel).where(
            (ProjectMemberModel.project_id == skill.project_id) &
            (ProjectMemberModel.user_id == "hljtest2")
        ))
        
        if membership:
            print(f"hljtest2 is a member of this project (role: {membership.role})")
        else:
            print("hljtest2 is NOT a member of this project")
    else:
        print("Skill not found")

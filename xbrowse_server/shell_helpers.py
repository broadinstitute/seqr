from base.models import Project

def getproj(project_id): 
    return Project.objects.get(project_id=project_id)

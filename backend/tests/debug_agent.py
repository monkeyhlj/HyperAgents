import requests

BASE_URL = 'http://localhost:8000/api/v1'

# Get project
projects = requests.get(f'{BASE_URL}/projects').json()
project_id = projects[0]['id']

print(f'Project ID: {project_id}')

# Get agents
agents = requests.get(f'{BASE_URL}/resources/projects/{project_id}?kind=agent').json()

print('First Zhipu agent:')
for agent in agents:
    if agent.get('model_provider') == 'zhipu':
        aid = agent.get('id')
        pid = agent.get('project_id')
        src = agent.get('source')
        print(f'  Agent ID: {aid}')
        print(f'  Project ID: {pid}')
        print(f'  Source: {src}')
        print(f'  Match: {pid == project_id}')
        break

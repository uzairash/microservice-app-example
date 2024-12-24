import boto3

# Initialize ECS client
ecs_client = boto3.client('ecs', 'ap-south-1')

def create_cluster(ecs_client, cluster_name):
    response = ecs_client.create_cluster(
        clusterName=cluster_name,
        capacityProviders=['FARGATE'],
        serviceConnectDefaults={
        'namespace': cluster_name
    }
    )
    print(f'Cluster {cluster_name} created successfully')
    return response['cluster']['clusterArn']

def register_task_definition(ecs_client, service_name, image, environment, port_mappings, private_repo_creds, execution_role, task_role):
    response = ecs_client.register_task_definition(
        family=service_name,
        containerDefinitions=[
            {
                'name': service_name,
                'image': image,
                'repositoryCredentials': {
                    'credentialsParameter': private_repo_creds
                } if private_repo_creds else None,
                'cpu': 256,
                'memory': 512,
                'essential': True,
                'environment': [{'name': k, 'value': v} for k, v in environment.items()],
                'portMappings': port_mappings
            }
        ],
        ephemeralStorage={
        'sizeInGiB': 21
        },
        runtimePlatform={
            'cpuArchitecture': 'X86_64',
            'operatingSystemFamily': 'LINUX'
        },
        taskRoleArn=task_role,
        executionRoleArn=execution_role,
        requiresCompatibilities=['FARGATE'],
        networkMode='awsvpc',
        cpu='256',
        memory='512'
    )
    print(f'Task definition for {service_name} created successfully')
    return response['taskDefinition']['taskDefinitionArn']

def create_service(ecs_client, cluster_name, service_name, task_definition, subnets, security_groups):
    response = ecs_client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        taskDefinition=task_definition,
        desiredCount=1,
        launchType='FARGATE',
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': subnets,
                'securityGroups': security_groups,
                'assignPublicIp': 'ENABLED'
            }
        },
        serviceConnectConfiguration={
            'enabled': True,
            'namespace': cluster_name,
            
        }
    )
    print(f'Service {service_name} created successfully')
    return response['service']['serviceArn']



# Cluster details
cluster_name = 'microservices-cluster'
subnets = ['subnet-021e4c85656747d98', 'subnet-091f161d52ffc95ac', 'subnet-0f589277124822a92']
security_groups = ['sg-0f7d983d4dc5cd3e2']
execution_role_arn = 'arn:aws:iam::730335323304:role/ecsTaskExecutionRole'
task_role_arn = 'arn:aws:iam::730335323304:role/ecsTaskExecutionRole'
repo_creds_arn = 'arn:aws:secretsmanager:ap-south-1:730335323304:secret:Docker-hub-credentials-mENosM'

# Create ECS Cluster
cluster_arn = create_cluster(ecs_client, cluster_name)

# Microservices configuration
services = [
    {
        'name': 'frontend',
        'image': 'uzair102/u_repo:frontend',
        'environment': {
            'PORT': '8080',
            'AUTH_API_ADDRESS': 'http://auth-api:8081',
            'TODOS_API_ADDRESS': 'http://todos-api:8082',
            'ZIPKIN_URL': 'http://zipkin:9411/api/v2/spans'
        },
        'portMappings': [{'containerPort': 8080, 'hostPort': 8080, 'protocol': 'tcp'}]
    },
    {
        'name': 'auth-api',
        'image': 'uzair102/u_repo:auth-api',
        'environment': {
            'AUTH_API_PORT': '8081',
            'JWT_SECRET': 'myfancysecret',
            'USERS_API_ADDRESS': 'http://users-api:8083',
            'ZIPKIN_URL': 'http://zipkin:9411/api/v2/spans'
        },
        'portMappings': [{'containerPort': 8081, 'hostPort': 8081, 'protocol': 'tcp'}]
    },
    {
        'name': 'todos-api',
        'image': 'uzair102/u_repo:todos-api',
        'environment': {
            'TODO_API_PORT': '8082',
            'JWT_SECRET': 'myfancysecret',
            'REDIS_HOST': 'redis-queue',
            'REDIS_PORT': '6379',
            'REDIS_CHANNEL': 'log_channel',
            'ZIPKIN_URL': 'http://zipkin:9411/api/v2/spans'
        },
        'portMappings': [{'containerPort': 8082, 'hostPort': 8082, 'protocol': 'tcp'}]
    },
    {
        'name': 'users-api',
        'image': 'uzair102/u_repo:users-api',
        'environment': {
            'SERVER_PORT': '8083',
            'JWT_SECRET': 'myfancysecret',
            'SPRING_ZIPKIN_BASE_URL': 'http://zipkin:9411'
        },
        'portMappings': [{'containerPort': 8083, 'hostPort': 8083, 'protocol': 'tcp'}]
    },
    {
        'name': 'log-message-processor',
        'image': 'log-message-processor',
        'environment': {
            'REDIS_HOST': 'redis-queue',
            'REDIS_PORT': '6379',
            'REDIS_CHANNEL': 'log_channel',
            'ZIPKIN_URL': 'http://zipkin:9411/api/v1/spans'
        },
        'portMappings': []
    },
    {
        'name': 'zipkin',
        'image': 'openzipkin/zipkin',
        'environment': {},
        'portMappings': [{'containerPort': 9411, 'hostPort': 9411, 'protocol': 'tcp'}]
    },
    {
        'name': 'redis-queue',
        'image': 'redis',
        'environment': {},
        'portMappings': []
    }
]

# Deploy services
for service in services:
    task_def_arn = register_task_definition(
        ecs_client,
        service_name=service['name'],
        image=service['image'],
        environment=service['environment'],
        port_mappings=service['portMappings'],
        private_repo_creds=repo_creds_arn,
        execution_role=execution_role_arn,
        task_role=task_role_arn
    )
    create_service(
        ecs_client,
        cluster_name=cluster_name,
        service_name=service['name'],
        task_definition=task_def_arn,
        subnets=subnets,
        security_groups=security_groups
    )

print("All services deployed successfully.")

using './main.bicep'

param resourceGroupName = readEnvironmentVariable('AZURE_ENV_NAME', 'society-demo-rg')
param location = readEnvironmentVariable('AZURE_LOCATION', 'eastus2')
param aiServicesName = 'society-agent-resource'
param communicationServicesName = 'societyacs'
param modelDeploymentName = 'gpt-4o-mini'
param modelName = 'gpt-4o-mini'
param modelVersion = '2024-07-18'
param principalId = readEnvironmentVariable('AZURE_PRINCIPAL_ID', '')

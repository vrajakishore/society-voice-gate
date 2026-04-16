// Azure AI Services (multi-service) — provides Voice Live API + Azure OpenAI
@description('AI Services account name')
param name string

@description('Location')
param location string

@description('Model deployment name')
param modelDeploymentName string

@description('Model name')
param modelName string

@description('Model version')
param modelVersion string

resource aiServices 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
    customSubDomainName: name
  }
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aiServices
  name: modelDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
  }
}

output name string = aiServices.name
output endpoint string = aiServices.properties.endpoint

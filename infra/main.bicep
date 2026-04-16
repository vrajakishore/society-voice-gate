targetScope = 'subscription'

// ── Parameters ──────────────────────────────────────────────────────────────
@description('Name of the resource group to create')
param resourceGroupName string

@description('Primary location for resources')
param location string

@description('Name for the Azure AI Services (multi-service) account')
param aiServicesName string

@description('Name for the Azure Communication Services resource')
param communicationServicesName string

@description('Model deployment name')
param modelDeploymentName string = 'gpt-4o-mini'

@description('Model name to deploy')
param modelName string = 'gpt-4o-mini'

@description('Model version')
param modelVersion string = '2024-07-18'

@description('Principal ID of the signed-in user for RBAC')
param principalId string

// ── Resource Group ──────────────────────────────────────────────────────────
resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
}

// ── AI Services (Voice Live API + Azure OpenAI) ─────────────────────────────
module aiServices 'modules/ai-services.bicep' = {
  scope: rg
  name: 'ai-services'
  params: {
    name: aiServicesName
    location: location
    modelDeploymentName: modelDeploymentName
    modelName: modelName
    modelVersion: modelVersion
  }
}

// ── Azure Communication Services ────────────────────────────────────────────
module acs 'modules/communication-services.bicep' = {
  scope: rg
  name: 'communication-services'
  params: {
    name: communicationServicesName
  }
}

// ── RBAC — Cognitive Services User on AI Services resource ──────────────────
module roleAssignment 'modules/role-assignment.bicep' = {
  scope: rg
  name: 'role-assignment'
  params: {
    aiServicesName: aiServices.outputs.name
    principalId: principalId
  }
}

// ── Outputs (available in postprovision hook as env vars) ───────────────────
output COGNITIVE_SERVICES_ENDPOINT string = aiServices.outputs.endpoint
output AI_SERVICES_NAME string = aiServices.outputs.name
output ACS_NAME string = acs.outputs.name
output RESOURCE_GROUP_NAME string = rg.name

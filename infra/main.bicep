// AtlasLens — minimal Azure footprint for the hackathon MVP.
// Resources provisioned:
//   - Log Analytics workspace + Application Insights
//   - Azure AI Search (Basic)
//   - Cosmos DB (serverless, NoSQL)
//   - Container Apps environment + a placeholder app (FastAPI backend)
//   - Static Web App is provisioned manually via `swa deploy` (no Bicep needed)
//
// Azure OpenAI is created separately (Foundry resource) because it requires
// special quota approval in many regions. Configure its endpoint/key via .env.
//
// Usage:
//   az deployment sub create -l japaneast -f infra/main.bicep \
//       -p namePrefix=atlaslens openAiEndpoint=https://... openAiKey=...

targetScope = 'subscription'

@description('Short prefix used for all resource names (lowercase, no spaces).')
param namePrefix string = 'atlaslens'

@description('Azure region.')
param location string = 'japaneast'

@description('Pre-provisioned Azure OpenAI endpoint (paste from Foundry).')
param openAiEndpoint string

@secure()
@description('Pre-provisioned Azure OpenAI API key.')
param openAiKey string

var rgName = '${namePrefix}-rg'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
}

module workspace 'modules/observability.bicep' = {
  name: 'observability'
  scope: rg
  params: {
    namePrefix: namePrefix
    location: location
  }
}

module search 'modules/search.bicep' = {
  name: 'search'
  scope: rg
  params: {
    namePrefix: namePrefix
    location: location
  }
}

module cosmos 'modules/cosmos.bicep' = {
  name: 'cosmos'
  scope: rg
  params: {
    namePrefix: namePrefix
    location: location
  }
}

module containerApps 'modules/container_apps.bicep' = {
  name: 'containerApps'
  scope: rg
  params: {
    namePrefix: namePrefix
    location: location
    logAnalyticsWorkspaceId: workspace.outputs.logAnalyticsId
    logAnalyticsCustomerId: workspace.outputs.customerId
    logAnalyticsSharedKey: workspace.outputs.primarySharedKey
    openAiEndpoint: openAiEndpoint
    openAiKey: openAiKey
    searchEndpoint: search.outputs.searchEndpoint
    searchKey: search.outputs.adminKey
    cosmosEndpoint: cosmos.outputs.endpoint
    cosmosKey: cosmos.outputs.primaryKey
  }
}

output backendUrl string = containerApps.outputs.backendUrl
output searchEndpoint string = search.outputs.searchEndpoint
output cosmosEndpoint string = cosmos.outputs.endpoint

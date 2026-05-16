param namePrefix string
param location string

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: '${namePrefix}-search'
  location: location
  sku: { name: 'basic' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    semanticSearch: 'free'
  }
}

output searchEndpoint string = 'https://${search.name}.search.windows.net'
output adminKey string = listAdminKeys(search.id, '2024-06-01-preview').primaryKey

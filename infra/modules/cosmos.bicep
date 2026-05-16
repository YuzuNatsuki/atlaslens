param namePrefix string
param location string

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-08-15' = {
  name: '${namePrefix}-cosmos'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    capabilities: [
      { name: 'EnableServerless' }
    ]
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    locations: [
      { locationName: location, failoverPriority: 0, isZoneRedundant: false }
    ]
    publicNetworkAccess: 'Enabled'
  }
}

resource db 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-08-15' = {
  name: 'atlaslens'
  parent: account
  properties: {
    resource: { id: 'atlaslens' }
  }
}

resource knowledge 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-08-15' = {
  name: 'knowledge'
  parent: db
  properties: {
    resource: {
      id: 'knowledge'
      partitionKey: { paths: ['/member_id'], kind: 'Hash' }
      indexingPolicy: { indexingMode: 'consistent' }
    }
  }
}

output endpoint string = account.properties.documentEndpoint
output primaryKey string = account.listKeys().primaryMasterKey

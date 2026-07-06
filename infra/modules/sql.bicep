@description('SQL logical server name')
param name string

@description('Azure region')
param location string

@description('SQL administrator password')
@secure()
param adminPassword string

resource sql 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: name
  location: location
  properties: {
    administratorLogin: 'sqladmin'
    administratorLoginPassword: adminPassword
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

// CDC requires the Standard tier or higher (Basic does not support it).
resource db 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sql
  name: 'source'
  location: location
  sku: {
    name: 'S0'
    tier: 'Standard'
  }
}

// Let Azure services (the pipeline runner) reach the server. Lock this down in production.
resource allowAzure 'Microsoft.Sql/servers/firewallRules@2023-05-01-preview' = {
  parent: sql
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

output fqdn string = sql.properties.fullyQualifiedDomainName

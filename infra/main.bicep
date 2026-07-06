targetScope = 'resourceGroup'

@description('Azure region')
param location string = resourceGroup().location

@description('Short prefix for resource names')
param namePrefix string = 'cdcscd2'

@description('SQL administrator password')
@secure()
param sqlAdminPassword string

// ADLS Gen2 storage for the Delta warehouse (dim tables + history).
module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    name: '${namePrefix}sa${uniqueString(resourceGroup().id)}'
    location: location
  }
}

// Azure SQL source (Standard tier — CDC requires Standard or higher).
module sql 'modules/sql.bicep' = {
  name: 'sql'
  params: {
    name: '${namePrefix}-sql-${uniqueString(resourceGroup().id)}'
    location: location
    adminPassword: sqlAdminPassword
  }
}

output sqlFqdn string = sql.outputs.fqdn
output storageAccount string = storage.outputs.name

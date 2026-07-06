@description('Storage account name (3-24 lowercase alphanumeric)')
param name string

@description('Azure region')
param location string

// ADLS Gen2 (hierarchical namespace) for the Delta warehouse.
resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    isHnsEnabled: true
  }
}

output name string = sa.name

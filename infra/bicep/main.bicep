@description('Region for all resources.')
param location string

@description('Name of the Azure Container Registry used to store the custom function image.')
param acrName string

@description('SKU for the Azure Container Registry.')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param acrSku string = 'Basic'

@description('Name of the storage account for the Function App.')
param storageAccountName string

@description('Name of the App Service plan that will host the Function App.')
param hostingPlanName string

@description('SKU for the App Service plan.')
@allowed([
  'EP1'
  'EP2'
  'EP3'
  'PC2'
  'PC3'
  'PC4'
])
param hostingPlanSku string = 'EP1'

@description('Name of the Function App.')
param functionAppName string

@description('Name of the Docker repository (without registry hostname).')
param imageName string

@description('Tag of the Docker image to deploy.')
param imageTag string

@description('Optional array of additional app settings to add to the Function App.')
param appSettings array = []

var defaultAppSettings = [
  {
    name: 'FUNCTIONS_WORKER_RUNTIME'
    value: 'python'
  }
  {
    name: 'FUNCTIONS_EXTENSION_VERSION'
    value: '~4'
  }
]

resource acr 'Microsoft.ContainerRegistry/registries@2023-06-01-preview' = {
  name: acrName
  location: location
  sku: {
    name: acrSku
  }
  properties: {
    adminUserEnabled: false
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

var storageAccountKeys = storageAccount.listKeys().keys
var storageConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccountKeys[0].value};EndpointSuffix=${environment().suffixes.storage}'

resource hostingPlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: hostingPlanName
  location: location
  sku: {
    name: hostingPlanSku
    tier: startsWith(hostingPlanSku, 'EP') ? 'ElasticPremium' : 'PremiumContainer'
  }
  properties: {
    reserved: true
  }
}

var extraAppSettings = [
  {
    name: 'AZURE_FUNCTIONS_ENVIRONMENT'
    value: 'Production'
  }
  {
    name: 'AzureWebJobsStorage'
    value: storageConnectionString
  }
  {
    name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
    value: storageConnectionString
  }
  {
    name: 'WEBSITE_CONTENTSHARE'
    value: toLower('${uniqueString(functionAppName, resourceGroup().id)}-content')
  }
  {
    name: 'DOCKER_REGISTRY_SERVER_URL'
    value: 'https://${acr.name}.azurecr.io'
  }
  {
    name: 'WEBSITE_RUN_FROM_PACKAGE'
    value: ''
  }
  {
    name: 'FUNCTIONS_WORKER_PROCESS_COUNT'
    value: '1'
  }
]

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: hostingPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${acr.name}.azurecr.io/${imageName}:${imageTag}'
      alwaysOn: true
      appSettings: concat(defaultAppSettings, appSettings, extraAppSettings)
    }
  }
}

resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionApp.id, acr.id, 'acrpull')
  scope: acr
  properties: {
    principalId: functionApp.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalType: 'ServicePrincipal'
  }
}

output acrLoginServer string = '${acr.name}.azurecr.io'
output functionAppPrincipalId string = functionApp.identity.principalId
output functionAppResourceId string = functionApp.id

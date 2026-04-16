// Azure Communication Services — telephony for incoming/outgoing calls
@description('Communication Services resource name')
param name string

resource acs 'Microsoft.Communication/communicationServices@2023-04-01' = {
  name: name
  location: 'global'
  properties: {
    dataLocation: 'unitedstates'
  }
}

output name string = acs.name
output resourceId string = acs.id

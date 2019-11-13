NETWORKS = {'db': {"HOST": "localhost",
                   "USER": "root",
                   "PASSWORD": "password",
                   "NAME": "pub_sub",
                   "PORT": 3306,
                   }
            }

NETWORK_ID = 0

EVENT_SUBSCRIPTIONS = {"OrganizationCreated": [{"name": "", "type": "lambda_arn",
                                                "url": "arn:aws:lambda:"}],

                       "OrganizationModified": [{"name": "", "type": "lambda_arn",
                                                 "url": "arn:aws:"}],

                       "OrganizationDeleted": [{"name": "", "type": "lambda_arn",
                                                "url": "arn:aws"}],
                       "ServiceCreated": [{"name": "", "type": "lambda_arn",
                                           "url": "arn:aws"}],

                       "ServiceMetadataModified": [{"name": "", "type": "lambda_arn",
                                                    "url": "arn:aws:"}],

                       "ServiceTagsModified": [{"name": "", "type": "lambda_arn",
                                                "url": "arn:aws"}],
                       "ServiceDeleted": [{"name": "", "type": "lambda_arn",
                                           "url": "arn:aws"}],

                       "ChannelOpen": [{"name": "", "type": "lambda_arn",
                                        "url": "arn:aws"}],

                       "ChannelOpen": [{"name": "", "type": "lambda_arn",
                                        "url": "arn:aws"}],
                       "ChannelExtend": [{"name": "", "type": "lambda_arn",
                                          "url": "arn:aws"}],

                       "ChannelAddFunds": [{"name": "", "type": "lambda_arn",
                                            "url": "arn:awser"}],
                       "ChannelSenderClaim": [{"name": "", "type": "lambda_arn",
                                               "url": "arn:aws"}],

                       }

WS_PROVIDER = "wss://ropsten.infura.io/"
REGION_NAME=""

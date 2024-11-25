from django.core.management.base import BaseCommand
from django.templatetags.static import static
from django.conf import settings
import urllib.parse
import main.gwallet


class Command(BaseCommand):
    help = "Push updated classes to Google Wallet"

    def handle(self, *args, **options):
        generic_class = main.gwallet.client.genericclass()
        transit_class = main.gwallet.client.transitclass()

        generic_class.update(
            resourceId=f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['railcard_pass_class']}",
            body={
                "id": f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['railcard_pass_class']}",
                "classTemplateInfo": {
                    "cardTemplateOverride": {
                        "cardRowTemplateInfos": [{
                            "oneItem": {
                                "item": {
                                    "firstValue": {
                                        "fields": [{
                                            "fieldPath": "object.imageModulesData['photo']"
                                        }]
                                    }
                                },
                            }
                        }, {
                            "twoItems": {
                                "startItem": {
                                    "firstValue": {
                                        "fields": [{
                                            "fieldPath": "object.textModulesData['traveler-1']"
                                        }]
                                    }
                                },
                                "endItem": {
                                    "firstValue": {
                                        "fields": [{
                                            "fieldPath": "object.textModulesData['traveler-2']"
                                        }]
                                    }
                                }
                            }
                        }, {
                            "twoItems": {
                                "startItem": {
                                    "firstValue": {
                                        "fields": [{
                                            "fieldPath": "object.validTimeInterval.start",
                                            "dateFormat": "DATE_YEAR"
                                        }]
                                    }
                                },
                                "endItem": {
                                    "firstValue": {
                                        "fields": [{
                                            "fieldPath": "object.validTimeInterval.end",
                                            "dateFormat": "DATE_YEAR"
                                        }]
                                    }
                                }
                            },
                        }, {
                            "twoItems": {
                                "startItem": {
                                    "firstValue": {
                                        "fields": [{
                                            "fieldPath": "object.textModulesData['railcard-number']",
                                        }]
                                    }
                                },
                                "endItem": {
                                    "firstValue": {
                                        "fields": [{
                                            "fieldPath": "object.textModulesData['issuer']",
                                        }]
                                    }
                                },
                            }
                        }]
                    },
                    "detailsTemplateOverride": {
                        "detailsItemInfos": [{
                            "item": {
                                "firstValue": {
                                    "fields": [{
                                        "fieldPath": "object.textModulesData['notes']",
                                    }]
                                }
                            },
                        }, {
                            "item": {
                                "firstValue": {
                                    "fields": [{
                                        "fieldPath": "object.linksModuleData.uris['more-info']",
                                    }]
                                }
                            },
                        }]
                    }
                },
                "enableSmartTap": False,
                "securityAnimation": {
                    "animationType": "foilShimmer"
                },
                "multipleDevicesAndHoldersAllowedStatus": "oneUserAllDevices"
            }
        ).execute()
        generic_class.update(
            resourceId=f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['bahncard_pass_class']}",
            body={
                "id": f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['bahncard_pass_class']}",
                "enableSmartTap": False,
                "classTemplateInfo": {
                    "cardTemplateOverride": {
                        "cardRowTemplateInfos": [{
                            "twoItems": {
                                "startItem": {
                                    "firstValue": {
                                        "fields": [{
                                            "fieldPath": "object.textModulesData['card-id']"
                                        }]
                                    }
                                },
                                "endItem": {
                                    "firstValue": {
                                        "fields": [{
                                            "fieldPath": "object.textModulesData['class']"
                                        }]
                                    }
                                }
                            }
                        }, {
                            "oneItem": {
                                "item": {
                                    "firstValue": {
                                        "fields": [{
                                            "fieldPath": "object.textModulesData['traveler-0']"
                                        }]
                                    }
                                }
                            }
                        }],
                    },
                    "detailsTemplateOverride": {
                        "detailsItemInfos": [{
                            "item": {
                                "firstValue": {
                                    "fields": [{
                                        "fieldPath": "object.textModulesData['issued-at']",
                                    }]
                                }
                            },
                        }, {
                            "item": {
                                "firstValue": {
                                    "fields": [{
                                        "fieldPath": "object.linksModuleData.uris['distributor']",
                                    }]
                                }
                            },
                        }]
                    }
                },
                "securityAnimation": {
                    "animationType": "foilShimmer"
                },
                "multipleDevicesAndHoldersAllowedStatus": "oneUserAllDevices"
            }
        ).execute()
        transit_class.update(
            resourceId=f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['train_ticket_pass_class']}",
            body={
                "id": f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['train_ticket_pass_class']}",
                "issuerName": settings.PKPASS_CONF["organization_name"],
                "logo": {
                    "sourceUri": {
                        "uri": urllib.parse.urljoin(settings.EXTERNAL_URL_BASE, static("pass/icon@3x.png")),
                    }
                },
                "transitType": "RAIL",
                "enableSingleLegItinerary": True,
                "enableSmartTap": False,
                "homepageUri": {
                    "uri": settings.EXTERNAL_URL_BASE,
                    "description": "VDVPKPass"
                },
                "securityAnimation": {
                    "animationType": "foilShimmer"
                },
                "multipleDevicesAndHoldersAllowedStatus": "oneUserAllDevices",
                "reviewStatus": "UNDER_REVIEW",
                "customCarriageLabel": {
                    "translatedValues": [{
                        "language": "de",
                        "value": "Zug nr."
                    }],
                    "defaultValue": {
                        "language": "en-gb",
                        "value": "Train nr."
                    }
                }
            }
        ).execute()

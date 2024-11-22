from django.core.management.base import BaseCommand
from django.conf import settings
import main.gwallet


class Command(BaseCommand):
    help = "Push updated classes to Google Wallet"

    def handle(self, *args, **options):
        generic_class = main.gwallet.client.genericclass()

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

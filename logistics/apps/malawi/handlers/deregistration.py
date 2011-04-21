#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

from django.utils.translation import ugettext as _
from rapidsms.conf import settings
from rapidsms.contrib.handlers.handlers.keyword import KeywordHandler
from rapidsms.models import Contact
from logistics.apps.logistics.models import ContactRole, Facility, SupplyPoint, REGISTER_MESSAGE, SupplyPointType
from rapidsms.contrib.locations.models import Location, LocationType
from logistics.apps.malawi import const

NOT_REGISTERED_MESSAGE = "We do not have a record of your registration. Nothing was done."
LEFT_MESSAGE = "You have successfully left the Stock Alert system. Goodbye!"
class HSADeregistrationHandler(KeywordHandler):
    """
    Allow remote users to set their preferred language, by updating the
    ``language`` field of the Contact associated with their connection.
    """

    keyword = "leave"

    def help(self):
        self.handle("")
        
    def handle(self, text):
        if not hasattr(self.msg,'logistics_contact'):
            self.respond(NOT_REGISTERED_MESSAGE)
        else:
            self.msg.logistics_contact.is_active = False
            self.msg.logistics_contact.save()
            if self.msg.logistics_contact.supply_point and \
               self.msg.logistics_contact.supply_point.type == const.hsa_supply_point_type():
                self.msg.logistics_contact.supply_point.deprecate()
            
            self.respond(LEFT_MESSAGE)
        
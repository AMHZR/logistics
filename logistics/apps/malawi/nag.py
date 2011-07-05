from datetime import datetime, timedelta
import logging
import os
from rapidsms.contrib.locations.models import Location
from rapidsms.models import Contact
from logistics.apps.logistics.models import ProductReport, ProductReportType, SupplyPoint,\
    NagRecord, ContactRole, StockRequest, StockRequestStatus
from rapidsms.contrib.messaging.utils import send_message
from logistics.apps.logistics.const import Reports
from logistics.apps.logistics.util import config
from logistics.apps.malawi.util import hsa_supply_points_below

DAYS_BETWEEN_FIRST_AND_SECOND_WARNING = 3
DAYS_BETWEEN_SECOND_AND_THIRD_WARNING = 2
DAYS_BETWEEN_THIRD_AND_FOURTH_WARNING = 2
REC_DAYS_BETWEEN_FIRST_AND_SECOND_WARNING = 3
REC_DAYS_BETWEEN_SECOND_AND_THIRD_WARNING = 4

EM_REPORTING_DAY = 1 # First of the month
WARNING_DAYS = 2 # Advance warning days before report is officially late

def get_non_reporting_hsas(since, report_code=Reports.SOH, location=None):
    """
    Get all HSAs who haven't reported since a passed in date
    """
    hsas = set(hsa_supply_points_below(location))
    reporters = set(x.supply_point for x in \
                    ProductReport.objects.filter(report_type__code=report_code,
                                                 report_date__range=[since,
                                                                     datetime.utcnow()]))
    return hsas - reporters

def nag_hsas_soh(since, location=None):
    """
    Send non-reporting HSAs a predefined nag message.  
    Notify their supervisor if they've been sufficiently delinquent.
    """
    # everyone who didn't report
    hsas = get_non_reporting_hsas(since, Reports.SOH, location)
    
    nags_in_range = NagRecord.objects.filter\
                        (report_date__range=[since, datetime.utcnow()],
                         nag_type=Reports.SOH)
    
    # empty init
    hsa_first_warnings = hsa_second_warnings = hsa_third_warnings = hsa_fourth_warnings = set(())
    now = datetime.utcnow()
    
    # only send nags if we're past the nag period
    if now < since + timedelta(days=WARNING_DAYS):
        # everyone who didn't report - people who have gotten at least 1 nag in the period
        hsa_first_warnings = hsas - set(x.supply_point for x in nags_in_range)
        
    if now < since + timedelta(days=WARNING_DAYS + DAYS_BETWEEN_FIRST_AND_SECOND_WARNING):
        # everyone who hasn't gotten a nag level 2 or higher
        hsa_second_warnings = hsas.intersection(x.supply_point for x in \
                                                nags_in_range.exclude(warning__gte=2))
                    
    if now < since + timedelta(days=WARNING_DAYS + DAYS_BETWEEN_FIRST_AND_SECOND_WARNING +\
                               DAYS_BETWEEN_SECOND_AND_THIRD_WARNING):
        # everyone who hasn't gotten a nag level 3 or higher,
        # minus the folks only getting level 2
        hsa_third_warnings = hsas.intersection(x.supply_point for x in \
                                               nags_in_range.exclude(warning__gte=3)) \
                                - hsa_second_warnings
    if now < since + timedelta(days=WARNING_DAYS + DAYS_BETWEEN_FIRST_AND_SECOND_WARNING +\
                               DAYS_BETWEEN_SECOND_AND_THIRD_WARNING + DAYS_BETWEEN_THIRD_AND_FOURTH_WARNING):
        
        # everyone who hasn't gotten a nag level 4 or higher,
        # minus the folks only getting levels 2 or 3
        hsa_fourth_warnings = hsas.intersection(x.supply_point for x in \
                                                nags_in_range.exclude(warning__gte=4)) \
                                - hsa_second_warnings - hsa_third_warnings
        
    warnings = [
            {'hsas': hsa_first_warnings,
             'number': 1,
             'days': WARNING_DAYS,
             'code': Reports.SOH,
             'message': config.Messages.HSA_NAG_FIRST,
             'flag_supervisor' : False},
            {'hsas': hsa_second_warnings,
             'number': 2,
             'days': DAYS_BETWEEN_FIRST_AND_SECOND_WARNING,
             'code': Reports.SOH,
             'message': config.Messages.HSA_NAG_SECOND,
             'flag_supervisor': False},
            {'hsas': hsa_third_warnings,
             'number': 3,
             'days': DAYS_BETWEEN_SECOND_AND_THIRD_WARNING,
             'code': Reports.SOH,
             'message': config.Messages.HSA_NAG_THIRD,
             'flag_supervisor': True,
             'supervisor_message': config.Messages.HSA_SUPERVISOR_NAG},
            {'hsas': hsa_fourth_warnings,
             'number': 4,
             'days': DAYS_BETWEEN_THIRD_AND_FOURTH_WARNING,
             'code': Reports.SOH,
             'message': config.Messages.HSA_NAG_THIRD, # Same messages
             'flag_supervisor': True,
             'supervisor_message': config.Messages.HSA_SUPERVISOR_NAG}
            ]

    send_nag_messages(warnings)

def nag_hsas_rec(since):
    """
    Send non-reporting HSAs a predefined nag message.  Notify their supervisor if they've been
    sufficiently delinquent.
    """
    hsas = set([x.supply_point for x in StockRequest.objects.filter(status=StockRequestStatus.APPROVED,
                                                                    responded_on__range = [since, datetime.utcnow()])])
    hsa_first_warnings = hsas - set(x.supply_point for x in NagRecord.objects.filter(report_date__range = [since,
                                                                               datetime.utcnow()], nag_type=Reports.REC))
    hsa_second_warnings = hsas.intersection(x.supply_point for x in \
                NagRecord.objects.filter(report_date__range = [since,
                                                               datetime.utcnow()-timedelta(days=DAYS_BETWEEN_FIRST_AND_SECOND_WARNING)],
                                         warning = 1,
                                         nag_type=Reports.REC))
    hsa_third_warnings = hsas.intersection(x.supply_point for x in \
                NagRecord.objects.filter(report_date__range = [since,
                                                               datetime.utcnow()-timedelta(days=DAYS_BETWEEN_SECOND_AND_THIRD_WARNING)],
                                         warning = 2,
                                         nag_type=Reports.REC))
    warnings = [
            {'hsas': hsa_first_warnings,
             'number': 1,
             'days': 0,
             'code': Reports.REC,
             'message': config.Messages.HSA_RECEIPT_NAG_FIRST,
             'flag_supervisor': False},
            {'hsas': hsa_second_warnings,
             'number': 2,
             'days': REC_DAYS_BETWEEN_FIRST_AND_SECOND_WARNING,
             'code': Reports.REC,
             'message': config.Messages.HSA_RECEIPT_NAG_SECOND,
             'flag_supervisor': True,
             'supervisor_message': config.Messages.HSA_RECEIPT_SUPERVISOR_NAG},
             {'hsas': hsa_third_warnings,
             'number': 3,
             'days': REC_DAYS_BETWEEN_SECOND_AND_THIRD_WARNING,
             'code': Reports.REC,
             'message': config.Messages.HSA_RECEIPT_NAG_THIRD,
             'flag_supervisor': True,
             'supervisor_message': config.Messages.HSA_RECEIPT_SUPERVISOR_NAG}
            ]
    send_nag_messages(warnings)


def send_nag_messages(warnings):
    for w in warnings:
        for hsa in w["hsas"]:
            try:
                contact = Contact.objects.get(supply_point=hsa)
                send_message(contact.default_connection, w["message"] % {'hsa': contact.name, 'days': w['days']})
                NagRecord(supply_point=hsa, warning=w["number"],nag_type=w['code']).save()
            except Contact.DoesNotExist:
                logging.error("Contact does not exist for HSA: %s" % hsa.name)
                continue
            if w["flag_supervisor"]:
                try:
                    supervisor = Contact.objects.get(is_active=True,
                                                     role=ContactRole.objects.get(code=config.Roles.HSA_SUPERVISOR),
                                                     supply_point=hsa.supplied_by)
                    send_message(supervisor.default_connection, w["supervisor_message"] % { 'hsa': contact.name})
                except Contact.DoesNotExist:
                    logging.error("Supervisor does not exist for HSA: %s" % hsa.name)


def nag_hsas_ept():
    # For the EPT group, nag them so that they report at least every 30 days
    since = datetime.utcnow() - timedelta(days=30-WARNING_DAYS)
    locs = [Location.objects.get(name=loc) for loc in config.Groups.GROUPS[config.Groups.EPT]]
    for l in locs:
        nag_hsas_soh(since, l)
    nag_hsas_rec(since)

def nag_hsas_em():
    # For the EM group, nag them to report around a (configurable) day of month
    # We send nags at 9am UTC/11am malawi time
    since = datetime.utcnow().replace(day=EM_REPORTING_DAY,
                                      hour=9,minute=0,second=0) - timedelta(days=WARNING_DAYS)
    
    # make sure the date is in the past
    if since > datetime.utcnow():
        try:
            since.replace(month=datetime.utcnow().month - 1) # wraparound?
        except ValueError:
            since.replace(year=datetime.utcnow().year - 1, month=12)
    
    locs = [Location.objects.get(name=loc) for loc in config.Groups.GROUPS[config.Groups.EM]]
    for l in locs:
        nag_hsas_soh(since, l)
    nag_hsas_rec(since)


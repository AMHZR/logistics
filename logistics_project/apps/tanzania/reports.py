from datetime import datetime
from logistics.reports import Colors, PieChartData
from logistics.models import SupplyPoint
from logistics_project.apps.tanzania.models import DeliveryGroups
from logistics_project.apps.tanzania.utils import submitted_to_msd
from models import SupplyPointStatusTypes, SupplyPointStatusValues
from django.utils.translation import ugettext as _
from utils import sps_with_latest_status
from calendar import month_name

class SupplyPointStatusBreakdown(object):

    def __init__(self, facilities=None, year=None, month=None):
        if not (year and month):
            self.month = datetime.utcnow().month
            self.year = datetime.utcnow().year
        else:
            self.month = month
            self.year = year
        if facilities is None:
            facilities = SupplyPoint.objects.filter(type__code="facility")
        self.dg = DeliveryGroups(month=month)

        self.submitted = list(sps_with_latest_status(sps=self.dg.submitting(facilities),
                                                year=self.year, month=self.month,
                                                status_type=SupplyPointStatusTypes.R_AND_R_FACILITY,
                                                status_value=SupplyPointStatusValues.SUBMITTED))

        self.not_submitted = list(sps_with_latest_status(sps=self.dg.submitting(facilities),
                                                 year=self.year, month=self.month,
                                                 status_type=SupplyPointStatusTypes.R_AND_R_FACILITY,
                                                 status_value=SupplyPointStatusValues.NOT_SUBMITTED))

        self.submit_reminder_sent = list(sps_with_latest_status(sps=self.dg.submitting(facilities),
                                                 year=self.year, month=self.month,
                                                 status_type=SupplyPointStatusTypes.R_AND_R_FACILITY,
                                                 status_value=SupplyPointStatusValues.REMINDER_SENT))

        self.submit_not_responding = list(set(self.submit_reminder_sent) - set(self.submitted) - set(self.not_submitted))

        self.delivery_received = list(sps_with_latest_status(sps=self.dg.delivering(facilities),
                                                 year=self.year, month=self.month,
                                                 status_type=SupplyPointStatusTypes.DELIVERY_FACILITY,
                                                 status_value=SupplyPointStatusValues.RECEIVED))
                                 
        self.delivery_not_received = list(sps_with_latest_status(sps=self.dg.delivering(facilities),
                                                 year=self.year, month=self.month,
                                                 status_type=SupplyPointStatusTypes.DELIVERY_FACILITY,
                                                 status_value=SupplyPointStatusValues.NOT_RECEIVED))

        self.delivery_reminder_sent = list(sps_with_latest_status(sps=self.dg.delivering(facilities),
                                                 year=self.year, month=self.month,
                                                 status_type=SupplyPointStatusTypes.DELIVERY_FACILITY,
                                                 status_value=SupplyPointStatusValues.REMINDER_SENT))

        self.delivery_not_responding = list(set(self.delivery_reminder_sent) - set(self.delivery_received) - set(self.delivery_not_received))

        self.soh_not_responding = list(sps_with_latest_status(sps=facilities, year=self.year, month=self.month,
                                                              status_type=SupplyPointStatusTypes.SOH_FACILITY,
                                                              status_value=SupplyPointStatusValues.REMINDER_SENT))


        self._submission_chart = None

    def submission_chart(self):
        graph_data = [
                {"display": _("Submitted"),
                 "value": len(self.submitted),
                 "color": Colors.GREEN,
                 "description": "(%s) Submitted (%s %s)" % \
                    (len(self.submitted), month_name[self.month], self.year)
                },
                {"display": _("Haven't Submitted"),
                 "value": len(self.not_submitted),
                 "color": Colors.RED,
                 "description": "(%s) Haven't Submitted (%s %s)" % \
                    (len(self.not_submitted), month_name[self.month], self.year)
                },
                {"display": _("Didn't Respond"),
                 "value": len(self.submit_not_responding),
                 "color": Colors.PURPLE,
                 "description": "(%s) Didn't Respond (%s %s)" % \
                    (len(self.submit_not_responding), month_name[self.month], self.year)
                }
            ]
        self._submission_chart = PieChartData(_("R&R Submission Summary") + " (%s %s)" % (month_name[self.month], self.year), graph_data)
        return self._submission_chart

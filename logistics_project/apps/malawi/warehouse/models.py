from django.db import models
from logistics.warehouse_models import ReportingModel

class MalawiWarehouseModel(ReportingModel):
    
    class Meta:
        abstract = True
        app_label = "malawi"

class ProductAvailabilityData(MalawiWarehouseModel):
    """
    This will be used to generate the "current stock status" table,
    as well as anything that needs to compute percent with / without 
    stock, oversupplied, undersupplied, etc.
    """
    # Dashboard: current stock status
    # Resupply Qts: % with stockout
    # Stock status: all
    product = models.ForeignKey('logistics.Product')
    total = models.PositiveIntegerField(default=0)
    managed = models.PositiveIntegerField(default=0)
    with_stock = models.PositiveIntegerField(default=0)
    under_stock = models.PositiveIntegerField(default=0)
    over_stock = models.PositiveIntegerField(default=0)
    without_stock = models.PositiveIntegerField(default=0)
    without_data = models.PositiveIntegerField(default=0)
    
    # unfortunately, we need to separately keep these for the aggregates
    managed_and_with_stock = models.PositiveIntegerField(default=0)
    managed_and_under_stock = models.PositiveIntegerField(default=0)
    managed_and_over_stock = models.PositiveIntegerField(default=0)
    managed_and_without_stock = models.PositiveIntegerField(default=0)
    managed_and_without_data = models.PositiveIntegerField(default=0)
    
    @property
    def managed_and_with_good_stock(self):
        return self.managed_and_with_stock - self.managed_and_over_stock \
            - self.managed_and_under_stock
    
class ProductAvailabilityDataSummary(MalawiWarehouseModel):
    """
    Aggregates the product availability up to the supply point level,
    no longer dealing with individual products, but just whether anything
    is managed and anything manaegd is stocked out.
    """
    # Sidebar: % with stockout
    # Dashboard: % with stockout
    total = models.PositiveIntegerField(default=0)
    manages_anything = models.PositiveIntegerField(default=0)
    with_any_stockout = models.PositiveIntegerField(default=0)

def _fmt_pct(num, denom):
    return "%.2f%%" % (float(num) / (float(denom) or 1) * 100)    

class ReportingRate(MalawiWarehouseModel):
    """
    Records information used to calculate the reporting rates
    """
    # Dashboard: Reporting Rates
    # Reporting Rates: all
    total = models.PositiveIntegerField(default=0)
    reported = models.PositiveIntegerField(default=0)
    on_time = models.PositiveIntegerField(default=0)
    complete = models.PositiveIntegerField(default=0)
    
    @property
    def late(self): 
        return self.reported - self.on_time
    
    @property
    def missing(self): 
        return self.total - self.reported
    
    # report helpers
    @property
    def pct_reported(self): return _fmt_pct(self.reported, self.total)
    
    @property
    def pct_on_time(self):  return _fmt_pct(self.on_time, self.total)
    
    @property
    def pct_late(self):     return _fmt_pct(self.late, self.total)
    
    @property
    def pct_missing(self):  return _fmt_pct(self.missing, self.total)
    
    @property
    def pct_complete(self): return _fmt_pct(self.complete, self.total)
        
            
class TimeTracker(MalawiWarehouseModel):
    """
    For keeping track of a time between two events. Currently used for 
    lead times. We keep the number of data points around so that we can
    include multiple values into an average.
    """
    # Lead times: all 
    type = models.CharField(max_length=10) # e.g. ord-ready
    total = models.PositiveIntegerField(default=0) # number of contributions to this
    time_in_seconds = models.PositiveIntegerField(default=0)
    
class OrderRequest(MalawiWarehouseModel):
    """
    Each time an order is made, used to count both regular and emergency
    orders for a particular month.
    """
    # Emergency Orders: all
    product = models.ForeignKey('logistics.Product')
    total = models.PositiveIntegerField(default=0)
    emergency = models.PositiveIntegerField(default=0)
    
    
class OrderFulfillment(MalawiWarehouseModel):
    """
    Each time an order is fulfilled, add up the amount requested and
    the amount received so we can determine order fill rates.
    """
    # Order Fill Rates: all 
    product = models.ForeignKey('logistics.Product')
    total = models.PositiveIntegerField(default=0)
    quantity_requested = models.PositiveIntegerField(default=0)
    quantity_received = models.PositiveIntegerField(default=0)

# Other:
# User Profiles (no changes needed)
# HSA (no changes needed)
# Consumption Profiles (likely changes needed, to be clarified)
# Resupply Qts: anything needed? TBD
# Alerts: TBD
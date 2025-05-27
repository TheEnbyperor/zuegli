import pytz
import datetime

class HZPPException(Exception):
    pass

EURO_SWITCHOVER = pytz.timezone("Europe/Zagreb").localize(datetime.datetime(2023, 1, 1, 0, 0, 0))

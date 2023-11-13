import pytz
from datetime import timedelta, datetime, timezone


class TimeOperator:


    def generate_current_timestamp(self):
        """
        Generate a current Timestamp in UTC
        """
        dt = datetime.now(timezone.utc)
        utc_timestamp = dt.astimezone(pytz.utc).timestamp()

        return int(utc_timestamp*1000)

    def generate_reverse_minutes(self, minutes):
        """
        Generate a Timestamp in UTC - minutes
        """
        df = datetime.now().astimezone(pytz.utc) - timedelta(minutes=minutes)
        utc_timezone = df.astimezone(pytz.utc).timestamp()

        return int(utc_timezone*1000)

    def generate_reverse_days(self, days):
        """
        Generate reverse day
        """
        df = datetime.now().astimezone(pytz.utc) - timedelta(days=days)
        utc_timezone = df.astimezone(pytz.utc).timestamp()

        return int(utc_timezone*1000)

    def period_to_timestamp(self, start, interval, time_to_add):
        """
        Convert period to timestamp
        """
        if interval == "1m" or interval == "3m" or interval == "5m" or interval == "15m" or interval == "30m":
            final_timestamp = datetime.fromtimestamp(start/1000) + timedelta(minutes=time_to_add)
            return int(final_timestamp.timestamp()*1000)
        elif interval == "1h" or interval == "2h" or interval == "4h" or interval == "6h" or interval == "8h" or \
                interval == "12h":
            final_timestamp = datetime.fromtimestamp(start/1000) + timedelta(hours=time_to_add)
            return int(final_timestamp.timestamp()*1000)
        elif interval == "1d" or interval == "3d":
            final_timestamp = datetime.fromtimestamp(start/1000) + timedelta(days=time_to_add)
            return int(final_timestamp.timestamp()*1000)
        elif interval == "1w":
            final_timestamp = datetime.fromtimestamp(start/1000) + timedelta(weeks=time_to_add)
            return int(final_timestamp.timestamp()*1000)
        else:
            print(f"Incorrect interval to convert to timestamp: {interval}")

    def interval_to_seconds(self, interval, extra_delay) -> int:
        """
        Convert interval to seconds
        """
        if interval == "1m":
            return int(60*extra_delay)
        elif interval == "3m":
            return int(60*3 * extra_delay)
        elif interval == "5m":
            return int(60*5 * extra_delay)
        elif interval == "15m":
            return int(60*15 * extra_delay)
        elif interval == "30m":
            return int(60*30 * extra_delay)
        elif interval == "1h":
            return int(60*60 * extra_delay)
        elif interval == "2h":
            return int(60*60*2 * extra_delay)
        elif interval == "4h":
            return int(60*60*4 * extra_delay)
        elif interval == "6h":
            return int(60*60*6 * extra_delay)
        elif interval == "8h":
            return int(60*60*8 * extra_delay)
        elif interval == "12h":
            return int(60*60*12 * extra_delay)
        elif interval == "1d":
            return int(86400 * extra_delay)
        elif interval == "3d":
            return int(86400*3 * extra_delay)
        elif interval == "1w":
            return int(86400*7 * extra_delay)
        else:
            return int(extra_delay)
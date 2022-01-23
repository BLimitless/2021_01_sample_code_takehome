from collections import defaultdict
from datetime import datetime
from typing import List, Optional

import pandas as pd
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel

from energy_client import EnergyClient, MeasureType, Timeseries, DataPoint


def get_first_moment_of_month(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class Fault(BaseModel):  # Not used for the at-home challenge
    """
    This model represents a Faulty measure, and is used to adjust the savings
    of a measure over a specific time range. For a given measure, you can
    assume that there are no overlapping faults.
    """

    name: str
    fault_factor: float = 1
    start: datetime
    end: datetime


class Measure(BaseModel):
    """
    This model represents an Energy Efficiency Measure, including a time range that
    describes when that measure was implemented / active on a building.
    """

    name: str
    measure_type: MeasureType
    faults: Optional[List[Fault]]  # not used for the at-home challenge
    start: datetime
    end: datetime

    def get_measure_savings_dataframe(self) -> pd.DataFrame:
        '''
        Returns dataframe of energy savings, with columns for Index, Values [savings], Month, Day, Minute.

        This dataframe can then be used for easy analysis, e.g. groupby.month, or single timestamp matching
        '''
        full_year = EnergyClient.get_measure_expected_energy_savings_for_generic_year(self.measure_type)
        timestamps = [item.timestamp for item in full_year]
        values = [item.value for item in full_year]

        df = pd.DataFrame({'Timestamps': timestamps, 'Values': values})
        df['Month'] = df['Timestamps'].apply(lambda x: x.month)
        df['Day'] = df['Timestamps'].apply(lambda x: x.day)
        df['Minute'] = df['Timestamps'].apply(lambda x: x.minute)

        return df

    # Implement this function for the at home challenge
    def get_savings_for_date_range(self, start: datetime, end: datetime) -> Timeseries:
        """
        Takes in a start and end date and returns the expected measure savings. For example,
        when this function is called from `get_past_and_future_year_of_monthly_energy_usage`,
        it should return timeseries data that matches the shape of the building energy usage
        data.

        A correct solution will account for whether the measure is active or not during the
        given time range.
        """
        current_time: datetime
        savings: Timeseries

        df = self.get_measure_savings_dataframe()
        # Loop through all timestamps that should have savings, append them to list if:
        current_time = start
        savings = []
        while(current_time < end):
            # if the measure is functional
            if(self.start <= current_time < self.end):
                savings.append(
                    DataPoint(timestamp=current_time,
                              value=df.loc[(df['Month']==current_time.month) &
                                           (df['Day']==current_time.day) &
                                           (df['Minute']==current_time.minute),
                                           'Values'].iloc[0]
                              )
                )
            else:
                savings.append(DataPoint(timestamp=current_time, value=0))
            current_time += relativedelta(minutes=15)
        return savings


class Building(BaseModel):
    """
    This model represents the overall Building in which we are looking to reduce energy usage.
    Each Building has a list of Energy Efficiency Measures which provide energy savings over
    a given time frame.
    """

    name: str
    measures: Optional[List[Measure]]

    def get_past_and_future_year_of_monthly_energy_usage(
        self, include_measure_savings: Optional[bool] = False
    ) -> Timeseries:
        now = get_first_moment_of_month(datetime.now())
        start = now - relativedelta(years=1)
        end = now + relativedelta(years=1)

        quarter_hourly_usage_data = EnergyClient.get_building_expected_energy_usage(
            start, end
        )

        if include_measure_savings:
            # this code will break until you implement `measure.get_savings_for_date_range`
            savings_by_measure = [
                measure.get_savings_for_date_range(start, end)
                for measure in self.measures
            ]

            for usage_data, *savings_data_args in zip(
                quarter_hourly_usage_data, *savings_by_measure
            ):
                for savings_data in savings_data_args:
                    usage_data.value -= savings_data.value

        monthly_usage = defaultdict(int)
        for quarter_hour_usage in quarter_hourly_usage_data:
            month_timestamp = get_first_moment_of_month(quarter_hour_usage.timestamp)
            monthly_usage[month_timestamp] += quarter_hour_usage.value

        return [DataPoint(timestamp=ts, value=v) for ts, v in monthly_usage.items()]

import unittest
from datetime import datetime

import pandas as pd
from dateutil.relativedelta import relativedelta
from models import Building, Measure, MeasureType, get_first_moment_of_month, DataPoint

start_of_month = get_first_moment_of_month(datetime.now())


# These fixtures are provided as an overview of what a building setup could look like.
# Note that the dates on which measures are active do not necessarily overlap. Feel
# free to add more fixtures as you build out your own tests.
building_1 = Building(
    name="Building 1",
    measures=[
        Measure(
            name="Building 1 - Measure 1",
            measure_type=MeasureType.SCHEDULING,
            start=datetime(year=2020, month=6, day=1),
            end=datetime(year=2021, month=1, day=1),
        ),
        Measure(
            name="Building 1 - Measure 2",
            measure_type=MeasureType.SAT_RESET,
            start=datetime(year=2021, month=8, day=7),
            end=datetime(year=2021, month=12, day=1),
        ),
    ],
)
building_2 = Building(
    name="Building 2",
    measures=[
        Measure(
            name="Building 2 - Measure 1",
            measure_type=MeasureType.LED_RETROFIT,
            start=datetime(year=2022, month=6, day=1),
            end=datetime(year=2023, month=1, day=1),
        )
    ],
)

building_partial_month_coverage = Building(
    name="Building Partial Coverage",
    measures=[
        Measure(
            name="Measure Partial Coverage",
            measure_type=MeasureType.SAT_RESET,
            start=datetime(
                year=start_of_month.year,
                month=start_of_month.month,
                day=6,
            ),
            end=datetime(
                year=start_of_month.year,
                month=start_of_month.month,
                day=15,
            ),
        )
    ],
)

building_full_month_coverage = Building(
    name="Building Full Coverage",
    measures=[
        Measure(
            name="Measure Full Coverage",
            measure_type=MeasureType.SAT_RESET,
            start=start_of_month,
            end=start_of_month + relativedelta(months=1),
        )
    ],
)


class TestChallengeTask(unittest.TestCase):

    # this should pass once the Challenge task has been completed correctly
    def test_get_past_and_future_year_of_monthly_energy_usage_with_measures(self):
        for building in (building_1, building_2):
            result_with_measures = (
                building.get_past_and_future_year_of_monthly_energy_usage(
                    include_measure_savings=True
                )
            )
            result_without_measures = (
                building.get_past_and_future_year_of_monthly_energy_usage()
            )
            for with_measures, without_measures in zip(
                result_with_measures, result_without_measures
            ):
                ts = with_measures.timestamp
                if any(
                    get_first_moment_of_month(measure.start) <= ts < measure.end
                    for measure in building.measures
                ):
                    self.assertLess(with_measures.value, without_measures.value)
                else:
                    self.assertEqual(with_measures.value, without_measures.value)

    # this should pass once the Challenge task has been completed correctly
    def test_partial_month_coverage(self):
        result_partial_coverage = building_partial_month_coverage.get_past_and_future_year_of_monthly_energy_usage(
            include_measure_savings=True
        )
        result_full_coverage = building_full_month_coverage.get_past_and_future_year_of_monthly_energy_usage(
            include_measure_savings=True
        )

        for partial_coverage, full_coverage in zip(
            result_partial_coverage, result_full_coverage
        ):
            ts = partial_coverage.timestamp
            if ts.year == start_of_month.year and ts.month == start_of_month.month:
                self.assertLess(full_coverage.value, partial_coverage.value)

    def test_get_measure_savings_dataframe(self):
        # several tests to make sure method returning dataframe of savings is working
        # bundling as large test function to avoid repeating the same for loops and method call over and over
        # there's probably a way to do that with @fixture or something and split up the tests, but I don't know it.
        for building in (building_1, building_2):
            for measure in building.measures:
                df = measure.get_measure_savings_dataframe()
                print('Current df looks like:')
                print(df.head())

                # make sure is DataFrame
                assert type(df) is pd.DataFrame, 'Get measure savings dataframe did not return dataframe'

                # make sure has right columns
                cols = str.split('Timestamps Values Month Day Minute', sep=' ')
                for col in df.columns:
                    if(col not in cols):
                        assert False, 'Unexpected column returned'
                for col in cols:
                    if(col not in df.columns):
                        assert False, 'Dataframe missing column'

                # make sure length is correct
                self.assertEqual(len(df.index),8760*4, 'Length incorrect')

    def test_get_measure_savings_for_date_range(self):
        # write this test for the at-home challenge
        test_start = datetime(year=2019, month=1, day=1)
        test_stop = datetime(year=2022, month=12, day=31)

        for building in (building_1, building_2):
            for measure in building.measures:
                result = measure.get_savings_for_date_range(test_start, test_stop)
                assert type(result) is list, 'Result not Timeseries'
                assert type(result[0]) is DataPoint, 'First entry in result not DataPoint'
                assert type(result[0].value is float), 'First value in Result is not float'
                assert type(result[0].timestamp is datetime), 'First timestamp in Result is not datetime'
                assert result[0].timestamp >= test_start, 'First timestamp is < test start'
                assert result[-1].timestamp < test_stop, 'Last timestamp is >= test stop'
                '''
                Couldn't figure out simple way to test that if a measure's off there's no savings,
                but all tests pass and the method code is pretty simple so stopping. This was fun! 
                '''
        assert True


if __name__ == "__main__":
    unittest.main()

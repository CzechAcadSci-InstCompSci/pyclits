"""
Integration tests for base class - DataField.
"""

import os
import unittest
from datetime import datetime

import numpy as np
import pytest
import xarray as xr
from pyclits.geofield import DataField

from . import TestHelperTempSave


class TestDataField(TestHelperTempSave):
    """
    Test DataField basic methods.
    """

    CORRECT_LATS = np.array(
        [
            30.0,
            32.5,
            35.0,
            37.5,
            40.0,
            42.5,
            45.0,
            47.5,
            50.0,
            52.5,
            55.0,
            57.5,
            60.0,
            62.5,
            65.0,
            67.5,
            70.0,
        ]
    )

    CORRECT_LONS = np.array(
        [
            350.0,
            352.5,
            355.0,
            357.5,
            0.0,
            2.5,
            5.0,
            7.5,
            10.0,
            12.5,
            15.0,
            17.5,
            20.0,
            22.5,
            25.0,
            27.5,
            30.0,
            32.5,
            35.0,
            37.5,
            40.0,
        ]
    )

    SELECTED_LATS = np.array([32.5, 35.0, 37.5, 40.0])
    SELECTED_LONS = np.array([17.5, 20.0, 22.5, 25.0, 27.5])
    SELECTED_LONS_PRIME_MERIDIAN = np.array([357.5, 0.0, 2.5])

    COS_WEIGHTS = np.array(
        [
            0.93060486,
            0.91836346,
            0.90507019,
            0.89070385,
            0.87523965,
            0.85864855,
            0.84089642,
            0.82194295,
            0.80174036,
            0.78023165,
            0.75734829,
            0.73300724,
            0.70710678,
            0.67952087,
            0.65009096,
            0.61861412,
            0.58482488,
        ]
    )

    def load_df(self):
        """
        Loads testing dataset: temperature at sigma 0.995 level from NCEP/NCAR
        reanalysis.
        """
        return DataField.load_nc(
            os.path.join(self.test_data_path, "air.sig995.nc")
        )

    def test_load_save(self):
        df = self.load_df()
        filename = os.path.join(self.temp_dir, "test.nc")
        df.save(filename)

        self.compare_nc_files(
            os.path.join(self.test_results_path, "load_save_result.nc"),
            filename,
        )

    def test_properties(self):
        df = self.load_df()

        self.assertTrue(hasattr(df, "preprocessing_steps"))
        self.assertTrue(hasattr(df, "_copy_attributes"))
        self.assertTrue(hasattr(df, "__constructor__"))
        self.assertTrue(hasattr(df, "__finalize__"))

        self.assertEqual(df.num_nans, 0)
        self.assertEqual(len(df.process_steps), 1)

        np.testing.assert_equal(df.lats, self.CORRECT_LATS)
        np.testing.assert_equal(df.lons, self.CORRECT_LONS)
        self.compare_time_range(
            df.time, datetime(1990, 1, 1), datetime(2000, 1, 1)
        )
        self.assertTrue(
            df.spatial_dims
            == (self.CORRECT_LATS.shape[0], self.CORRECT_LONS.shape[0])
        )
        self.assertListEqual(df.dims_not_time, ["lats", "lons"])
        for (k1, v1), (k2, v2) in zip(
            df.coords_not_time.items(),
            {
                k: v.values for k, v in df.data.coords.items() if k != "time"
            }.items(),
        ):
            self.assertEqual(k1, k2)
            np.testing.assert_equal(v1, v2)

    def test_iterate(self):
        df = self.load_df()
        for name, it in df.iterate(return_as="datafield"):
            self.assertTrue(isinstance(it, DataField))
            self.assertTrue(isinstance(name, dict))
            self.assertTupleEqual(it.shape, (df.shape[0], 1, 1))
            self.assertEqual(len(it.process_steps), 2)

        for name, it in df.iterate(return_as="xr"):
            self.assertTrue(isinstance(it, xr.DataArray))
            self.assertTrue(isinstance(name, tuple))
            self.assertTupleEqual(it.shape, (df.shape[0], 1))

        with pytest.raises(ValueError):
            for name, it in df.iterate(return_as="abcde"):
                pass

    def test_rolling(self):
        df = self.load_df()
        rolled = df.rolling(roll_over=20, dropnans=False, inplace=False)
        self.assertTrue(isinstance(rolled, DataField))
        self.assertTupleEqual(rolled.shape, df.shape)
        self.assertEqual(len(rolled.process_steps), 2)
        df.rolling(roll_over=20, dropnans=False, inplace=True)
        xr.testing.assert_allclose(df.data, rolled.data)

        df = self.load_df()
        rolled = df.rolling(roll_over=20, dropnans=True, inplace=False)
        self.assertTrue(isinstance(rolled, DataField))
        self.assertTupleEqual(rolled.shape[1:], df.shape[1:])
        self.assertEqual(len(rolled.process_steps), 2)
        df.rolling(roll_over=20, dropnans=True, inplace=True)
        xr.testing.assert_allclose(df.data, rolled.data)

    def test_shift_lons(self):
        df = self.load_df()
        # shift to -180 -- 179
        shifted = df.shift_lons_to_minus_notation(df.data)
        self.assertTrue(
            (shifted.lons <= 180).all() and (shifted.lons >= -180).all()
        )

        # shift back
        shifted_back = df.shift_lons_to_all_east_notation(shifted)
        self.assertTrue(
            (shifted_back.lons >= 0).all() and (shifted_back.lons <= 360).all()
        )

        # final check - original opened data should be the same as shifted back
        xr.testing.assert_equal(df.data, shifted_back)

    def test_select_date(self):
        df = self.load_df()
        selected_df = df.select_date(
            datetime(1991, 5, 20), datetime(1992, 3, 7), inplace=False
        )
        self.compare_time_range(
            selected_df.time, datetime(1991, 6, 1), datetime(1992, 3, 1)
        )
        self.assertEqual(len(selected_df.process_steps), 2)

    def test_select_months(self):
        df = self.load_df()
        # select jan, july and august
        jja_months = [1, 7, 8]
        jja_df = df.select_months(months=jja_months, inplace=False)
        # test that all datetimes have months only in the allowed range
        self.assertTrue(
            all(
                jja_df.time.astype("datetime64[D]")[time].item().month
                in jja_months
                for time in range(jja_df.time.shape[0])
            )
        )
        self.assertEqual(len(jja_df.process_steps), 2)

    def test_select_lat_lon(self):
        df = self.load_df()
        lats_cut = [32, 41.32]
        lons_cut = [17.00001, 28]
        selected_df = df.select_lat_lon(lats_cut, lons_cut, inplace=False)
        np.testing.assert_equal(selected_df.lats, self.SELECTED_LATS)
        np.testing.assert_equal(selected_df.lons, self.SELECTED_LONS)
        self.assertEqual(len(selected_df.process_steps), 3)

    def test_select_lat_lon_through_prime_meridian(self):
        df = self.load_df()
        lats_cut = [32, 41.32]
        lons_cut = [356, 4.12]
        selected_df = df.select_lat_lon(lats_cut, lons_cut, inplace=False)
        np.testing.assert_equal(selected_df.lats, self.SELECTED_LATS)
        np.testing.assert_equal(
            selected_df.lons, self.SELECTED_LONS_PRIME_MERIDIAN
        )
        self.assertEqual(len(selected_df.process_steps), 3)

    def test_cos_weights(self):
        df = self.load_df()
        np.testing.assert_allclose(df.cos_weights[:, 0], self.COS_WEIGHTS)

    def test_interpolate_temporal_nans(self):
        df = self.load_df()
        interpd_df = df.interpolate_temporal_nans(method="cubic", inplace=False)
        self.assertEqual(len(interpd_df.process_steps), 2)
        self.assertTrue(
            interpd_df.spatial_dims
            == (self.CORRECT_LATS.shape[0], self.CORRECT_LONS.shape[0])
        )
        df.interpolate_temporal_nans(method="cubic", inplace=True)
        xr.testing.assert_allclose(df.data, interpd_df.data)

    def test_temporal_resample(self):
        df = self.load_df()
        resampled_df = df.temporal_resample(
            resample_to="3M", function=np.nanmean, inplace=False
        )
        self.assertEqual(len(resampled_df.process_steps), 2)

        # assert only time dimension got resampled - no changes to spatial dims
        self.assertTrue(
            resampled_df.spatial_dims
            == (self.CORRECT_LATS.shape[0], self.CORRECT_LONS.shape[0])
        )
        df.temporal_resample(
            resample_to="3M", function=np.nanmean, inplace=True
        )
        xr.testing.assert_allclose(df.data, resampled_df.data)

    def test_dt(self):
        df = self.load_df()
        with pytest.raises(ValueError):
            df.dt(units="fail_please")
        self.assertEqual(df.dt(units="seconds"), 2629440.0)
        self.assertEqual(df.dt(units="hours"), 730.4)
        self.assertAlmostEqual(df.dt(units="days"), 30.43333333)
        self.assertAlmostEqual(df.dt(units="months"), 1.0, places=3)
        self.assertAlmostEqual(df.dt(units="years"), 0.08332363)

    def test_spatial_resample(self):
        df = self.load_df()
        resampled_df = df.spatial_resample(
            d_lat=5, d_lon=5, method="linear", inplace=False
        )
        self.assertEqual(len(resampled_df.process_steps), 2)

        # assert that time dimension did not change
        self.compare_time_range(
            df.time, datetime(1990, 1, 1), datetime(2000, 1, 1)
        )
        df.spatial_resample(d_lat=5, d_lon=5, method="linear", inplace=True)
        xr.testing.assert_allclose(df.data, resampled_df.data)

    def test_deseasonalise(self):
        df = self.load_df()
        deseas_df, mean_df, std_df, trend_df = df.deseasonalise(
            standardise=True, detrend_data=True, inplace=False
        )
        self.assertEqual(len(deseas_df.process_steps), 4)

        # assert that time dimension did not change
        self.compare_time_range(
            df.time, datetime(1990, 1, 1), datetime(2000, 1, 1)
        )
        mean_df2, std_df2, trend_df2 = df.deseasonalise(
            standardise=True, detrend_data=True, inplace=True
        )
        xr.testing.assert_allclose(deseas_df.data, df.data)
        xr.testing.assert_allclose(mean_df, mean_df2)
        xr.testing.assert_allclose(std_df, std_df2)
        xr.testing.assert_allclose(trend_df, trend_df2)

    def test_pca(self):
        df = self.load_df()
        pcs, eofs, var = df.pca(n_comps=5)
        self.assertTrue(isinstance(pcs, xr.DataArray))
        self.assertTrue(isinstance(eofs, xr.DataArray))
        self.assertTrue(isinstance(var, np.ndarray))
        self.assertTupleEqual(pcs.shape, (df.time.shape[0], 5))
        self.assertTupleEqual(
            eofs.shape, (5, df.lats.shape[0], df.lons.shape[0])
        )
        self.assertTupleEqual(var.shape, (5,))
        self.assertTrue(isinstance(df.pca_mean, xr.DataArray))

    def test_parametric_phase(self):
        for wrapped in [True, False]:
            df = self.load_df()
            param_phase_df = df.parametric_phase(
                central_period=1.0,
                window=0.25,
                units="years",
                return_wrapped=wrapped,
                inplace=False,
            )
            self.assertEqual(len(param_phase_df.process_steps), 2)
            self.assertDictContainsSubset(
                {
                    "parametric_phase_period": 1.0,
                    "parametric_phase_window": 0.25,
                    "parametric_phase_units": "years",
                },
                param_phase_df.data.attrs,
            )

            self.compare_time_range(
                df.time, datetime(1990, 1, 1), datetime(2000, 1, 1)
            )
            df.parametric_phase(
                central_period=1.0,
                window=0.25,
                units="years",
                return_wrapped=wrapped,
                inplace=True,
            )
            xr.testing.assert_allclose(df.data, param_phase_df.data)

    def test_ccwt(self):
        for return_as in [
            "raw",
            "amplitude",
            "amplitude_regressed",
            "phase_wrapped",
            "phase_unwrapped",
            "reconstruction",
            "reconstruction_regressed",
        ]:
            df = self.load_df()
            ccwt_df = df.ccwt(
                central_period=1.0,
                units="years",
                return_as=return_as,
                inplace=False,
            )
            self.assertEqual(len(ccwt_df.process_steps), 2)
            self.assertDictContainsSubset(
                {
                    "CCWT_period": 1.0,
                    "CCWT_units": "years",
                },
                ccwt_df.data.attrs,
            )

            self.compare_time_range(
                df.time, datetime(1990, 1, 1), datetime(2000, 1, 1)
            )
            df.ccwt(
                central_period=1.0,
                units="years",
                return_as=return_as,
                inplace=True,
            )
            xr.testing.assert_allclose(df.data, ccwt_df.data)


if __name__ == "__main__":
    unittest.main()

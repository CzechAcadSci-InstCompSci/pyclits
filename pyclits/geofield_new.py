"""
Base class for any geo spatio-temporal field. Represented as xarray.DataArray.

(c) Nikola Jajcay
"""

from datetime import date, datetime

import numpy as np
import pandas as pd
import xarray as xr


class DataField:
    """
    Class holds spatio-temporal geophysical field.
    """

    @classmethod
    def load_nc(cls, filename, variable=None):
        """
        Loads NetCDF file using xarray.

        :param filename: filename of nc file
        :type filename: str
        :param variable: which variable to load
        :type variable: str
        """
        try:
            loaded = xr.open_dataarray(filename)
        except ValueError:
            assert variable is not None
            loaded = xr.open_dataset(filename)
            loaded = loaded[variable]
        return cls(loaded)

    def __init__(self, data):
        """
        :param data: spatio-temporal data
        :type data: xr.DataArray
        """
        assert isinstance(
            data, xr.DataArray
        ), f"Data has to be xr.DataArray, got {type(data)}"

        self.data = data
        # rename coords to unified format
        self._rename_coords("la", "lats")
        self._rename_coords("lo", "lons")
        self._rename_coords("time", "time")
        # sort by lats and time, NOT lons
        self.data = self.data.sortby(self.data.lats)
        self.data = self.data.sortby(self.data.time)

        if np.any(self.data.lons.values < 0.0):
            print("**WARNING: found negative longitude, shifting to 0-360")
            self.data = self.shift_lons_to_all_east_notation(self.data)

    def _rename_coords(self, substring, new_name):
        """
        Rename coordinate in xr.DataArray to new_name.

        :param substring: substring for old coordinate name to match
        :type substring: str
        :param new_name: new name for matched coordinate
        :type new_name: str
        """
        for coord in self.data.coords:
            if substring in coord:
                old_name = coord
                break
        self.data = self.data.rename({old_name: new_name})

    @staticmethod
    def _update_coord_attributes(old_coord, new_coord, new_units=None):
        """
        Update coordinate attributes after shifting, resampling, etc.

        :param old_coord: old coordinate with attributes
        :type old_coord: xr.DataArray
        :param new_coord: new coordinate to fill attributes to
        :type new_coord: xr.DataArray
        :param new_units: new unit name if desired
        :type new_units: str|None
        :return: coordinate with attributes
        :rtype: xr.DataArray
        """
        new_attrs = old_coord.attrs
        # change range if present in attributes
        if "actual_range" in new_attrs:
            new_attrs["actual_range"] = [
                new_coord.values.min(),
                new_coord.values.max(),
            ]
        if "units" in new_attrs and new_units is not None:
            new_attrs["units"] = new_units

        new_coord.attrs = new_attrs
        return new_coord

    def shift_lons_to_minus_notation(self, dataarray):
        """
        Shift longitude coordinate to minus notation, i.e. -180E -- 179E.
        Longitudes less than 0 are considered W.

        :param dataarray: geospatial field with longitudes as coordinates
        :type dataarray: xr.DataArray|xr.Dataset
        :return: field with shifted coords to -180 -- 179
        :rtype: xr.DataArray|xr.Dataset
        """
        shifted = dataarray.assign_coords(
            lons=((dataarray.lons + 180) % 360) - 180
        )

        shifted["lons"] = self._update_coord_attributes(
            dataarray.lons, shifted.lons, new_units="degrees_east_west"
        )
        return shifted

    def shift_lons_to_all_east_notation(self, dataarray):
        """
        Shift longitude coordinate to 0-360 notation. Longitudes > 180 are
        considered W.

        :param dataarray: geospatial field with longitudes as coordinates
        :type dataarray: xr.DataArray|xr.Dataset
        :return: field with shifted coords to 0 - 360
        :rtype: xr.DataArray|xr.Dataset
        """
        shifted = dataarray.assign_coords(lons=(dataarray.lons + 360) % 360)

        shifted["lons"] = self._update_coord_attributes(
            dataarray.lons, shifted.lons, new_units="degrees_east"
        )
        return shifted

    @property
    def time(self):
        return self.data.time.values

    @property
    def lats(self):
        return self.data.lats.values

    @property
    def lons(self):
        return self.data.lons.values

    @property
    def spatial_dims(self):
        return (self.lats.shape[0], self.lons.shape[0])

    def save(self, filename):
        """
        Save DataField as nc file.

        :param filename: filename for nc file
        :type filename: str
        """
        # harmonize missing and fill_values for saving
        try:
            self.data.variable.encoding[
                "missing_value"
            ] = self.data.variable.encoding["_FillValue"]
        except KeyError:
            pass

        if not filename.endswith(".nc"):
            filename += ".nc"

        self.data.to_netcdf(filename)

    def select_date(self, date_from, date_to, inplace=True):
        """
        Selects date range. Both ends are inclusive.

        :param date_from: date from
        :type date_from: datetime.date|datetime.datetime
        :param date_to: date to
        :type date_to: datetime.date|datetime.datetime
        :param inplace: whether to make operation in-place or return
        :type inplace: bool
        """
        assert isinstance(
            date_from, (date, datetime)
        ), f"Date from must be datetime, got {type(date_from)}"
        assert isinstance(
            date_to, (date, datetime)
        ), f"Date to must be datetime, got {type(date_to)}"

        selected_data = self.data.sel(time=slice(date_from, date_to))

        if inplace:
            self.data = selected_data
        else:
            return DataField(data=selected_data)

    def select_months(self, months, inplace=True):
        """
        Subselects only certain months.

        :param months: months to keep
        :type months: list[int]
        :param inplace: whether to make operation in-place or return
        :type inplace: bool
        """
        assert isinstance(
            months, (list, tuple)
        ), f"Months must be an iterable, got {type(months)}"

        months_index = filter(
            lambda x: self.data.time[x].dt.month.values in months,
            range(len(self.time)),
        )
        selected_data = self.data.isel(time=list(months_index))

        if inplace:
            self.data = selected_data
        else:
            return DataField(data=selected_data)

    def select_lat_lon(self, lats=None, lons=None, inplace=True):
        """
        Subselects region in the data given by lats and lons.

        :param lats: latitude bounds to keep, both are inclusive
        :type lats: list[int|None]|None
        :param lons: longitude bounds to keep, both are inclusive
        :type lons: list[int|None]|None
        :param inplace: whether to make operation in-place or return
        :type inplace: bool
        """
        selected_data = self.data.copy()
        if lats is not None:
            assert len(lats) == 2, f"Need two lats, got {lats}"
            selected_data = selected_data.sel(lats=slice(lats[0], lats[1]))

        if lons is not None:
            assert len(lons) == 2, f"Need two lons, got {lons}"
            # shift to -180 -- 179 (xarray only selects on monotically
            # increasing coordinates)
            shifted = self.shift_lons_to_minus_notation(selected_data)
            # shift user passed lons to -180 -- 179
            lons = [((lon + 180) % 360 - 180) for lon in lons]
            # select
            selected_data = shifted.sel(lons=slice(lons[0], lons[1]))
            # shift back
            selected_data = self.shift_lons_to_all_east_notation(selected_data)

        if inplace:
            self.data = selected_data
        else:
            return DataField(data=selected_data)

    @property
    def cos_weights(self):
        """
        Returns a grid with scaling weights based on cosine of latitude.
        """
        cos_weights = np.zeros(self.spatial_dims)
        for ndx in range(self.lats.shape[0]):
            cos_weights[ndx, :] = np.cos(self.lats[ndx] * np.pi / 180.0) ** 0.5

        return cos_weights

    def temporal_resample(self, resample_to, function=np.nanmean, inplace=True):
        """
        Resamples data in temporal sense.

        :param resample_to: target resampling period for the data
        :type resample_to: pandas time str
        :param function: function to use for reducing
        :type function: callable
        :param inplace: whether to make operation in-place or return
        :type inplace: bool
        """
        resampled = self.data.resample(time=resample_to).reduce(
            function, dim="time"
        )

        if inplace:
            self.data = resampled
        else:
            return DataField(data=resampled)

    def spatial_resample(self, d_lat, d_lon, method="linear", inplace=True):
        """
        Resamples data in spatial sense. Uses scipy's internal `interp` method.

        :param d_lat: target difference in latitude
        :param d_lat: float|int
        :param d_lon: target difference in longitude
        :param d_lon: float|int
        :param method: interpolation method to use
        :type method: str['nearest' or 'linear']
        :param inplace: whether to make operation in-place or return
        :type inplace: bool
        """
        # shift to -180 -- 179 for resampling
        shifted = self.shift_lons_to_minus_notation(self.data)

        resampled = shifted.interp(
            lats=np.arange(shifted.lats.min(), shifted.lats.max() + 1, d_lat),
            lons=np.arange(shifted.lons.min(), shifted.lons.max() + 1, d_lon),
            method=method,
        )
        # create new coordinates attributes
        resampled["lons"] = self._update_coord_attributes(
            shifted.lons, resampled.lons
        )
        resampled["lats"] = self._update_coord_attributes(
            shifted.lats, resampled.lats
        )

        resampled_shifted_back = self.shift_lons_to_all_east_notation(resampled)

        if inplace:
            self.data = resampled_shifted_back
        else:
            return DataField(data=resampled_shifted_back)

    def deseasonalise(self, base_period=None, standardise=False, inplace=True):
        """
        Removes seasonality in mean and optionally in std.

        :param base_period: period for computing cycle, if None, take all data
        :type base_period: list[datetimes]|None
        :param standardise: whether to also remove seasonality in STD
        :type standardise: bool
        :param inplace: whether to make operation in-place or return
        :type inplace: bool
        :return: seasonal mean and std
        :rtype: xr.DataArray, xr.DataArray
        """
        inferred_freq = pd.infer_freq(self.time)
        if base_period is None:
            base_period = [None, None]

        base_data = self.data.sel(time=slice(base_period[0], base_period[1]))

        if inferred_freq in ["M", "SM", "BM", "MS", "SMS", "BMS"]:
            # monthly data
            groupby = base_data.time.dt.month
        elif inferred_freq in ["C", "B", "D"]:
            # daily data
            groupby = base_data.time.dayofyear
        else:
            raise ValueError(
                "Anomalise supported only for daily or monthly data"
            )

        # compute climatologies
        climatology_mean = base_data.groupby(groupby).mean("time")
        if standardise:
            climatology_std = base_data.groupby(groupby).std("time")
        else:
            climatology_std = 1.0

        stand_anomalies = xr.apply_ufunc(
            lambda x, mean, std: (x - mean) / std,
            self.data.groupby(groupby),
            climatology_mean,
            climatology_std,
        )

        if inplace:
            self.data = stand_anomalies
            return climatology_mean, climatology_std
        else:
            return (
                DataField(data=stand_anomalies),
                climatology_mean,
                climatology_std,
            )

    def anomalise(self, base_period=None, inplace=True):
        """
        Removes seasonal/yearly cycle from the data.

        :param base_period: period for computing cycle, if None, take all data
        :type base_period: list[datetimes]|None
        :param inplace: whether to make operation in-place or return
        :type inplace: bool
        :return: seasonal mean
        :rtype: xr.DataArray
        """
        return self.deseasonalise(
            base_period=base_period, standardise=False, inplace=inplace
        )[:-1]

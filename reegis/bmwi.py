# -*- coding: utf-8 -*-

""" This module is designed to download and prepare BMWI data.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import logging

if not os.environ.get('READTHEDOCS') == 'True':
    # External libraries
    import pandas as pd

    # Internal modules
    import reegis.config as cfg
    import reegis.tools as tools


def get_bmwi_energiedaten_file(overwrite=False):
    filename = os.path.join(cfg.get('paths', 'general'),
                            cfg.get('bmwi', 'energiedaten'))
    logging.debug("Return status from energiedaten file: {0}".format(
        tools.download_file(filename, cfg.get('bmwi', 'url_energiedaten'),
                            overwrite=overwrite)))
    return filename


def read_bmwi_sheet_7(sub):
    """

    Parameters
    ----------
    sub : str
        Sub-table 'a' or 'b'.

    Returns
    -------
    pd.DataFrame

    Examples
    --------
    >>> fs = read_bmwi_sheet_7('a').sort_index()  # doctest: +SKIP
    >>> int(float(fs.loc[('Industrie', 'gesamt'), 2014]))  # doctest: +SKIP
    2545
    >>> fs = read_bmwi_sheet_7('b').sort_index()  # doctest: +SKIP
    >>> float(fs.loc[('private Haushalte', 'gesamt'), 2014])  # doctest: +SKIP
    2188.04
    """
    filename = get_bmwi_energiedaten_file()

    sheet = '7' + sub

    fs = pd.DataFrame()
    n = 4
    while 2014 not in fs.columns:
        n += 1
        fs = pd.read_excel(filename, sheet, skiprows=n)

    # Convert first column to string
    fs['Unnamed: 0'] = fs['Unnamed: 0'].apply(str)

    # Create 'A' column with sector name (shorten the name)
    fs['A'] = fs['Unnamed: 0'].apply(
        lambda x: x.replace('nach Anwendungsbereichen ', '')
        if 'Endenergie' in x else float('nan'))

    fs['A'] = fs['A'].fillna(method='ffill')
    fs = fs[fs['A'].notnull()]
    fs['A'] = fs['A'].apply(
        lambda x: x.replace('Endenergieverbrauch in der ', ''))
    fs['A'] = fs['A'].apply(
        lambda x: x.replace('Endenergieverbrauch im ', ''))
    fs['A'] = fs['A'].apply(
        lambda x: x.replace('Endenergieverbrauch in den ', ''))
    fs['A'] = fs['A'].apply(lambda x: x.replace('Sektor ', ''))
    fs['A'] = fs['A'].apply(
        lambda x: x.replace('privaten Haushalten', 'private Haushalte'))

    # Create 'B' column with type
    fs['B'] = fs['Unnamed: 0'].apply(
        lambda x: x if '-' not in x else float('nan'))
    fs['B'] = fs['B'].fillna(method='ffill')

    fs['B'] = fs['B'].apply(lambda x: x if 'nan' not in x else float('nan'))
    fs = fs[fs['B'].notnull()]

    # Create 'C' column with fuel
    fs['C'] = fs['Unnamed: 0'].apply(lambda x: x if '-' in x else float('nan'))
    fs['C'] = fs['C'].fillna(fs['B'])

    # Delete first column and set 'A', 'B', 'C' columns to index
    del fs['Unnamed: 0']

    # Set new columns to index
    fs = fs.set_index(['A', 'B', 'C'], drop=True)
    return fs


def bmwi_re_energy_capacity():
    """Prepare the energy production and capacity table from sheet 20.

    Examples
    --------
    >>> re = bmwi_re_energy_capacity()  # doctest: +SKIP
    >>> re.loc[2016, ('water', 'capacity')]  # doctest: +SKIP
    5601
    """
    filename = get_bmwi_energiedaten_file()
    repp = pd.read_excel(filename, '20', skiprows=22).iloc[:24]
    repp = repp.drop(repp.index[[0, 4, 8, 12, 16, 20]])
    repp['type'] = (['water'] * 3 +
                    ['wind'] * 3 +
                    ['bioenergy'] * 3 +
                    ['biogenic waste'] * 3 +
                    ['solar'] * 3 +
                    ['geothermal'] * 3)
    repp['value'] = ['energy', 'capacity', 'fraction'] * 6
    repp.set_index(['type', 'value'], inplace=True)
    del repp['Unnamed: 0']
    return repp.transpose().sort_index(1)


def get_annual_electricity_demand_bmwi(year):
    """Returns the annual demand for the given year from the BMWI Energiedaten
    in TWh (Tera Watt hours). Will return None if data for the given year is
    not available.

    Examples
    --------
    >>> get_annual_electricity_demand_bmwi(2014)  # doctest: +SKIP
    523.988
    >>> get_annual_electricity_demand_bmwi(1900)  # doctest: +SKIP
    None
    """
    infile = get_bmwi_energiedaten_file()

    table = pd.read_excel(infile, '21', skiprows=7, index_col=[0])
    try:
        return table.loc['   zusammen', year]
    except KeyError:
        return None


if __name__ == "__main__":
    pass

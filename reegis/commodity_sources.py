# -*- coding: utf-8 -*-

"""Reegis geometry tools.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import logging

# External libraries
import pandas as pd

# oemof libraries
from oemof.tools import logger

# internal modules
import reegis.config as cfg
import reegis.bmwi


def initialise_commodity_sources():
    cols = pd.MultiIndex(levels=[[], []], labels=[[], []], names=['', ''])
    src = pd.DataFrame(columns=cols, index=range(1990, 2017))
    return src


def prices_from_bmwi_energiedaten(src):
    fuels = {
        '  - Rohöl': 'Oil',
        '  - Erdgas': 'Natural gas',
        '  - Steinkohlen': 'Hard coal'
    }

    filename = reegis.bmwi.get_bmwi_energiedaten_file()

    # get prices for commodity source from sheet 26
    fs = pd.read_excel(filename, '26', skiprows=6, index_col=[0]).iloc[4:7]
    del fs['Einheit']
    fs = fs.transpose().rename(columns=fuels)

    # get unit conversion (uc) from sheet 0.2
    uc = pd.read_excel(filename, '0.2', skiprows=6, index_col=[0]).iloc[:6]
    del uc['Unnamed: 1']
    del uc.index.name
    uc.set_index(uc.index.str.strip(), inplace=True)
    uc = uc.drop(uc.index[[0]])

    # convert the following columns to EUR / Joule using uc (unit conversion)
    fs['Oil'] = (fs['Oil'] /
                 uc.loc['1 Mio. t Rohöleinheit (RÖE)', 'PJ'] / 1.0e15 * 1.0e6)
    fs['Natural gas'] = fs['Natural gas'] / 1.0e+12
    fs['Hard coal'] = (fs['Hard coal'] /
                       uc.loc['1 Mio. t  Steinkohleeinheit (SKE)', 'PJ'] /
                       1.0e15 * 1.0e6)

    for col in fs.columns:
        src[col.lower(), 'costs'] = fs[col]
    return src


def emissions_from_znes(src):

    znes = pd.read_csv(
            os.path.join(cfg.get('paths', 'static_sources'),
                         cfg.get('static_sources', 'znes_flens_data')),
            skiprows=1, header=[0, 1], index_col=[0])
    znes['emission', 'value'] /= 1.0e+3  # gCO2 / J
    for fuel in znes.index:
        src[fuel.lower(), 'emission'] = znes.loc[fuel, ('emission', 'value')]
    return src


def prices_2014_from_znes(src, force_znes=False):
    znes = pd.read_csv(
            os.path.join(cfg.get('paths', 'static_sources'),
                         cfg.get('static_sources', 'znes_flens_data')),
            skiprows=1, header=[0, 1], index_col=[0])
    znes['fuel price', 'value'] /= 1.0e+9  # EUR / J
    for fuel in znes.index:
        if src.get((fuel.lower(), 'costs')) is None or force_znes:
            src.loc[2014, (fuel.lower(), 'costs')] = znes.loc[
                fuel, ('fuel price', 'value')]
    return src


def get_commodity_sources():
    logging.info("Get prices and emissions for commodity sources.")
    commodity_sources = initialise_commodity_sources()
    commodity_sources = prices_from_bmwi_energiedaten(commodity_sources)
    commodity_sources = emissions_from_znes(commodity_sources)
    commodity_sources = prices_2014_from_znes(commodity_sources)
    commodity_sources.sort_index(1, inplace=True)
    logging.info("Emissions: [g/J], Costs: [EUR/J]")
    return commodity_sources


if __name__ == "__main__":
    logger.define_logging()
    logging.info("Commodity Sources.")
    print(get_commodity_sources())

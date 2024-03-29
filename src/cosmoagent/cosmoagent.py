""" Cosmoagent module for cryptocurrencies """
# pylint: disable=no-name-in-module, import-error, R0801

import os
import time
import threading

# local imports
from utils import utils, trends, broker, dynamodb
from utils import cosmomixins

# Staging
STAGING = bool(int(os.getenv('TF_VAR_STAGING')))

# Cosmoagent vars
COSMOAGENT_CONFIG = {}
SYMBOLS_TIMESTAMPS = {}
FROM_LAMBDA = bool(int(os.getenv('TF_VAR_FROM_LAMBDA')))
SYMBOL_TYPE = os.getenv('TF_VAR_SYMBOL_TYPE')
US_MARKET_STATUS = True

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session(from_lambda=FROM_LAMBDA)
CONFIG_TABLE_NAME = 'mm_cosmoagent'

SYMBOLS_TIMESTAMPS_FEATURE = f'{SYMBOL_TYPE.lower()}_symbols_timestamps'

@utils.logger.catch
def put_symbols_timestamps():
    """ Put symbols timestamps for monitoring purposes """
    utils.logger.info('Put Symbols timestamps')

    to_put = {'feature' : SYMBOLS_TIMESTAMPS_FEATURE, 'value' : SYMBOLS_TIMESTAMPS}

    dynamodb.put_item_from_dict(AWS_DYNAMO_SESSION,
                                CONFIG_TABLE_NAME,
                                to_put,
                                STAGING)


@utils.logger.catch
def put_planet_trend_info(symbol, ptrend, mtrend, strend, pd_limit, pz_limit, pclose):
    """ Put planet trend indicator in Dynamo table """
    # pylint: disable=too-many-arguments, global-variable-not-assigned
    global SYMBOLS_TIMESTAMPS

    utils.logger.info(f'{symbol} Put Planet info')

    cosmo_time = cosmomixins.get_cosmobot_time()
    cosmo_week = cosmo_time[0]
    cosmo_timestamp = cosmo_time[4]

    to_log = f'{symbol} pclose: {pclose} tms: {cosmo_timestamp} mtrend: {mtrend}'
    utils.logger.info(to_log)

    to_put = {  'week' : cosmo_week,
                'timestamp' : cosmo_timestamp,
                'ptrend' : ptrend,
                'mtrend' : mtrend,
                'strend' : strend,
                'pclose' : pclose,
                'pd_limit' : pd_limit,
                'pz_limit' : pz_limit }

    table_name = f'mm_cosmobot_historical_{symbol}'
    result = dynamodb.put_item_from_dict(AWS_DYNAMO_SESSION, table_name, to_put, STAGING)

    if result:
        SYMBOLS_TIMESTAMPS[symbol] = cosmo_timestamp


def get_crypto_planet_trend(symbol):
    """ Get planet trend indicator data """
    # pylint: disable=broad-except
    utils.logger.info(f'{symbol} Get Planet info')

    try:

        # 1day data
        trend_data = broker.binance_get_chart_data( symbol,
                                                    start='44 days ago',
                                                    end='now',
                                                    period='1d',
                                                    is_df=True,
                                                    decimal=True)

        ptrend, pclose, pd_limit, pz_limit = trends.planets_volume(trend_data)
        minfo = trends.planets_volume(trend_data, trend_type='mean')
        sinfo = trends.planets_volume(trend_data, trend_type='sum')

        return (symbol, ptrend, minfo[0], sinfo[0], pd_limit, pz_limit, pclose)

    except Exception as exc:
        utils.logger.error(exc)
        return (symbol, None, None, None, None, None, None)


def get_stock_planet_trend(symbol):
    """ Get planet trend indicator data """
    # pylint: disable=broad-except
    utils.logger.info(f'Get Planet info for {symbol}')

    try:

        # 1day data
        trend_data = broker.yfinance_get_chart_data( symbol, period='30d', interval='1d')

        ptrend, pclose, pd_limit, pz_limit = trends.planets_volume(trend_data)
        minfo = trends.planets_volume(trend_data, trend_type='mean')
        sinfo = trends.planets_volume(trend_data, trend_type='sum')

        return (symbol, ptrend, minfo[0], sinfo[0], pd_limit, pz_limit, pclose)

    except Exception as exc:
        utils.logger.error(exc)
        return (symbol, None, None, None, None, None, None)


@utils.logger.catch
def run(symbol):
    """ Run cosmoagent"""

    utils.logger.info(f'Run Cosmoagent for {symbol}')

    if SYMBOL_TYPE == 'CRYPTO':
        symbol_cosmos_info = get_crypto_planet_trend(symbol)
    elif SYMBOL_TYPE in ('STOCK', 'ETF'):
        symbol_cosmos_info = get_stock_planet_trend(symbol)
    else:
        symbol_cosmos_info = (None,)

    if symbol_cosmos_info[1]:
        put_planet_trend_info(*symbol_cosmos_info)


@utils.logger.catch
def launch(event=None, context=None):
    """ Load configs and run once the agent"""
    # pylint: disable=unused-argument, global-statement
    global COSMOAGENT_CONFIG, SYMBOLS_TIMESTAMPS, US_MARKET_STATUS
    # Load config
    COSMOAGENT_CONFIG = dynamodb.load_feature_value_config( AWS_DYNAMO_SESSION,
                                                            CONFIG_TABLE_NAME,
                                                            'config',
                                                            STAGING)

    SYMBOLS_TIMESTAMPS = dynamodb.load_feature_value_config( AWS_DYNAMO_SESSION,
                                                            CONFIG_TABLE_NAME,
                                                            SYMBOLS_TIMESTAMPS_FEATURE,
                                                            STAGING)

    SYMBOLS_TIMESTAMPS = {sym: int(tms) for sym, tms in SYMBOLS_TIMESTAMPS.items()}

    # Log path
    if not FROM_LAMBDA:
        utils.logger_path(COSMOAGENT_CONFIG['log_path'])

    if event == 'first_launch':
        utils.logger.info('First launch: only loads config')
        return

    # Start bot run() with threads
    threads = []

    # Get Market Status
    US_MARKET_STATUS = broker.us_market_status()

    if SYMBOL_TYPE == 'CRYPTO':
        # Use threading but be careful to not impact binance rate limit: max 20 req/s
        symbols_chunks = utils.divide_list_chunks(COSMOAGENT_CONFIG['crypto_symbols'], 10)

    elif SYMBOL_TYPE == 'STOCK' and US_MARKET_STATUS:
        symbols_chunks = utils.divide_list_chunks(COSMOAGENT_CONFIG['stock_symbols'], 10)

    elif SYMBOL_TYPE == 'ETF' and US_MARKET_STATUS:
        symbols_chunks = utils.divide_list_chunks(COSMOAGENT_CONFIG['etf_symbols'], 10)

    else:
        if not US_MARKET_STATUS:
            utils.logger.info('US Market close')
        else:
            utils.logger.error(f'Wrong Symbol Type: {SYMBOL_TYPE}')
        symbols_chunks = []

    for chunk in symbols_chunks:
        for symbol in chunk:
            runner = threading.Thread(target=run, args=(symbol,))
            threads.append(runner)
            runner.start()

        for thread in threads:
            thread.join()

        time.sleep(2)

    put_symbols_timestamps()

import config
import requests
import json
import pandas as pd
from kiteconnect import KiteConnect
import redis

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

def getOptionsWithPremium(symbol, premium_start, premium_end, expiry_date, type):
    df = getOptionsChainData(symbol)
    filtered_df = df[(df['expiryDate'] == expiry_date) & (df[f'{type}.lastPrice'] > premium_start) & (df[f'{type}.lastPrice'] < premium_end)]

    _premiunIncrement = 2
    while len(filtered_df) == 0:
        # increase the premiums
        filtered_df = df[(df['expiryDate'] == expiry_date) & (df[f'{type}.lastPrice'] > premium_start) & (df[f'{type}.lastPrice'] < premium_end + _premiunIncrement)]
        _premiunIncrement += 2

    return filtered_df.iloc[len(filtered_df) - 1].strikePrice


def getOptionsChainData(symbol):
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; '
            'x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36'}

    main_url = "https://www.nseindia.com/"
    response = requests.get(main_url, headers=headers)
    cookies = response.cookies

    url = f'https://www.nseindia.com/api/option-chain-indices?symbol={symbol}'
    data = requests.get(url, headers=headers, cookies=cookies)

    return pd.json_normalize(data.json()['records']['data'])

def getInstrumentTokensAndTradingSymbols(type, strike_price):
    df = pd.read_json(config.SYMBOLS_PATH)
    filter_df = df[df['strike'] == int(strike_price)]
    if type == 'CE':
        return filter_df.iloc[0].CE_symbol, filter_df.iloc[0].CE_instrument_token
    else:
        return filter_df.iloc[0].PE_symbol, filter_df.iloc[0].PE_instrument_token

def get_nearest_symbol_info(
    p_index_name='BANKNIFTY',
    p_instrument_type='CE',
    ):

    kite = KiteConnect(api_key=config.API_KEY)
    access_token = redis_client.get('Access_Token')
    kite.set_access_token(access_token)

    instruments_df = pd.DataFrame (kite.instruments (exchange='NFO'))
    options_df = instruments_df[(instruments_df['segment'] == 'NFO-OPT') & (instruments_df['name'].isin(['NIFTY', 'BANKNIFTY']))] #the original data that downloaded from Zerodha for all the instruments
    options_df = options_df[options_df['expiry'].isin(options_df.groupby('name').expiry.min())]

    l_symbols = options_df[(options_df['name'] == p_index_name)
                             & (options_df['instrument_type']
                             == p_instrument_type)].tradingsymbol.map(lambda x: \
            'NFO:' + x).to_list()

    data = kite.ltp(l_symbols)

    # Create a list of dictionaries to represent the rows

    rows = [{
        'exchange': key.split(':')[0],
        'symbol': key.split(':')[1],
        'instrument_type': key[-2:],
        'instrument_token': value['instrument_token'],
        'last_price': value['last_price'],
        } for (key, value) in data.items()]

    # Convert the list of dictionaries to a DataFrame

    df = pd.DataFrame(rows)
    df['nearest'] = (df.last_price - config.CLOSEST_PREMIUM).abs()
    result = df.sort_values(['nearest'])[:1].to_dict(orient='records')
    return result[0]['symbol']



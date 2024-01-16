from asyncio.log import logger
from kiteconnect import KiteConnect, KiteTicker
import config
import pandas as pd
import redis
from loggingConfig import get_logger,setup_logging
from sessionVariables import Order
import sessionVariables
import utils

setup_logging()
logger = get_logger(__name__)

def startTicksData():
    logger.info('Generating access token')
    redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)

    if redis_client.exists('Access_Token') == 1 :
        access_token = redis_client.get('Access_Token')
        logger.info(f'ACCESS TOKEN from redis- {access_token}')
    else :
        access_token = utils.generate_access_token()
        logger.info(f'ACCESS TOKEN - {access_token}')
        redis_client.set('Access_Token', access_token)

    logger.info('TicksAndOrders started')
    
    global kws
    kws = KiteTicker(config.API_KEY, access_token)

    logger.info('Generating trading symbols')
    try:
        kite = KiteConnect(api_key=config.API_KEY)
        kite.set_access_token(access_token)
        utils.options_instruments(kite, p_json_path=config.SYMBOLS_PATH, p_index='BANKNIFTY', p_contract_exp=config.EXPIRY_WEEK)
        logger.info('Generated trading symbols successfully')
    except Exception as e:
        logger.error(f'Error in generating symbols - {e}')
    
    def on_ticks(ws, ticks):
        global df
        # Callback to receive ticks.

        df=pd.json_normalize(ticks)
        if len(df) == 0:
            return

        for index, row in df.iterrows():
            if redis_client.exists(str(row['instrument_token'])) == 1:      
                redis_client.set(str(row['instrument_token']), row['last_price'])

    def on_order_update(ws, order):        
        order_df=pd.json_normalize(order)
        if len(order_df) == 0:
            return

        logger.info(order)
        
        for index, row in order_df.iterrows():
            if 'BANKNIFTY' in row["tradingsymbol"]:
                #update order to ache
                if row['status'] == 'COMPLETE':
                    order = Order(row["tradingsymbol"],row['transaction_type'],row["instrument_token"],row["quantity"],'',row["order_id"],row['status'],row['average_price'])
                    sessionVariables.addOrUpdateOrderToCache(order)
                
                    ws.subscribe([int(row["instrument_token"])])
                    ws.set_mode(ws.MODE_LTP, [int(row["instrument_token"])])
                    redis_client.set(str(row['instrument_token']), row['average_price'])

            if 'NIFTY' in row["tradingsymbol"]:
                #update order to ache
                
                if row['status'] == 'COMPLETE':
                    order = Order(row["tradingsymbol"],row['transaction_type'],row["instrument_token"],row["quantity"],'',row["order_id"],row['status'],row['average_price'])
                    sessionVariables.addOrUpdateOrderToCache(order)
                
                    ws.subscribe([int(row["instrument_token"])])
                    ws.set_mode(ws.MODE_LTP, [int(row["instrument_token"])])
                    redis_client.set(str(row['instrument_token']), row['average_price'])


    def on_connect(ws, response):
        tokens = config.INSTRUMENT_TOKEN.split(",")
        for token in tokens:
            redis_client.set(token, '')
            ws.subscribe([int(token)])
            ws.set_mode(ws.MODE_LTP, [int(token)])
        logger.info('ticks data connected')

    def on_close(ws, code, reason):
        # On connection close stop the main loop
        # Reconnection will not happen after executing `ws.stop()`
        # ws.stop()
        logger.debug('ticks data closed')

    def on_error(ws, code, reason):
        logger.error("Error at ticks and  orders")
        logger.error(reason)

    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close
    kws.on_order_update = on_order_update
    kws.on_error = on_error

    # Infinite loop on the main thread. Nothing after this will run.
    # You have to use the pre-defined callbacks to manage subscriptions.
    kws.connect()


from ctypes import util
from loggingConfig import get_logger,setup_logging
from kiteconnect import KiteConnect
import config
import json
from order import Order
import sessionVariables
import redis
import utilities

setup_logging()
logger = get_logger(__name__)

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

def placeOrder(order: Order):

    kite = KiteConnect(api_key=config.API_KEY)
    access_token = config.ACCESS_TOKEN

    if redis_client.exists('Access_Token') == 1 :
        access_token = redis_client.get('Access_Token')
        logger.info(f'ACCESS TOKEN from redis- {access_token}')
    else :
        access_token = utilities.generate_access_token()
        logger.info(f'ACCESS TOKEN - {access_token}')
        redis_client.set('Access_Token', access_token)
        access_token = redis_client.set('Access_Token')

    kite.set_access_token(access_token)
    
    # Place an order
    try:
        if order.quantity > config.LEG_QTY:
            legs_qty = round(order.quantity/config.LEG_QTY)
            remaininglots = order.quantity % config.LEG_QTY

            for i in range(legs_qty):
                order_id = kite.place_order(tradingsymbol=order.tradingsymbol,
                                            exchange=kite.EXCHANGE_NFO,
                                            transaction_type= kite.TRANSACTION_TYPE_BUY if order.transaction_type == 'BUY' else kite.TRANSACTION_TYPE_SELL,
                                            quantity=config.LEG_QTY,
                                            variety=kite.VARIETY_REGULAR,
                                            order_type=kite.ORDER_TYPE_MARKET,
                                            product=kite.PRODUCT_MIS, # change this to kite.PRODUCT_NRML
                                            validity=kite.VALIDITY_DAY)
                sessionVariables.addOrUpdateOrderToCache(Order(order.tradingsymbol, order.transaction_type,'',config.LEG_QTY,'',order_id,'Pending',''))
            if remaininglots > 0:
                order_id = kite.place_order(tradingsymbol=order.tradingsymbol,
                                            exchange=kite.EXCHANGE_NFO,
                                            transaction_type= kite.TRANSACTION_TYPE_BUY if order.transaction_type == 'BUY' else kite.TRANSACTION_TYPE_SELL,
                                            quantity=remaininglots,
                                            variety=kite.VARIETY_REGULAR,
                                            order_type=kite.ORDER_TYPE_MARKET,
                                            product=kite.PRODUCT_MIS, # change this to kite.PRODUCT_NRML
                                            validity=kite.VALIDITY_DAY)
                sessionVariables.addOrUpdateOrderToCache(Order(order.tradingsymbol, order.transaction_type,'',remaininglots,'',order_id,'Pending',''))
            
            # leg_qty = order.quantity / 2

            # order_id = kite.place_order(tradingsymbol=order.tradingsymbol,
            #                         exchange=kite.EXCHANGE_NFO,
            #                         transaction_type= kite.TRANSACTION_TYPE_BUY if order.transaction_type == 'BUY' else kite.TRANSACTION_TYPE_SELL,
            #                         quantity=order.quantity,
            #                         variety=kite.VARIETY_ICEBERG,
            #                         order_type=kite.ORDER_TYPE_LIMIT,
            #                         price=5.3,
            #                         product=kite.PRODUCT_MIS, # change this to kite.PRODUCT_NRML
            #                         validity=kite.VALIDITY_DAY,
            #                         iceberg_legs=2,
            #                         iceberg_quantity=int(leg_qty))
        else:
            order_id = kite.place_order(tradingsymbol=order.tradingsymbol,
                                        exchange=kite.EXCHANGE_NFO,
                                        transaction_type= kite.TRANSACTION_TYPE_BUY if order.transaction_type == 'BUY' else kite.TRANSACTION_TYPE_SELL,
                                        quantity=order.quantity,
                                        variety=kite.VARIETY_REGULAR,
                                        order_type=kite.ORDER_TYPE_MARKET,
                                        product=kite.PRODUCT_MIS, # change this to kite.PRODUCT_NRML
                                        validity=kite.VALIDITY_DAY)

            logger.info(f"Order placed. ID is: {order_id}")
            sessionVariables.addOrUpdateOrderToCache(Order(order.tradingsymbol, order.transaction_type,'',order.quantity,'',order_id,'Pending',''))
        return order_id
        
    except Exception as e:        
        logger.info("Order placement failed: {}".format(e))
    
def storeOrderToJsonFile(executedOrder):
     #store in a json file
    executed_order = {
        "order_id": executedOrder.order_id,
        "trading_symbol": executedOrder.tradingsymbol,
        "instrument_token": str(executedOrder.instrument_token),
        "average_price":executedOrder.average_price,
    }
    json_string = json.dumps(executed_order)
    file_path = config.SESSION_ORDERS_FILE

    # Append the JSON data to the file
    with open(file_path, "a") as file:
        file.write(json_string + "\n")

from asyncio.log import logger
from typing import List
import redis
import json
import numpy as np

class Order:
    def __init__(self, tradingsymbol, transaction_type, instrument_token, quantity, strategycode, orderid, status, averagePrice) -> None:
        self.tradingsymbol = tradingsymbol
        self.transaction_type = transaction_type
        self.instrument_token = instrument_token
        self.quantity = quantity
        self.strategycode = strategycode
        self.orderid = orderid
        self.status = status
        self.averagePrice = averagePrice
        pass

orders_key = 'orders'
_orders = []

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

def class_to_dict(obj):
    if isinstance(obj, np.int64):
        return str(obj)
    return obj.__dict__


def addOrUpdateOrderToCache(order: Order):
    if redis_client.exists(orders_key) == 0:       
        _orders.append(order)
        serialized_object = json.dumps(_orders,default=class_to_dict)
        redis_client.set(orders_key, serialized_object)
        return
   
    retrieved_object = redis_client.get(orders_key)
    # Deserialize the object using pickle
    _orders_object = json.loads(retrieved_object)
   
    for obj in _orders_object:       
        if obj['orderid'] == order.orderid:
            obj['quantity'] = order.quantity
            obj['status'] = order.status
            obj["tradingsymbol"] = order.tradingsymbol
            obj["transaction_type"] = order.transaction_type
            obj["strategycode"] = order.strategycode
            obj['averagePrice'] = order.averagePrice
            obj['instrument_token'] = order.instrument_token

            serialized_object = json.dumps(_orders_object,default=class_to_dict)
            redis_client.set(orders_key, serialized_object)
            return
    if _orders_object is None:
        _orders_object = List[Order]

    _orders_object.append(order)
    serialized_object = json.dumps(_orders_object,default=class_to_dict)
    redis_client.set(orders_key, serialized_object)

def RemoveOrderFromCache(orderid):      
    retrieved_object = redis_client.get(orders_key)
    _orders_object = json.loads(retrieved_object)
    _orders = []

    for obj in _orders_object:       
        if obj['orderid'] != orderid:
             _orders.append(Order(obj['tradingsymbol'], obj['transaction_type'],obj['instrument_token'], obj['quantity'], obj['strategycode'],obj["orderid"],obj["status"],obj['averagePrice']))

    serialized_object = json.dumps(_orders,default=class_to_dict)
    redis_client.set(orders_key, serialized_object)
    return

def getOrdersFromCache() -> List[Order]:
    result: List[Order] = []
    if redis_client.exists(orders_key) == 1:
        retrieved_object = redis_client.get(orders_key)   
        json_data = json.loads(retrieved_object)        
        for obj in json_data:
            result.append(Order(obj['tradingsymbol'], obj['transaction_type'],obj['instrument_token'], obj['quantity'], obj['strategycode'],obj["orderid"],obj["status"],obj['averagePrice']))        

    return result

def removeAllKeys():
    redis_client.flushall()
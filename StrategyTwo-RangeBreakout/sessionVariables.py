from asyncio.log import logger
from typing import List
import redis
import json
import numpy as np
from ordermanagement import Order
import config

class HoldingPosition:
    def __init__(self, symbol, token, buyPrice, entryCount, status) -> None:
        self.Symbol = symbol
        self.Token = token
        self.BuyPrice = buyPrice
        self.EntryCount = entryCount
        self.Status = status
        pass

_holdingPositions = []
holding_position_key = 'holding_positions'
orders_key = 'orders'
_orders = []

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

def class_to_dict(obj):
    if isinstance(obj, np.int64):
        return str(obj)
    return obj.__dict__

def StoreOrUpdateHoldingPsitions(holdingPsition: HoldingPosition):
    
    if redis_client.exists(holding_position_key) == 0:       
        _holdingPositions.append(holdingPsition)
        serialized_object = json.dumps(_holdingPositions,default=class_to_dict)
        redis_client.set(holding_position_key, serialized_object)
        return
   
    retrieved_object = redis_client.get(holding_position_key)
    # Deserialize the object using pickle
    _holdingPositions_object = json.loads(retrieved_object)
   
    for obj in _holdingPositions_object:       
        if obj['Symbol'] == holdingPsition.Symbol:
            obj['BuyPrice'] = holdingPsition.BuyPrice
            obj['Status'] = holdingPsition.Status
            serialized_object = json.dumps(_holdingPositions_object,default=class_to_dict)
            redis_client.set(holding_position_key, serialized_object)
            return
    if _holdingPositions_object is None:
        _holdingPositions_object = List[HoldingPosition]

    _holdingPositions_object.append(holdingPsition)
    serialized_object = json.dumps(_holdingPositions_object,default=class_to_dict)
    redis_client.set(holding_position_key, serialized_object)

def RemoveHoldingPsition(symbol):      
    retrieved_object = redis_client.get(holding_position_key)
    _holdingPositions_object = json.loads(retrieved_object)
    _holdingPositions = []

    for obj in _holdingPositions_object:       
        if obj['Symbol'] == symbol:
             _holdingPositions.append(HoldingPosition(obj['Symbol'], obj['Token'], obj['BuyPrice'], obj['EntryCount'], 'Completed'))
        else:            
            _holdingPositions.append(HoldingPosition(obj['Symbol'], obj['Token'], obj['BuyPrice'], obj['EntryCount'], obj['Status']))            
    
    serialized_object = json.dumps(_holdingPositions,default=class_to_dict)
    redis_client.set(holding_position_key, serialized_object)
    return

def getHoldingPosition(symbol):      
    retrieved_object = redis_client.get(holding_position_key)
    _holdingPositions_object = json.loads(retrieved_object)    

    for obj in _holdingPositions_object:       
        if obj['Symbol'] == symbol:
            return HoldingPosition(obj['Symbol'], obj['Token'], obj['BuyPrice'], obj['EntryCount'], obj['Status'])    

def getHoldingPositions() -> List[HoldingPosition]:
    result: List[HoldingPosition] = []
    if redis_client.exists(holding_position_key) == 1:
        retrieved_object = redis_client.get(holding_position_key)   
        json_data = json.loads(retrieved_object)        
        for obj in json_data:
            result.append(HoldingPosition(obj['Symbol'], obj['Token'], obj['BuyPrice'], obj['EntryCount'], obj['Status']))        

    return result

def setHold_monitoring(value):
    redis_client.set('Hold_monitoring', str(value))

def getHold_monitoring() -> bool:
    bool(redis_client.get('Hold_monitoring'))

def setExit_Session(value):
    redis_client.set('Exit_Session', str(value))

def getExit_Session():
    bool(redis_client.get('Exit_Session'))

def isCE_Position():
    if redis_client.exists('CE_Position') == 1:
        return redis_client.get('CE_Position') == 'True'
    else:
        return False

def isPE_Position():
    if redis_client.exists('PE_Position') == 1:
        return redis_client.get('PE_Position') == 'True'
    else:
        return False

def setCE_Position(value):
    bool(redis_client.set('CE_Position', str(value)))

def setPE_Position(value):
    bool(redis_client.set('PE_Position', str(value)))    

def increment_CE_Position_count():
    if redis_client.exists('CE_Position_Count') == 1:
        count = int(redis_client.get('CE_Position_Count'))
        redis_client.set('CE_Position_Count', count + 1)
    else:
        redis_client.set('CE_Position_Count', 1)

def increment_PE_Position_count():
    if redis_client.exists('PE_Position_Count') == 1:
        count = int(redis_client.get('PE_Position_Count'))
        redis_client.set('PE_Position_Count', count + 1)
    else:
        redis_client.set('PE_Position_Count', 1)

def is_CE_Reentry_limit_reached():
    if redis_client.exists('CE_Position_Count') == 1 and not redis_client.get('CE_Position_Count') is None:
        return int(redis_client.get('CE_Position_Count')) > int(config.NO_OF_ENTRIES)
    return False

def is_PE_Reentry_limit_reached():
    if redis_client.exists('PE_Position_Count') == 1 and not redis_client.get('PE_Position_Count') is None:
        return int(redis_client.get('PE_Position_Count')) > int(config.NO_OF_ENTRIES)
    return False

def get_CE_Position_count():
    if redis_client.exists('CE_Position_Count') == 1 and not redis_client.get('CE_Position_Count') is None:
        return int(redis_client.get('CE_Position_Count'))
    return 0

def get_PE_Position_count():
    if redis_client.exists('PE_Position_Count') == 1 and not redis_client.get('PE_Position_Count') is None:
        return int(redis_client.get('PE_Position_Count'))
    return 0

def set_subscribe_tokens(token):
    if redis_client.exists('subscribe_tokens') == 1:
        tokens = redis_client.get('subscribe_tokens')
        tokens = f'{tokens},{token}'
        redis_client.set('subscribe_tokens', tokens)
    else:
        redis_client.set('subscribe_tokens', token)

def get_subscribe_tokens():
    if redis_client.exists('subscribe_tokens') == 1:
        return redis_client.get('subscribe_tokens')
    return None

def setCE_Position_premium(value):
    redis_client.set('CE_Position_premium', str(value))

def setPE_Position_premium(value):
    redis_client.set('PE_Position_premium', str(value))

def getCE_Position_premium(value):
    return float(redis_client.get('CE_Position_premium'))

def getPE_Position_premium(value):
    return float(redis_client.get('PE_Position_premium'))

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
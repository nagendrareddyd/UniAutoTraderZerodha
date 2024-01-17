from asyncio import constants
from time import sleep
from  order import Order
import redis
from loggingConfig import get_logger,setup_logging
import optionsUtilities
import config
import sessionVariables
from sessionVariables import HoldingPosition
import asyncio
import pytz
from datetime import datetime
import time
from tzlocal import get_localzone
import math
from order import Order
import ordermanagement
import utilities

setup_logging()
logger = get_logger(__name__)
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)

def startStrategyProcess():
    logger.info('started strategy')
    if redis_client.exists('Access_Token') != 1 :
        access_token = utilities.generate_access_token()
        logger.info(f'ACCESS TOKEN - {access_token}')
        redis_client.set('Access_Token', access_token)
        access_token = redis_client.get('Access_Token')

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start())
    loop.close()

async def start():

    ResetAllKeys()
    
    WaitForStartTime()

    # find the range high and low
    (rangeHigh, rangeLow) = SetRangeHighAndLow()
    logger.info(f'Range High - {rangeHigh} , Range Low - {rangeLow}')
    
    # wait until the buy signal
    while True:

        try:
            underlyingstockLtp = float(redis_client.get(config.INSTRUMENT_TOKEN))
        except Exception as e: 
            logger.error('Error')
            sleep(1)

        if underlyingstockLtp > rangeHigh and not sessionVariables.isCE_Position() and sessionVariables.get_CE_Position_count() == 0:
            # buy CE ATM
            logger.info("Range high breakout")
            sessionVariables.setCE_Position(True)
            sessionVariables.increment_CE_Position_count()
            placeOrder('CE')
            
            
        if underlyingstockLtp < rangeLow and not sessionVariables.isPE_Position() and sessionVariables.get_PE_Position_count() == 0:
            # buy PE ATM
            logger.info("Range low breakout")
            sessionVariables.setPE_Position(True)
            sessionVariables.increment_PE_Position_count()
            placeOrder('PE')
            
        if sessionVariables.get_CE_Position_count() != 0 and sessionVariables.get_PE_Position_count() != 0:
            break

def placeOrder(optiontype):
    (symbol) = optionsUtilities.get_nearest_symbol_info(config.EXCHANGE, optiontype)
    logger.info(f'Order placed for {symbol}')
    order = Order(symbol, 'BUY', '', config.LOT_QUANTITY, config.STRATEGY_CODE,'','','')
    ordermanagement.placeOrder(order)
    sleep(1)


def processedOrders(order: Order): 
    if order.status == 'COMPLETE':
        if order.transaction_type == 'BUY':
            logger.info("BUY transaction of " + str(order.instrument_token))
            redis_client.set(order.instrument_token, order.averagePrice)
            if str(order.tradingsymbol).endswith('CE'):
                entrycount = sessionVariables.get_CE_Position_count()
            else:
                entrycount = sessionVariables.get_PE_Position_count()
            
            sessionVariables.StoreOrUpdateHoldingPsitions(HoldingPosition(order.tradingsymbol, str(order.instrument_token),order.averagePrice, entrycount, 'Active'))
            sessionVariables.setHold_monitoring(False)

        else:
            logger.info("Updating Sell order in holding position to completed")
            
            sessionVariables.RemoveHoldingPsition(order.tradingsymbol)
        sessionVariables.RemoveOrderFromCache(order.orderid)
    logger.info("Completed processing order")

def startMonitoringPositions():
    logger.info('Started monitoring positions')
    while True:

        #TODO: modify this to check if all the re-entries are completed the sell order also
        # if sessionVariables.is_CE_Reentry_limit_reached() and sessionVariables.is_CE_Reentry_limit_reached():
        #     break

        if len(sessionVariables.getOrdersFromCache()) != 0:
            for order in sessionVariables.getOrdersFromCache():
                if order.status == 'COMPLETE':
                    processedOrders(order)

        if len(sessionVariables.getHoldingPositions()) == 0 or sessionVariables.getHold_monitoring():
            continue

        if check_exit_time_reached():
           break 
        
        for holdingPsition in sessionVariables.getHoldingPositions():
            if redis_client.exists(holdingPsition.Token) == 0:
                continue

            position_current_price = redis_client.get(holdingPsition.Token)

            if holdingPsition.Status == 'Completed':
                if float(holdingPsition.BuyPrice) <= float(position_current_price):
                    if holdingPsition.Symbol.endswith('CE') and not sessionVariables.isCE_Position() and not sessionVariables.is_CE_Reentry_limit_reached():
                        logger.info(f'Reached re-entry for CE, trading symbol - {holdingPsition.Symbol}')
                        order = Order(holdingPsition.Symbol, 'BUY','', config.LOT_QUANTITY, config.STRATEGY_CODE,'','','')
                        ordermanagement.placeOrder(order)
                        sessionVariables.setCE_Position(True)
                        sessionVariables.increment_CE_Position_count()
                        sleep(1)
                        continue
                    if holdingPsition.Symbol.endswith('PE') and not sessionVariables.isPE_Position() and not sessionVariables.is_PE_Reentry_limit_reached():
                        logger.info(f'Reached re-entry for PE, trading symbol - {holdingPsition.Symbol}')
                        sessionVariables.setPE_Position(True)
                        sessionVariables.increment_PE_Position_count()
                        order = Order(holdingPsition.Symbol, 'BUY','', config.LOT_QUANTITY, config.STRATEGY_CODE,'','','')
                        ordermanagement.placeOrder(order)
                        sleep(1)
                        continue

            if holdingPsition.Status == 'Active' and is_stoploss_hit(float(holdingPsition.BuyPrice), float(position_current_price), int(config.STOP_LOSS_PERCENTAGE)):
                if holdingPsition.Symbol.endswith('CE') and sessionVariables.isCE_Position():
                    logger.info(f'Reached stop loss for CE, trading symbol - {holdingPsition.Symbol}')
                    sessionVariables.setCE_Position(False)
                    order = Order(holdingPsition.Symbol, 'SELL','', config.LOT_QUANTITY, config.STRATEGY_CODE,'','','')
                    ordermanagement.placeOrder(order)
                    sleep(1)
                   
                elif sessionVariables.isPE_Position():
                    logger.info(f'Reached stop loss for PE, trading symbol - {holdingPsition.Symbol}')
                    sessionVariables.setPE_Position(False)
                    order = Order(holdingPsition.Symbol, 'SELL','', config.LOT_QUANTITY, config.STRATEGY_CODE,'','','')
                    ordermanagement.placeOrder(order)
                    sleep(1)

def WaitForStartTime():
    # wait untill - 9:36 - india time
    local_time = datetime.now()

    starthourandMinute = config.ENTRY_TIME.split(':')
    target_time = datetime(local_time.year, local_time.month, local_time.day, int(starthourandMinute[0]), int(starthourandMinute[1]), 0)

    current_time = datetime.now()

    # Calculate the time difference in seconds
    time_difference = (target_time - current_time).total_seconds()
    if time_difference > 0:
        print("Waiting for", time_difference, "seconds...")
        logger.info(f'Waiting for {time_difference} seconds...')
        time.sleep(time_difference)
        print("Time's up! It's now", target_time)
        logger.info(f'Time up! It now {target_time}')
    else:
        print("The target time has already passed.")

def SetRangeHighAndLow():
    rangeHigh = 0
    rangeLow = 1000000

    while isTimeInRange():
        try:
            underlyingStockLtp = redis_client.get(config.INSTRUMENT_TOKEN)
            if rangeHigh < float(underlyingStockLtp):
                rangeHigh = float(underlyingStockLtp)
            if rangeLow > float(underlyingStockLtp):
                rangeLow = float(underlyingStockLtp)
        except Exception as e: 
            logger.error('error')
    return rangeHigh, rangeLow

def isTimeInRange():    
    local_time = datetime.now()

    rangeEndTime =  config.RANGE_END_TIME.split(':')

    end_time = datetime(year=local_time.year, month=local_time.month, day=local_time.day, hour=int(rangeEndTime[0]), minute=int(rangeEndTime[1]), second=0)
    current_time = datetime.now()

    time_difference = (end_time - current_time).total_seconds()
    return time_difference > 0

def is_stoploss_hit(oldvalue, newvalue, percentage):
    return newvalue <= oldvalue - (oldvalue/100 * percentage)

def check_exit_time_reached():
    local_timezone = get_localzone()
    original_timezone = pytz.timezone(str(local_timezone))
    local_time = datetime.now()

    exitTime =  config.EXIT_TIME.split(':')
    original_datetime = original_timezone.localize(datetime(local_time.year, local_time.month, local_time.day, int(exitTime[0]), int(exitTime[1]), 0))

    # Convert the datetime to a different timezone
    target_timezone = pytz.timezone('Asia/Kolkata')
    exit_time = original_datetime.astimezone(target_timezone)
    current_time = datetime.now(target_timezone)

    if exit_time.hour == current_time.hour and exit_time.minute == current_time.minute:
        exit_all_positions()
        sleep(1)
        return True
    
    return False

def exit_all_positions():
    logger.info('Reached exit time - exit all active positions')
    for holdingPsition in sessionVariables.getHoldingPositions():
        if redis_client.exists(holdingPsition.Token) == 0:
            continue
        if holdingPsition.Status == 'Active':
            order = Order(holdingPsition.Symbol, 'SELL','', config.LOT_QUANTITY, config.STRATEGY_CODE,'','','')
            ordermanagement.placeOrder(order)
            sleep(1)

def ResetAllKeys():
    redis_client.delete("PE_Position")
    redis_client.delete("CE_Position")
    redis_client.delete("PE_Position_Count")
    redis_client.delete("CE_Position_Count")
    redis_client.delete("holding_positions")
    redis_client.delete("Hold_monitoring")
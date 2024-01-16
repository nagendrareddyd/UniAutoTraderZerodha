from dataclasses import dataclass
import json
import config
import pandas as pd

def storeOrderToJsonFile(executedOrder, initialprice):
     #store in a json file

    # cal p&l
    pnl = 0
    if executedOrder['transaction_type'] == 'BUY':
        pnl = initialprice - float(executedOrder['average_price'])

    executed_order = {
        "order_id": executedOrder['order_id'],
        "trading_symbol": executedOrder['tradingsymbol'],
        "instrument_token": str(executedOrder['instrument_token']),
        "average_price":executedOrder['average_price'],
        "pnl": pnl
    }
    json_string = json.dumps(executed_order)
    file_path = config.SESSION_ORDERS_FILE

    # Write the updated data back to the file
    with open(file_path, 'a') as file:
        json.dump(json_string, file, indent=4)

def generate_access_token():
  creds={'api_key': config.API_KEY, 'api_secret': config.API_SECRET, 'user_id': config.USER_ID, 'user_pwd': config.PASSWORD, 'totp_key': config.TOTP_KEY}

  import requests, json
  from pyotp import TOTP
  from kiteconnect import KiteConnect
  # import pandas as pd, datetime as dt, xlwings as xw, numpy as np
  import pandas as pd, datetime as dt, numpy as np
  from multiprocessing.dummy import Pool as ThreadPool
  
  class CustomError(Exception):
    pass

  login_url = "https://kite.zerodha.com/api/login"
  twofa_url = "https://kite.zerodha.com/api/twofa"

  session = requests.Session()

  response=session.post(login_url,data={'user_id':creds['user_id'],'password':creds['user_pwd']})
  request_id = json.loads(response.text)['data']['request_id']
  twofa_pin = TOTP(creds['totp_key']).now()
  api_key = creds['api_key']
  api_secret = creds['api_secret']

  response_1=session.post(twofa_url,data={'user_id':creds['user_id'],'request_id':request_id,'twofa_value':twofa_pin,'twofa_type':'totp'})

  kite = KiteConnect(api_key = api_key)
  kite_url = kite.login_url()

  # This is the killer part. This is amazingly extract the request id without opening the url in the browser.
  access_token='DUMMY'
  try:
    # print(kite_url)
    session.get(kite_url)
    
  except Exception as e:
    e_msg = str(e)
    #print(e_msg)
    
    request_token = e_msg.split('request_token=')[1].split(' ')[0].split('&action')[0]
    # print('Successful Login with Request Token:{}'.format(request_token))
    data = kite.generate_session(request_token, api_secret=api_secret)
    access_token = data['access_token']
  if access_token=='DUMMY':
    raise CustomError("access token did not generated")
  return access_token
      
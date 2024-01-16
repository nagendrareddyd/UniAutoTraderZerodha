import config
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

def options_instruments(p_kite, p_json_path, p_index='BANKNIFTY', p_contract_exp='w1'):
    import pandas as pd
    instruments_df = pd.DataFrame (p_kite.instruments (exchange='NFO'))
    options_df = instruments_df[(instruments_df['segment'] == 'NFO-OPT') & (instruments_df['name']==p_index)] #the original data that downloaded from Zerodha for all the instruments
    sorted_exp_dates=options_df.expiry.drop_duplicates().sort_values()
    exp_date=sorted_exp_dates.iloc[0]
    if p_contract_exp.lower() in ['w1','w2','w3', 'w4', 'w5']:
        exp_date=sorted_exp_dates.iloc[int(p_contract_exp[1])-1]
    options_df = options_df[options_df['expiry']==exp_date]
        
    ce_df = options_df[options_df['instrument_type']=='CE'][["strike", "instrument_token","tradingsymbol"]]
    ce_df=ce_df.rename(columns={'tradingsymbol': 'CE_symbol',"instrument_token":"CE_instrument_token"})
    pe_df = options_df[options_df['instrument_type']=='PE'][["strike", "instrument_token","tradingsymbol"]]
    pe_df=pe_df.rename(columns={'tradingsymbol': 'PE_symbol',"instrument_token":"PE_instrument_token"})
    
    options_df = ce_df.merge(pe_df)
    
    options_df.strike = options_df.strike.astype(int)
        
    options_df.to_json(p_json_path, orient='records')
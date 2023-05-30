import requests
import json
import time
import copy

## tokens ##
delay = 120
last_order = None
last_order_2 = None
account_id = ''
client_id = ''
channel = ''
channel_2 = ''
discord_token = ''
discord_token_2 = ''
refresh_token = ''
stock_list = []

def authenticate():
    # define the endpoint
    url = r"https://api.tdameritrade.com/v1/oauth2/token"

    # define authentication headers
    headers = {"Content-Type":"application/x-www-form-urlencoded"}

    # define the payload
    auth_payload = {'grant_type': 'refresh_token', 
               'refresh_token': refresh_token,
               'client_id': client_id}

    # post the data to get the token
    authReply = requests.post(r'https://api.tdameritrade.com/v1/oauth2/token', headers=headers, data=auth_payload)

    # convert it to a dictionary
    decoded_content = authReply.json()                       

    # grab the access_token
    access_token = decoded_content['access_token']

    # define order headers
    header = {'Authorization':"Bearer {}".format(access_token),
              "Content-Type":"application/json"}

    # define the endpoint for orders
    endpoint = r"https://api.tdameritrade.com/v1/accounts/{}/orders".format(account_id)

    return endpoint, header

# retrieve contents of most recent discord message
def retrieve_messages(token, channelid):
    headers = {
        'authorization': token
        }
    r = requests.get(f'https://discord.com/api/v8/channels/{channelid}/messages', headers=headers)
    js = json.loads(r.text)
    print(js[0]['content'])
    msg = js[0]['content'].split()
    return msg

def convert_to_stop(order, sl, price):
    json = copy.deepcopy(order)
    if sl != False:
        json["stopPrice"] = str(round(float(json["price"]) * sl, 2))
    elif price != False:
        json["stopPrice"] = price
    del json["price"]
    json["orderLegCollection"][0]["instruction"] = "SELL_TO_CLOSE"
    json["orderType"] = "STOP"
    return json

# decode contents of message to modify order template
def parse(message):
    #msg = ['BTO', 'QQQ', '324P', '5/24', '@.60', 'Trimming', '(Tight', '(SL', '@.50)'] FORMAT
    #msg = ['BTO', 'QQQ', '326P', '5/24', '@1.26'] FORMAT
    msg = message[1:]
    order_type = ""
    price = ""
    if msg[0] == 'BTO':
        order_type = "BUY_TO_OPEN"
        price = (str(float(msg[4][1:]) + 0.02))
    elif msg[0] == 'STC':
        order_type = "SELL_TO_CLOSE"
        price = (str(float(msg[4][1:]) - 0.05))
    else:
        return False
    stock = msg[1]
    d = msg[3].split('/')
    date = d[0].zfill(2) + d[1].zfill(2) + '23'
    option_type = msg[2][-1] + msg[2].rstrip(msg[2][-1])
    symbol = stock + "_" + date + option_type
    #price = msg[4][1:]

    quantity = 3

    # trim 50%
    for m in msg:
        if "Trim" in m:
            quantity = 2

    # buy/sell order template
    full_order = {
      "complexOrderStrategyType": "NONE",
      "orderType": "LIMIT",
      "session": "NORMAL",
      "price": "6.45",
      "duration": "DAY",
      "orderStrategyType": "SINGLE",
      "orderLegCollection": [
        {
          "instruction": "SELL_TO_CLOSE",
          "quantity": 1,
          "instrument": {
            "symbol": "XYZ_032015C49",
            "assetType": "OPTION"
            }
        }
      ]
    }

    # replace values in json
    full_order["price"] = price
    full_order["orderLegCollection"][0]["instruction"] = order_type
    full_order["orderLegCollection"][0]["quantity"] = quantity
    full_order["orderLegCollection"][0]["instrument"]["symbol"] = symbol

    full_order = json.dumps(full_order)
    #print(full_order)
    full_order = json.loads(full_order)
    main_order = copy.deepcopy(full_order)
    
    # stop loss check
    sl_index = -1
    if "SL" in msg:
        sl_index = msg.index("SL")
    elif "(SL" in msg:
        sl_index = msg.index("(SL")
    else:
        full_order = None
    if sl_index != -1:
        if ")" in msg[sl_index + 1]:
            msg[sl_index + 1] = msg[sl_index + 1][1:-1]
        else:
            msg[sl_index + 1] = msg[sl_index + 1][1:]
        full_order = convert_to_stop(full_order, False, msg[sl_index + 1])

    full_order = json.dumps(full_order)
    #print(full_order)
    full_order = json.loads(full_order)

    print(main_order, full_order)
    return main_order, full_order

def parse_2(message):
    msg = message
    # msg = ["QQQ", "5/24", "337P", "at", "1.70"] FORMAT
    if msg[0].isupper() or msg[0][1:].isupper():
        order_type = "BUY_TO_OPEN"
        if "$" in msg[0]:
            stock = msg[0][1:]
        else:
            stock = msg[0]
        d = msg[1].split('/')
        date = d[0].zfill(2) + d[1].zfill(2) + '23'
        option_type = msg[2][-1] + msg[2].rstrip(msg[2][-1])
        symbol = stock + "_" + date + option_type
        price = ""
        if "$" in msg[4]:
            price = (str(float(msg[4][1:]) + 0.02))
        else:
            price = (str(float(msg[4]) + 0.02))

        full_order = {
          "complexOrderStrategyType": "NONE",
          "orderType": "LIMIT",
          "session": "NORMAL",
          "price": "6.45",
          "duration": "DAY",
          "orderStrategyType": "SINGLE",
          "orderLegCollection": [
            {
              "instruction": "SELL_TO_CLOSE",
              "quantity": 1,
              "instrument": {
                "symbol": "XYZ_032015C49",
                "assetType": "OPTION"
                }
            }
          ]
        }

        quantity = 1

        # replace values in json
        full_order["price"] = price
        full_order["orderLegCollection"][0]["instruction"] = order_type
        full_order["orderLegCollection"][0]["quantity"] = quantity
        full_order["orderLegCollection"][0]["instrument"]["symbol"] = symbol
        
        stock_list.append([stock, full_order])
        return full_order
    else:
        for m in msg:
            if "trim" in m or "out" in m:
                for m2 in msg:
                    if m2.isupper():
                        for i in range(len(stock_list)):
                            if stock_list[i][0] == m2:
                                # sell to close
                                stock_list[i][1]["orderLegCollection"][0]["instruction"] = "SELL_TO_CLOSE"
                                #stock_list[i][1]["orderType"]: "MARKET"
                                #stock_list[i][1]["price"] = (str(float(price) - 0.07))
                                stock_list[i][1]["price"] = "0.01"
                                main_order = copy.deepcopy(stock_list[i][1])
                                stock_list.pop(i)
                                return main_order
        return False

    
while(True):
    try:
        # define the payload in json format
        payload, stop_order = parse(retrieve_messages(discord_token, channel))
        if payload == False or last_order == payload:
            print('passed')
            pass 
        else:
            endpoint, header = authenticate()

            # make a post
            content = requests.post(url = endpoint, json = payload, headers = header)

            # show the status code
            print(content.status_code)
            last_order = payload

            if payload["orderLegCollection"][0]["instruction"] == "SELL_TO_CLOSE":
                pass
            elif stop_order is None:
                print("stop_order_manual")
                stop = convert_to_stop(payload, 0.8, False)
                time.sleep(1)
                content = requests.post(url = endpoint, json = stop, headers = header)
            elif stop_order is not None:
                print("stop_order_auto")
                time.sleep(1)
                content = requests.post(url = endpoint, json = stop_order, headers = header)
                print(content.status_code)
    except:
        print("Not valid.")

    try:
        payload_2 = parse_2(retrieve_messages(discord_token_2, channel_2))
        if payload_2 == False or last_order_2 == payload_2:
            print('passed_2')
            pass
        else:
            endpoint, header = authenticate()

            # make a post
            content = requests.post(url = endpoint, json = payload_2, headers = header)

            # show the status code
            print(content.status_code)
            last_order_2 = payload_2

            # send stop order
            if payload_2["orderLegCollection"][0]["instruction"] == "SELL_TO_CLOSE":
                pass
            else:
                print("stop_order_manual_2")
                stop = convert_to_stop(payload_2, 0.8, False)
                time.sleep(1)
                content = requests.post(url = endpoint, json = stop, headers = header)
    except:
        print("Not valid. (2)")
        
    time.sleep(delay)

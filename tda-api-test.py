import requests
import json
import time
from datetime import datetime
import copy

## tokens ##
delay = 60
account_id = ''
client_id = ''
channel_list = ['', '']
discord_token_list = ['', '']
last_message_list = ['', '']
refresh_token = ''
access_token = input("Access Token: ")
token_count = 0

def get_order_template():
    return {
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

def authenticate():
    global token_count
    token_count += 1
    print("token generated! - " + str(token_count))
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
    global access_token
    access_token = decoded_content['access_token']
    print(access_token)
    return None

def get_order_headers():
    # define the endpoint for orders
    endpoint = r"https://api.tdameritrade.com/v1/accounts/{}/orders".format(account_id)

    # define order headers
    header = {'Authorization':"Bearer {}".format(access_token),
              "Content-Type":"application/json"}
    return endpoint, header

def get_position_headers():
    # define the endpoint for positions
    endpoint = r"https://api.tdameritrade.com/v1/accounts/{}?fields=positions".format(account_id)
    
    # define position headers
    header = {'Authorization':"Bearer {}".format(access_token),
              "Content-Type":"application/json"}
    return endpoint, header

# retrieve contents of most recent discord message
def retrieve_messages(token, channelid):
    headers = {
        'authorization': token
        }
    r = requests.get(f'https://discord.com/api/v8/channels/{channelid}/messages', headers=headers)
    js = json.loads(r.text)
    print(js[0]['content'][0:50])
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
    json["duration"] = "GOOD_TILL_CANCEL"
    return json

def check_auth():
    endpoint, header = get_position_headers()
    response = requests.get(url = endpoint, headers = header)
    if response.status_code == 401:
        authenticate()
        return check_auth()
    return response

def get_orders(symbol):
    orders = []
    response = check_auth()
    content = json.loads(response.content.decode('ascii'))
    positions = content["securitiesAccount"]["positions"]
    
    for i in range(len(positions)):
        if positions[i]["instrument"]["assetType"] == "OPTION" and positions[i]["instrument"]["underlyingSymbol"] == symbol:
            quantity = positions[i]["longQuantity"]
            symbol = positions[i]["instrument"]["symbol"]
            orders.append([symbol, quantity])
    return orders

def check_exist(payload):
    order = payload["orderLegCollection"][0]
    if order["instruction"] != "SELL_TO_CLOSE" and len(get_orders(order["instrument"]["symbol"].split("_")[0])) > 0:
        return True
    return False

def sell(symbol):
    orders = get_orders(symbol)
    full_order = get_order_template()
    full_order["orderLegCollection"][0]["instruction"] = "SELL_TO_CLOSE"
    full_order["orderType"] = "MARKET"
    full_order["duration"] = "GOOD_TILL_CANCEL"
    del full_order["price"]
    #print("found order!")
    print(orders)
    for i in range(len(orders)):
         full_order["orderLegCollection"][0]["instrument"]["symbol"] = orders[i][0]
         full_order["orderLegCollection"][0]["quantity"] = orders[i][1]
    return full_order

# decode contents of message to modify order template
def parse(message):
    #msg = ['BTO', 'QQQ', '324P', '5/24', '@.60', 'Trimming', '(Tight', '(SL', '@.50)']
    #msg = ['BTO', 'QQQ', '326P', '6/9', '@0.01']
    msg = message[1:]
    full_order = get_order_template()
    order_type = ""
    price = ""
    stock = msg[1]
    d = msg[3].split('/')
    date = d[0].zfill(2) + d[1].zfill(2) + '23'
    option_type = msg[2][-1] + msg[2].rstrip(msg[2][-1])
    symbol = stock + "_" + date + option_type
    if msg[0] == 'BTO':
        order_type = "BUY_TO_OPEN"
        price = (str(float(msg[4][1:]) + 0.03))
    if msg[0] == 'STC':
        order_type = "SELL_TO_CLOSE"
        full_order["duration"] = "GOOD_TILL_CANCEL"
        price = (str(float(msg[4][1:]) - 0.05))

    quantity = 3
    # trim 50%
    for m in msg:
        if "Trim" in m:
            quantity = 2
    
    # replace values in json
    full_order["orderType"] = "LIMIT"
    full_order["price"] = price
    full_order["orderLegCollection"][0]["instruction"] = order_type
    full_order["orderLegCollection"][0]["quantity"] = quantity
    full_order["orderLegCollection"][0]["instrument"]["symbol"] = symbol
    return full_order

def parse_2(message):
    msg = message
    keywords = ['call', 'calls', 'put', 'puts']
    sell_keywords = ['rim', 'out', 'lose', 'tak', 'Tak']
    full_order = get_order_template()
    # msg = ["QQQ", "5/24", "337P", "at", "1.70"]
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
        price = price = (str(float(msg[4]) + 0.03))
        p = 3
        if "." in msg[4]:
            p = 4
        if "$" in msg[p]:
            price = (str(float(msg[p][1:]) + 0.03))
        quantity = 1

        # replace values in json
        full_order["orderType"] = "LIMIT"
        full_order["price"] = price
        full_order["orderLegCollection"][0]["instruction"] = order_type
        full_order["orderLegCollection"][0]["quantity"] = quantity
        full_order["orderLegCollection"][0]["instrument"]["symbol"] = symbol
        return full_order
    else:
        for m in msg:
            if [x for x in sell_keywords if(x in m)]:
                for m2 in msg:
                    if m2.isupper() and m2.isalpha():
                        return sell(m2)
                if any(x in keywords for x in msg):
                    for i in range(len(msg)):
                        if any(x in keywords for x in [msg[i]]) and msg[i-1].isalpha() and len(msg[i-1]) > 3 and len(msg[i-1]) < 6:
                            return sell(msg[i-1].upper())
        return None
    
def send_payload(payload):
    endpoint, header = get_order_headers()

    # make a post
    content = requests.post(url = endpoint, json = payload, headers = header)

    # show the status code
    print(str(payload) + " __" + str(content.status_code) + "__")

    # create stop limit order
    if payload["orderLegCollection"][0]["instruction"] == "BUY_TO_OPEN":
        stop = convert_to_stop(payload, 0.8, False)
        time.sleep(5)
        content = requests.post(url = endpoint, json = stop, headers = header)
        print(str(stop) + " __" + str(content.status_code) + "__")
    return None
    
while(True):
    check_auth()
    func = [parse, parse_2]
    for i in range(len(channel_list)):
        try:
            message = retrieve_messages(discord_token_list[i], channel_list[i])
            if last_message_list[i] == message:
                print(f'message previously read! ({i+1})')
            else:
                payload = func[i](message)
                if check_exist(payload):
                    print(f'order exists in account! ({i+1})') 
                else:
                    print(f'sending payload ({i+1})')
                    last_message_list[i] = message
                    send_payload(payload)
        except:
            print(f'Invalid request. ({i+1})')

    print("==[" + datetime.now().strftime("%m/%d %H:%M:%S") + "]==")
    time.sleep(delay)

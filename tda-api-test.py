import requests
import json
import time
from datetime import datetime
import copy
import sqlite3

## tokens ##
tokens = open("tokens.txt","r")
lines = tokens.read().splitlines()
account_id, client_id, channel_list, discord_token_list, refresh_token, output = lines[0], lines[1], lines[2].split(), lines[3].split(), lines[4], lines[5]
tokens.close()
access_token = input("Access Token: ")
last_message_list = [None, None]
delay = 5
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
    #print(js[0]['content'][0:50])
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

def transact(symbol, prices, quantity, action):
    orders = get_orders(symbol) # ['AAPL_100623P175', 2]
    full_order = get_order_template()
    if action == 0:
        full_order["orderLegCollection"][0]["instruction"] = "SELL_TO_CLOSE"
        full_order["duration"] = "GOOD_TILL_CANCEL"
        full_order["orderType"] = "MARKET"
        del full_order["price"]
    elif action == 1:
        full_order["orderLegCollection"][0]["instruction"] = "BUY_TO_OPEN"
        full_order["duration"] = "DAY"
        full_order["orderType"] = "LIMIT"
        full_order["price"] = prices[0]
    
    #print("found order!")
    for i in range(len(orders)):
        full_order["orderLegCollection"][0]["instrument"]["symbol"] = orders[i][0]
        if action == 1:
            if orders[i][1] > 2:
                full_order["orderLegCollection"][0]["quantity"] = 0
        else:
            if quantity > orders[i][1]:
                full_order["orderLegCollection"][0]["quantity"] = orders[i][1]
            else:  
                full_order["orderLegCollection"][0]["quantity"] = quantity
    print(orders)
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
        price = (str(round(float(msg[4][1:]) + 0.05, 2)))
    if msg[0] == 'STC':
        order_type = "SELL_TO_CLOSE"
        full_order["duration"] = "GOOD_TILL_CANCEL"
        price = (str(round(float(msg[4][1:]) - 0.10, 2)))

    quantity = 1
    # trim 50%
    for m in msg:
        if "Trim" in m:
            quantity = 1
    
    # replace values in json
    full_order["orderType"] = "LIMIT"
    full_order["price"] = price
    full_order["orderLegCollection"][0]["instruction"] = order_type
    full_order["orderLegCollection"][0]["quantity"] = quantity
    full_order["orderLegCollection"][0]["instrument"]["symbol"] = symbol
    return full_order

def db_most_recent():
    conn = sqlite3.connect('stock_list.db')
    cursor = conn.execute("SELECT * FROM TRADE ORDER BY ID DESC LIMIT 1;")
    header, symbol = "", ""
    for row in cursor:
        header = row[1]
        symbol = row[2]
    conn.close()
    return header, symbol

def db_insert(header, ticker, price):
    conn = sqlite3.connect('stock_list.db')
    query = "INSERT INTO TRADE (HEADER,TICKER,PRICE) VALUES ('{}', '{}', '{}')".format(header, ticker, price)
    conn.execute(query)
    conn.commit()
    conn.close()

def check_stock(message):
    stock_list = ["MSFT", "AMZN", "SPY", "NVDA", "META", "NFLX", "GOOGL", "AAPL", "TSLA", "AMD", "ROKU", "DIS", "ORCL", "BABA", "COIN", "SPOT", "SHOP", "QQQ", "SNOW", "SPX"]
    stock_dict = {"AMAZON" : "AMZN",
              "TESLA": "TSLA",
              "APPLE": "AAPL"}
    upper_msg = [x.upper() for x in message]
    upper_msg = [stock_dict.get(item,item) for item in upper_msg]
    price_list = []
    for word in message:
        if "." in word:
            w = ''.join(i for i in word if i.isdigit() or i in './\\')
            if w[0] == ".":
                w = "0" + w
            price_list.append(w)
    return [i for i in upper_msg if i in stock_list], price_list

def parse_2(message):
    msg = message
    sell_phrases = ['rim', 'Out', 'out', 'lose', 'tak', 'Tak', 'Cut', 'cut', 'ash', 'top', 'xit']
    trim_phrases = ['rim', 'some', 'more']
    full_order = get_order_template()
    # msg = ["QQQ", "5/24", "337P", "at", "1.70"]
    # msg = ["$AVGO", "6/9", "850C", "at", "$4.70"]
    # msg = "Good gains on DIS here. Bid to ask a little whacky but 5.10-5.60 currently. Feel free to take gains if you’d like. I’ll swing".split()
    if msg[0].isupper() or msg[0][1:].isupper():
        order_type = "BUY_TO_OPEN"
        stock = msg[0]
        d = msg[1].split('/')
        date = d[0].zfill(2) + d[1].zfill(2) + '23'
        option_type = msg[2][-1] + msg[2].rstrip(msg[2][-1])
        symbol = stock + "_" + date + option_type
        p = 3
        if "." in msg[4] or msg[4][1] == ",":
            p = 4
        if msg[4][1] == ",":
            msg[4][1] == "."
        price = round(float(msg[p]) + 0.05, 2)

        quantity = 1
        if price < 3:
            quantity = 2
        if price < 1:
            quantity = 3

        price = str(price)

        # replace values in json
        full_order["orderType"] = "LIMIT"
        full_order["price"] = price
        full_order["orderLegCollection"][0]["instruction"] = order_type
        full_order["orderLegCollection"][0]["quantity"] = quantity
        full_order["orderLegCollection"][0]["instrument"]["symbol"] = symbol
        db_header, db_symbol = db_most_recent()
        print("DB: {}".format(db_header))
        if symbol != db_symbol:
            db_insert(symbol, stock.upper(), float(price))
        return full_order
    elif "avg" in msg or "add" in msg:
        ticker_list, prices = check_stock(msg)
        return transact(ticker_list[0], prices, 1, 1)
    else:
        quantity = 2
        ticker_list, prices = check_stock(msg)
        sell = False
        for word in msg:
            if [x for x in sell_phrases if(x in word)]:
                sell = True
                if [y for y in trim_phrases if(y in word)]:
                    quantity = 1
        if len(ticker_list) > 0 and sell:
            print("b")
            return transact(ticker_list[0], prices, quantity, 0)
        elif sell:
            print("c")
            header, symbol = db_most_recent()
            print(header, symbol)
            return transact(symbol, prices, quantity, 0)
    return None
    
def send_payload(payload, f):
    endpoint, header = get_order_headers()

    # make a post
    content = requests.post(url = endpoint, json = payload, headers = header)

    # show the status code
    print(str(payload) + " __" + str(content.status_code) + "__", file=f)

    # create stop limit order
    if payload["orderLegCollection"][0]["instruction"] == "BUY_TO_OPEN":
        stop = convert_to_stop(payload, 0.7, False)
        time.sleep(5)
        content = requests.post(url = endpoint, json = stop, headers = header)
        print(str(stop) + " __" + str(content.status_code) + "__", file=f)
    return None

while(True):
    func = [parse, parse_2]
    # debug = [cur_print, cur_print_2]
    with open(output, "a") as f:
        for i in range(len(channel_list)):
            try:
                message = retrieve_messages(discord_token_list[i], channel_list[i])
                #message = ["adding more to", "META", "10/6 175P at", "$2.35", "new", "avg"]
                #message = ["$AAPL", "10/6", "175P", "at", "$2.85"]
                for j in range(len(message)):
                    message[j] = message[j].replace('$', '')
                if last_message_list[i] == message:
                    pass
                    # print(f'message previously read! ({i+1})')
                else:
                    last_message_list[i] = message
                    check_auth()
                    print("==[" + datetime.now().strftime("%m/%d %H:%M:%S") + "]==", file=f)
                    print(" ".join([str(item) for item in message])[0:50], file=f)
                    payload = func[i](message)
                    if check_exist(payload) and "avg" not in message:
                        print(f'order exists in account! ({i+1})', file=f)
                    else:
                        if "avg" in message:
                            print('(avg)', file=f)
                        print(f'sending payload ({i+1})', file=f)
                        #print(payload, file=f)
                        send_payload(payload, f)
            except:
                print(f'Invalid request. ({i+1})', file=f)

    time.sleep(delay)

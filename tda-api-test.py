import requests
import json
import time

## tokens ##
delay = 120
last_order = None
account_id = ''
client_id = ''
channel = ''
discord_token = ''
refresh_token = ''

# retrieve contents of most recent discord message
def retrieve_messages(channelid):
    headers = {
        'authorization': discord_token
        }
    r = requests.get(f'https://discord.com/api/v8/channels/{channelid}/messages', headers=headers)
    js = json.loads(r.text)
    print(js[0]['content'])
    msg = js[0]['content'].split()
    return msg

# decode contents of message to modify order template
def parse(message):
    #msg = ['BTO', 'QQQ', '326P', '5/22', '@1.26']
    msg = message[1:]
    order_type = ""
    if msg[0] == 'BTO':
        order_type = "BUY_TO_OPEN"
    elif msg[0] == 'STC':
        order_type = "SELL_TO_CLOSE"
    else:
        return False
    stock = msg[1]
    d = msg[3].split('/')
    date = d[0].zfill(2) + d[1].zfill(2) + '23'
    option_type = msg[2][-1] + msg[2].rstrip(msg[2][-1])
    symbol = stock + "_" + date + option_type
    price = msg[4][1:]

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
          "quantity": 3,
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
    full_order["orderLegCollection"][0]["instrument"]["symbol"] = symbol

    full_order = json.dumps(full_order)
    print(full_order)
    full_order = json.loads(full_order)
    return full_order

while(True):
    try:
        # define the payload in json format
        payload = parse(retrieve_messages(channel))

        if payload == False or last_order == payload:
            print('passed')
            pass
        else:
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

            # make a post
            content = requests.post(url = endpoint, json = payload, headers = header)

            # show the status code
            print(content.status_code)
            last_order = payload
    except:
        print("Not valid.")       
    time.sleep(delay)



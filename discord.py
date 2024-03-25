import requests
import json
import time
import phemex_bot_2 as ph

## tokens ##
tokens = open("tokens.txt","r")
lines = tokens.read().splitlines()
account_id, client_id, channel_list, discord_token_list, refresh_token, output = lines[0], lines[1], lines[2].split(), lines[3].split(), lines[4], lines[5]
tokens.close()
db = "stock_list.db"
#access_token = input("Access Token: ")
last_message_list = [None, None, None]
delay = 5
token_count = 0

# retrieve contents of most recent discord message
def retrieve_messages(token, channelid, last):
    headers = {
        'authorization': token
        }
    r = requests.get(f'https://discord.com/api/v8/channels/{channelid}/messages', headers=headers)
    js = json.loads(r.text)
    #print(js[0]['content'][0:50])
    msg = js[last]
    return msg

last_message = ""
while(True):
    message = retrieve_messages(discord_token_list[2], channel_list[2], 0)['content']
    if (last_message != message):
        last_message = message
        #print(message)
        try:
            if ("LONG" in message or "SHORT" in message) and ("USDT" in message):
                cleaned = message.upper().replace(" ", "")
                lines = cleaned.split("\n")
                dir = ""
                entries = []
                profits = []
                if "SHORT" in lines:
                    dir = "SHORT"
                elif "LONG" in lines:
                    dir = "LONG"
                index = lines.index(dir)
                symbol = lines[index+1].replace("/", "")
                lev = lines[index+2].split(":")[1][:-1]
                qty = "1000"
                i = 0
                flag = True
                for line in lines:
                    if ")" in line:
                        val = line.split(")")
                        if int(val[0]) > i and flag:
                            entries.append(val[1])
                            i = int(val[0])
                        else:
                            profits.append(val[1])
                            flag = False
                    if "AMOUNT" in line:
                        qty = line.split("$")[1]
                        qty = qty.replace(",", "")
                qty = str(int(int(qty)/5 * int(lev) * 1/float(entries[0])))
                print(symbol, lev, entries, profits, qty)

                client = ph.Client("", "")
                #pos = client.query_position(currency="USDT", symbol="AVAXUSDT")
                #all_pos = pos["data"]["positions"]
                #for i in all_pos:
                    #print(i['symbol'], i['positionMarginRv'], i['avgEntryPriceRp'], i['markPriceRp'])
                params = {'symbol': symbol, 'side': "Buy", 'posSide': "Long", 'priceRp': entries[0], 'takeProfitRp': profits[0], 'orderQtyRq': qty}
                print(client.set_leverage(symbol = symbol, leverageRr = lev))
                print(client.place_hedged_order(params))
            print("t:", message[0:50])
        except:
            print("e:", message[0:50])

    time.sleep(5)
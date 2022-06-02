import random
import requests as r
from threading import Thread
import queue
from loguru import logger
from sys import stderr
from time import sleep
import names
from pyuseragents import random as u_a

logger.remove()
logger.add(stderr, format="<white>{time:HH:mm:ss}</white> | <level>{level: <8}</level> | <cyan>{line}</cyan> - <white>{message}</white>")

print(f"--== BY @Agubus ==--")

q = queue.Queue()

tokens = [a.replace("\n", "") for a in open(input("File with tokens --> "), "r").readlines()]

proxy_answer = input("Proxy y/n --> ")
if proxy_answer in ("Y", "y"):
    proxies = [a.replace("\n", "") for a in open(input("File with proxies --> "), "r").readlines()]

    print(
        "Proxy type",
        "1 - http",
        "2 - https",
        "3 - socks",
        sep="\n")

    types = ['http', 'https', 'http']
    proxy_type = types[int(input("--> "))]
else:
    proxies = [None]*len(tokens)

threads = int(input("Number of threads --> "))
if threads <= 0:
    raise Exception("Number of threads cant be less than 0 or equal to it")

print(
    "-----------------------",
    "1 - add reactions",
    "2 - get last messages in chat",
    "3 - send messages to chat",
    "4 - change names",
    "-----------------------",
    sep="\n")
task = int(input("Choose task --> "))

def add_reations(ses: r.Session, chat_id, message_ids, reactions):
    for message_id in message_ids:
        for reaction in reactions:
            for b in range(4):
                resp = ses.put(f"https://discord.com/api/v9/channels/{chat_id}/messages/{message_id}/reactions/{reaction}/%40me?location=Message")
                if resp.status_code == 204:
                    break
                else:
                    sleep(2)

                if b >= 3:
                    logger.error(f"Error with {ses.headers['authorization']}, {resp.status_code}, {resp.text}")
                    return

    logger.success(f"{ses.headers['authorization']} -- done")

def parse_last_msgs(ses: r.Session, chat_id, num):
    chat_name = ses.get(f"https://discord.com/api/v9/channels/{chat_id}").json()['name']

    resp = ses.get(f"https://discord.com/api/v9/channels/{chat_id}/messages?limit=100")
    msgs = []

    last_id = resp.json()[-1]["id"]

    msgs.extend(resp.json())

    while len(msgs) < num:

        resp = ses.get(f"https://discord.com/api/v9/channels/{chat_id}/messages?limit=100&before={last_id}")

        if resp.status_code == 200:
            msgs.extend(resp.json())
            last_id = resp.json()[-1]["id"]
        elif resp.status_code == 429:
            sleep(int(resp.json()['retry_after']))
            continue
        else:
            logger.error(f"Failed to parse messages {resp.status_code} {resp.text}")

    with open(f"{chat_name}.txt", "w", encoding="utf8") as f:
        for msg in msgs[:num]:
            f.write(msg["content"].replace("\n","")+"\n")

def send_messages(ses: r.Session, chat_id, message):
    _data = {'content': message, 'tts': False}

    try:
        resp = ses.post(f'https://discord.com/api/v9/channels/{chat_id}/messages', json=_data, timeout=2)
    except r.exceptions.ReadTimeout:
        sleep(10)
        send_messages(ses, chat_id, message)
        return

    if resp.status_code == 200:
        logger.success(f"Send message '{message}' with {ses.headers['authorization']}")
    elif resp.status_code == 429:
        sleep(int(resp.json()['retry_after']))
        send_messages(ses, chat_id, message)
    else:
        logger.error(f"{resp.status_code} {resp.text} Failed to send message '{message}' with {ses.headers['authorization']}")

def change_name(ses: r.Session, password, new_name):

    _data = {"password":password, "username":new_name}

    resp = ses.patch("https://discord.com/api/v9/users/@me", json=_data)

    if resp.status_code == 200:
        logger.success(f"Changed name of {ses.headers['authorization']} to {new_name}")
    elif resp.status_code == 429:
        sleep(int(resp.json()['retry_after']))
        change_name(ses, password, new_name)
    else:
        raise Exception(f"{resp.status_code} {resp.text}; Failed to change name of {ses.headers['authorization']} to {new_name}")

def performer(task_num, auth_tok, proxy, **transit_datas):
    ses = r.Session()
    ses.headers["authorization"] = auth_tok
    ses.headers["user-agent"] = u_a()

    resp = ses.get('https://discord.com/api/v9/users/@me?with_analytics_token=true')

    if resp.status_code == 200:
        pass
    elif resp.status_code == 429:
        sleep(int(resp.json()['retry_after']))
        performer(task_num, auth_tok, proxy, **transit_datas)
    else:
        raise Exception(f"{resp.status_code} {resp.text}; Failed to get acc data of {auth_tok}")

    if proxy is not None:
        ses.proxies = {
            proxy_type : proxy
        }

    if task_num == 1:
        add_reations(ses=ses, **transit_datas)
    elif task_num == 3:
        send_messages(ses=ses, **transit_datas)
    elif task_num == 4:
        change_name(ses=ses, **transit_datas)

def threader():
    while True:
        data = q.get()
        try:
            performer(**data)
        except Exception as e:
            logger.error(e)
        q.task_done()

if __name__ == "__main__":

    if not task in (2, 999999999999):
        for i in range(threads):
            Thread(target=threader, daemon=True).start()

    if task == 1:            #reactions
        c_id = input("Chat id --> ")

        answ = int(input("1 - file with msg ids \n2 - auto react to last 100 messages \n-->"))

        if answ == 1:
            message_ids_l = [a.replace("\n", "") for a in open(input("File with message ids --> "), "r").readlines()]
        else:
            ses_l = r.Session()
            ses_l.headers["authorization"] = tokens[0]

            msgs_resp = ses_l.get(f"https://discord.com/api/v9/channels/{c_id}/messages?limit=100")

            if msgs_resp.status_code == 200:
                message_ids_l = [a['id'] for a in msgs_resp.json()]
            else:
                raise Exception(f"Failed to get messages from {c_id}")

        reactions_l = [a.replace("\n", "") for a in open(input("File with reactions --> "), "r", encoding = "utf8").readlines()]

        task_data = {
            "chat_id":c_id,
            "message_ids":message_ids_l,
            "reactions":reactions_l,
        }

        for token in tokens:
            q.put({"task_num":task, "auth_tok":token, "proxy":proxies.pop(0), **task_data})

        q.join()

    elif task == 2:          #parse messages
        c_id = input("Chat id --> ")
        num = int(input("Number of messages --> "))

        ses_l = r.Session()
        ses_l.headers["authorization"] = tokens[0]

        print("Parsing")

        parse_last_msgs(ses_l, c_id, num)

    elif task == 3:          #send messages
        c_id = input("Chat id --> ")
        messages_to_send = [a.replace("\n", "") for a in open(input("File with messages to send --> "), "r", encoding="utf8").readlines()]
        send_type = input("1 - send messages once\n2 - send messages endlessly\n --> ")

        if send_type == 2:
            print("To stop the program close the window")

        temp_tokens = tokens.copy()
        temp_proxy = proxies.copy()

        while True:
            for message_to_send in messages_to_send:

                if len(temp_tokens) == 0 or len(temp_proxy) == 0:
                    temp_tokens = tokens.copy()
                    temp_proxy = proxies.copy()

                task_data = {
                    "chat_id":c_id,
                    "message":message_to_send
                }
                try:
                    q.put({"task_num": task, "auth_tok": temp_tokens.pop(0), "proxy": temp_proxy.pop(0), **task_data})
                except Exception as e:
                    print(temp_tokens, temp_proxy)
                    raise e

                q.join()
            if send_type==1:
                logger.info("-SENT FULL BATCH-")
                break

    elif task == 4:          #change names
        passwords = [a.replace("\n", "") for a in open(input("File with passwords --> "), "r", encoding="utf8").readlines()]

        answ = int(input("1 - names from a file\n2 - auto generated\n --> "))

        if answ == 1:
            names = [a.replace("\n", "") for a in open(input("File with names --> "), "r", encoding="utf8").readlines()]
        else:
            names = [f'{names.get_first_name()}{random.randint(10, 99)}' for _ in tokens]

        for token in tokens:
            task_data = {
                "password":passwords.pop(0),
                "new_name":names.pop(0)
            }
            q.put({"task_num": task, "auth_tok": token, "proxy": proxies.pop(0), **task_data})

        q.join()

    #elif task == 5:


    input("done")
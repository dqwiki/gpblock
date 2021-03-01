from http.cookiejar import MozillaCookieJar
from datetime import datetime, timezone, timedelta
import time
import sys, os, platform, requests
import json, re

import credentials as login
from mwclient import Site

cookies_file_en = '/data/project/deltaquad-bots/stewie-en.txt'
cookies_file_meta = '/data/project/deltaquad-bots/stewie-meta.txt'

#en login

cookie_jar_en = MozillaCookieJar(cookies_file_en)
if os.path.exists(cookies_file_en):
    # Load cookies from file, including session cookies (expirydate=0)
    cookie_jar_en.load(ignore_discard=True, ignore_expires=True)
print('We have %d cookies' % len(cookie_jar_en))

connection = requests.Session()
connection.cookies = cookie_jar_en  # Tell Requests session to use the cookiejar.

enwiki =  Site('en.wikipedia.org', pool=connection)
print("Login status: ")
print(enwiki.logged_in)
if not enwiki.logged_in:
	enwiki.login(login.username,login.password)

# Save cookies to file, including session cookies (expirydate=0)
print(connection.cookies)
cookie_jar_en.save(ignore_discard=True, ignore_expires=True)
###############

#meta login

cookie_jar_meta = MozillaCookieJar(cookies_file_meta)
if os.path.exists(cookies_file_meta):
    # Load cookies from file, including session cookies (expirydate=0)
    cookie_jar_meta.load(ignore_discard=True, ignore_expires=True)
print('We have %d cookies' % len(cookie_jar_meta))

connection = requests.Session()
connection.cookies = cookie_jar_meta  # Tell Requests session to use the cookiejar.

meta =  Site('meta.wikimedia.org', pool=connection)
print("Login status: ")
print(meta.logged_in)
if not meta.logged_in:
	meta.login(login.metauser,login.metapass)

# Save cookies to file, including session cookies (expirydate=0)
print(connection.cookies)
cookie_jar_meta.save(ignore_discard=True, ignore_expires=True)
###############

def callAPI(wiki,**params):
    if wiki=="enwiki":return enwiki.api(**params)
    if wiki=="meta":return meta.api(**params)
def getToken(wiki):
    params = {"action": "query",
        "format": "json",
        "meta": "tokens",
        "type": "csrf"
              }
    if wiki=="enwiki":return enwiki.api(**params)['query']['tokens']['csrftoken']
    if wiki=="meta":return meta.api(**params)['query']['tokens']['csrftoken']
def checkActive(oldtime):
    then = time.strptime(oldtime, "%Y-%m-%dT%H:%M:%SZ")
    now = time.gmtime()
    thenSeconds = time.mktime(then)
    nowSeconds = time.mktime(now)
    if thenSeconds > nowSeconds:return True
    else:return False
def checkExistGblock(ip):
    #https://meta.wikimedia.org/w/api.php?action=query&format=json&list=globalblocks&bgip=192.252.215.3
    params = {'action': 'query',
            'format': 'json',
            'list': 'globalblocks',
            'bgip': ip
            }
    raw = callAPI(wiki="enwiki",**params)['query']
    try:
        if len(raw['globalblocks'])>0:return True
        else:return False
    except:return False
def findblocks():
    numberblocked=0
    #https://en.wikipedia.org/w/api.php?action=query&format=json&list=logevents&leprop=ids%7Ctitle%7Ctype%7Ctimestamp%7Ccomment%7Cdetails%7Cparsedcomment&leaction=block%2Fblock&lestart=2021-02-14T22%3A24%3A31.000Z&leuser=ProcseeBot&lelimit=100
    params = {'action': 'query',
            'format': 'json',
            'list': 'logevents',
            'leprop': 'ids|title|type|timestamp|comment|details',
            'leaction': 'block/block',
            #'lestart': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'lestart': '2021-02-27T20:00:00', #TEMP TO RECOVER
            'leend': datetime.now() + timedelta(days=-60),
            'leuser': 'ST47ProxyBot',
            'lelimit': '5000'
            }
    raw = callAPI(wiki="enwiki",**params)['query']['logevents']
    for block in raw:
        ip=block['title'].split('User:')[1]#has to be user for IPv6 support
        expire=block['params']['expiry']
        comment=block['comment'].split("<!-- ")[1].split(" -->")[0]
        print('---New block---')
        print('IP: '+ip)
        params = {"action": "globalblock",
                    "format": "json",
                    "target": block['title'].split(':')[1],
                    "expiry": expire,
                    "reason": "[[m:NOP|No open proxies]]: <!-- " + comment + " -->",
                    "alsolocal": True,
                    "token": getToken(wiki="meta")
                  }
        if checkExistGblock(ip):
            print("Already blocked IP/range: "+ip)
            continue
        if checkActive(expire):
            print("Blocked: "+ip)
            numberblocked+=1
            raw = callAPI(wiki="meta",**params)
            continue
        else:
            print("Skipping expired block: "+ip)
            continue
    print(numberblocked)
findblocks()

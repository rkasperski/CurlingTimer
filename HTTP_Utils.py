from Logger import debug
import json
import asyncio
import aiohttp
import time
from Utils import myIPAddress

ip = myIPAddress()
port = 80
scheme = "http"
httpGetRequestTimeout = 2

HEADERS = {
    'user-agent': 'FakeRequestor/1.0',
}

CLOCK_HDR = "CC-Clock"


async def getUrlJSONResponse(who, url, headers=None, params=None, timeout=None, retries=1, stack_info=False):
    if not timeout:
        timeout = httpGetRequestTimeout

    hdrs = HEADERS.copy()
    if headers:
        hdrs.update(headers)

    for retry in range(retries):
        debug("getUrlJSON: %s %s start %s params=%s", who, url, timeout, params)
        
        startTime = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                startTime = time.time()
                async with session.get(url, headers=hdrs, params=params, timeout=timeout, ssl=False) as response:
                    text = await response.text()
                    data = json.loads(text) if text else {}

            elapsedTime = time.time() - startTime
        
            debug("getUrlJSON: %s %s %s complete retry: %s/%s", who, url, elapsedTime, retry + 1, retries)

            data["_elapsedTime"] = elapsedTime
            data["_startTime"] = startTime
            return data

        except json.JSONDecodeError as e:
            debug("getUrlJSON: %s %s %s Exception JSONDecodeError: bad data %s retry: %s/%s",
                  who, url, time.time() - startTime, e, retry + 1, retries, stack_info=stack_info)
        except asyncio.TimeoutError as e:
            debug("getUrlJSON: %s %s %s Exception ASycnIO: timeout %s retry: %s/%s",
                  who, url, time.time() - startTime, e, retry + 1, retries, stack_info=stack_info)
        except aiohttp.client_exceptions.ClientConnectionError as e:
            debug("getUrlJSON: %s %s %s Exception AIOHttp: ClientConnectionError %s retry: %s/%s",
                  who, url, time.time() - startTime, e, retry + 1, retries, stack_info=stack_info)
        except aiohttp.client_exceptions.ContentTypeError as e:
            debug("getUrlJSON: %s %s %s Exception AIOHttp: ContentTypeError %s retry: %s/%s",
                  who, url, time.time() - startTime, e, retry + 1, retries, stack_info=stack_info)
        except asyncio.CancelledError as e:
            debug("getUrlJSON: %s %s %s Exception ASycnIO: CancelledError %s retry: %s/%s",
                  who, url, time.time() - startTime, e, retry + 1, retries, stack_info=stack_info)
        except Exception as e:
            debug("getUrlJSON: %s %s %s Exception %s retry: %s/%s",
                  who, url, time.time() - startTime, e, retry + 1, retries, exc_info=True)

    return None


async def postUrlJSONResponse(who, url, headers=None, data=None, jsonData=None, timeout=1, retries=1, stack_info=False):
    if not timeout:
        timeout = httpGetRequestTimeout

    hdrs = HEADERS.copy()
    if headers:
        hdrs.update(headers)
    
    if jsonData is not None:
        data = json.dumps(jsonData).encode("utf-8")
        hdrs["content-type"] = "application/json"

    for retry in range(retries):
        debug("postUrlJSON: %s %s start %s retry: %s/%s data=%s headers=%s ", who, url, timeout, retry + 1, retries, data, hdrs)

        startTime = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, headers=hdrs, timeout=timeout, ssl=False) as response:
                    text = await response.text()
                    data = json.loads(text) if text else {}

            elapsedTime = time.time() - startTime
            debug("postUrlJSON: %s %s complete %s retry: %s/%s ", who, url, elapsedTime, retry + 1, retries)
            
            data["_elapsedTime"] = elapsedTime
            data["_startTime"] = startTime
            return data

        except json.JSONDecodeError as e:
            debug("postUrlJSON: %s %s %s Exception JSONDecodeError: bad data %s retry: %s/%s <<%s>>",
                  who, url, time.time() - startTime, e, retry + 1, retries, text, stack_info=stack_info)
        except asyncio.TimeoutError as e:
            debug("postUrlJSON: %s %s %s Exception ASycnIO: timeout %s retry: %s/%s ",
                  who, url, time.time() - startTime, e, retry + 1, retries, stack_info=stack_info)
        except aiohttp.client_exceptions.ClientConnectionError as e:
            debug("postUrlJSON: %s %s %s Exception AIOHttp: ClientConnectionErro  %s retry: %s/%s ",
                  who, url, time.time() - startTime, e, retry + 1, retries, stack_info=stack_info)
        except aiohttp.client_exceptions.ContentTypeError as e:
            debug("postUrlJSON: %s %s %s Exception  AIOHttp: ContentTypeError %s retry: %s/%s",
                  who, url, time.time() - startTime, e, retry + 1, retries, stack_info=stack_info)
        except asyncio.CancelledError as e:
            debug("postUrlJSON: %s %s %s Exception ASycnIO: CancelledError %s retry: %s/%s ",
                  who, url, time.time() - startTime, e, retry + 1, retries, stack_info=stack_info)
        except Exception as e:
            debug("postUrlJSON: %s %s %s Exception %s retry: %s/%s ",
                  who, url, time.time() - startTime, e, retry + 1, retries, exc_info=True)

    return None

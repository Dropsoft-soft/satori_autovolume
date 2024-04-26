from random import uniform

import aiohttp
from loguru import logger
import time
import json

TIMEOUT = [5, 10]
MAX_RETRY = 4

ERROR_CODE_EXCEPTION = -1
ERROR_CODE_FAILED_REQUEST = -2


async def global_request(wallet, method="post", request_retry=0, proxy: str = None, need_sleep= False, **kwargs):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        if proxy is not None:
            session.proxies.update(
                {
                    "http": f"{proxy}",
                    "https": f"{proxy}"
                }
            )

        if request_retry > MAX_RETRY:
            return
        retry = 0

        while True:
            try:
                if method == "post":
                    response = await session.post(**kwargs)
                elif method == "get":
                    response = await session.get(**kwargs)
                elif method == "put":
                    response = await session.put(**kwargs)
                elif method == "options":
                    response = await session.options(**kwargs)

                status_code = response.status

                if status_code == 201 or status_code == 200:

                    timing = uniform(TIMEOUT[0], TIMEOUT[1])
                    # logger.info(f'{wallet} response: {status_code}. sleep {timing}')
                    if need_sleep:
                        time.sleep(timing)
                    try:
                        return status_code, await response.json()
                    except json.decoder.JSONDecodeError:
                        logger.info('The request success but not contain a JSON')
                        break
                else:
                    if status_code == 400:
                        logger.warning(f'[{wallet} - {kwargs["url"]}] info: {await response.json()}')
                    elif status_code == 401:
                        message = f'[{wallet} - {kwargs["url"]}] Not authorised: {status_code}'
                        logger.warning(message)
                        return 401, message
                    else:
                        logger.error(f'[{wallet} - {kwargs["url"]}] Bad status code: {status_code} {await response.json()}')
                        if need_sleep:
                            time.sleep(30)

                    retry += 1
                    if retry > 4:
                        message = f'[{wallet} - {kwargs["url"]}] request attempts reached max retries count'
                        logger.error(message)
                        return ERROR_CODE_FAILED_REQUEST, message

            except ConnectionError as error:
                logger.error(f'{wallet} - HTTPSConnectionPool - {kwargs["url"]} failed to make request | {error}')
                if need_sleep:
                    time.sleep(25)
                await global_request(method=method, request_retry=request_retry + 1, proxy=proxy, need_sleep=True, **kwargs)
                break

            except Exception as error:
                logger.error(f'{wallet} - {kwargs["url"]} failed to make request | {error}')
                if need_sleep:
                    time.sleep(10)
                return ERROR_CODE_EXCEPTION, error

from random import uniform

import requests
from loguru import logger
import time
import json

TIMEOUT = [5, 10]
MAX_RETRY = 4

ERROR_CODE_EXCEPTION = -1
ERROR_CODE_FAILED_REQUEST = -2


def global_request(wallet, method="post", request_retry=0, proxy: str = None, need_sleep=True, **kwargs):
    session = requests.Session()
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
                response = session.post(**kwargs, verify=False)
            elif method == "get":
                response = session.get(**kwargs, verify=False)
            elif method == "put":
                response = session.put(**kwargs, verify=False)
            elif method == "options":
                response = session.options(**kwargs, verify=False)

            status_code = response.status_code

            if status_code == 201 or status_code == 200:

                timing = uniform(TIMEOUT[0], TIMEOUT[1])
                logger.info(f'{wallet} response: {status_code}. sleep {timing}')
                if need_sleep:
                    time.sleep(timing)
                try:
                    return status_code, response.json()
                except json.decoder.JSONDecodeError:
                    logger.info('The request success but not contain a JSON')
                    break
            else:
                if status_code == 400:
                    logger.warning(f'[{wallet} - {kwargs["url"]}] info: {response.json()}')
                elif status_code == 401:
                    message = f'[{wallet} - {kwargs["url"]}] Not authorised: {status_code}'
                    logger.warning(message)
                    return 401, message
                else:
                    logger.error(f'[{wallet} - {kwargs["url"]}] Bad status code: {status_code} {response.json()}')
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
            global_request(method=method, request_retry=request_retry + 1, proxy=proxy, need_sleep=True, **kwargs)
            break

        except Exception as error:
            logger.error(f'{wallet} - {kwargs["url"]} failed to make request | {error}')
            if need_sleep:
                time.sleep(10)
            return ERROR_CODE_EXCEPTION, error

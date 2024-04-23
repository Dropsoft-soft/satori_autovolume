import asyncio
import math
import random
from .client import WebClient
from loguru import logger
from .request import global_request

pairs = [
    "ETH-USD",
    # "BTC-USD"
]


class Satori(WebClient):
    def __init__(self, _id: int, private_key: str, chain: str) -> None:
        super().__init__(id=_id, key=private_key, chain=chain)
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US',
            'authorization': '',
            'brand-exchange': 'zksync',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://zksync.satori.finance',
            'pragma': 'no-cache',
            'referer': 'https://zksync.satori.finance/portfolio/account',
            'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        }
        logger.info(f'account id: {self.id} address: {self.address}')

    async def start_trading(self):
        nonce = await self.get_nonce()
        if nonce is None:
            logger.info(f'can\'t get nonce for account id: {self.id}')
            return
        signed_nonce = await self.sign_message(nonce)

        token = await self.get_token(signed_nonce)

        self.headers['authorization'] = token

        if token is None:
            logger.info(f'can\'t get token for account id: {self.id}')
            return

        trade_pairs_response = await self.get_trade_pairs()

        while True:

            trade_pairs = [(item['symbol'], item['id']) for item in trade_pairs_response]
            pair_id, pair_name = self.get_random_pair(trade_pairs)
            # logger.info(f'random pair {pair_id} > {pair_name}')

            amount = await self.get_satori_balance(4)
            # await self.get_all_balance(trade_pairs_response)

            order_opened = await self.open_position(pair_id, amount)

            if order_opened is not None:
                sleep_time = round(random.uniform(20, 40), 0)
                logger.info(f'Sleep for {sleep_time}')
                await asyncio.sleep(sleep_time)
                order_info = await self.get_opened_order_ids()
                if order_info:
                    logger.info(f"Size of the order_info: {len(order_info)}")

                for record_id, contract_pair_id in order_info:
                    await self.position_entrust(record_id)

                long_order_info = await self.get_long_order_ids()
                # if long_order_info:
                    # logger.info(f"Size of the long_order_info: {len(long_order_info)}")

                for record_id, contract_pair_id, quantity in long_order_info:
                    await self.close_position(record_id, contract_pair_id, quantity)
            else:
                logger.info("Can't open Order")

            sleep_time = round(random.uniform(5, 10), 0)
            logger.info(f'Sleep for {sleep_time}')
            await asyncio.sleep(sleep_time)

    async def get_nonce(self):
        response_code, response = await global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/auth/auth/generateNonce',
            json={"address": f"{self.address}"},
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            return response['data']['nonce']
        else:
            return None

    async def get_token(self, signed_nonce):
        response_code, response = await global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/auth/auth/token',
            json={"address": f"{self.address}",
                  "signature": f"{signed_nonce}"},
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            return response['data']
        else:
            return None

    async def get_user(self):
        response_code, response = await global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/contract-provider/contract/getUser',
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            return response['msg']
        else:
            return None

    async def portfolio_account(self, coin_id):
        response_code, response = await global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/contract-provider/contract/portfolioAccount',
            json={"coinId": f'{coin_id}', "timeType": 1},
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            return response['data']['profitList']
        else:
            return None

    async def get_trade_pairs(self):
        response_code, response = await global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/contract-provider/contract/contractPairList',
            json={
                "coinId": 4,
                "coinSymbol": "USD",
                "settleDecimal": 6,
                "isDelivery": False
            },
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            data = response['data']

            return data
        else:
            return None

    async def open_position(self, contract_pair_id, amount):
        amount = math.floor(amount * 100) / 100
        price = 4000 #ETH
        quantity = round(amount / price, 3)

        expire_time = await self.get_time()
        expire_time = expire_time + 60244

        message = self.get_message(quantity, self.address, expire_time, contract_pair_id, False, amount)
        message = str(message).replace("'", '"')  # Convert single quotes to double quotes
        message_hash = await self.sign_message(message)
        # client_order_id = '7tD0_yhku_62Py33ySe2F'

        response_code, response = await global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/contract-provider/contract/order/openPosition',
            json={
                "contractPairId": contract_pair_id,
                "contractPositionId": 0,
                "isLong": True,
                "isMarket": False,
                "quantity": quantity,
                "signHash": message_hash,
                "originMsg": message,
                "lever": 1,
                "amount": amount,
                "price": price,
                "positionType": 3,
                "matchType": 1,
                # "clientOrderId": client_order_id
            },
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            logger.info(f"Position Opened for {amount}")
            return True
        else:
            logger.info(f"OPEN FAILED {response}")
            return False

    async def get_time(self):
        response_code, response = await global_request(
            wallet=self.address,
            method="get",
            url=f'https://zksync.satori.finance/api/third/info/time',
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            data = response['data']
            return data
        else:
            return None

    def get_message(self, quantity, address, expire_time, contract_pair_id, is_close, amount):
        json_data = {
            "quantity": quantity,
            "address": address,
            "expireTime": expire_time,
            "contractPairId": contract_pair_id,
            "isClose": is_close,
            "amount": amount
        }
        return json_data

    def get_random_pair(self, trade_pairs):
        pair_exist = False
        for pair in pairs:
            for pair_name, pair_id in trade_pairs:
                if pair == pair_name:
                    pair_exist = True
                    break
            if pair_exist:
                break

        if not pair_exist:
            return None

        while True:
            random_pair = random.choice(pairs)

            # Try to find the corresponding ID in the dictionary
            for pair_name, pair_id in trade_pairs:
                if pair_name == random_pair:
                    return pair_id, pair_name

            logger.info(f"No matching pair ID found for {random_pair}. Trying another pair...")

    async def close_position(self, order_id, contract_pair_id, quantity):
        amount = 100
        expire_time = await self.get_time()
        expire_time = expire_time + 60244

        message = self.get_message(quantity, self.address, expire_time, contract_pair_id, True, amount)
        message = str(message).replace("'", '"')  # Convert single quotes to double quotes
        message_hash = await self.sign_message(message)
        # client_order_id = '7tD0_yhku_62Py33ySe2F'

        response_code, response = await global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/contract-provider/contract/order/closePosition',
            json={
                "contractPairId": contract_pair_id,
                "contractPositionId": order_id,
                "isMarket": True,
                "signHash": message_hash,
                "originMsg": message,
                # "clientOrderId": client_order_id,
                "quantity": quantity,
                "isLong": True,
                "amount": amount,
                "price": None
            },
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            logger.info(f'Position Closed')
            return True
        else:
            return False

    async def get_satori_balance(self, coin_id):
        response_code, response = await global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/contract-provider/contract-account/account/{coin_id}',
            json={},
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            amount = response['data']['availableAmount']
            try:
                return float(amount)
            except (ValueError, TypeError):
                return 0.0
        else:
            return None

    async def get_all_balance(self, trade_pairs_response):
        coins_and_ids = {}
        for item in trade_pairs_response:
            coin_id = item['settleCoin']['id']
            coin_name = item['settleCoin']['name']
            coins_and_ids[coin_name] = coin_id

        for coin_name, coin_id in coins_and_ids.items():
            amount = await self.get_satori_balance(coin_id)
            logger.info(f"Coin Name: {coin_name}, Coin ID: {coin_id} > {amount}")

    async def get_opened_order_ids(self):
        response_code, response = await global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/contract-provider/contract-current-entrust/selectContractCurrentEntrustList',
            json={
                'pageNo': 1,
                'pageSize': 100
            },
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            return [(record['id'], record['contractPairId']) for record in response['data']['records']]
        else:
            return None

    async def position_entrust(self, record_id):
        response_code, response = await global_request(
            wallet=self.address,
            method="get",
            url=f'https://zksync.satori.finance/api/contract-provider/contract/cancelEntrust?id={record_id}',
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            logger.info(f'Order Closed')
            return response
        else:
            logger.info(f"CLOSE FAILED {response}")
            return None

    async def get_long_order_ids(self):
        #
        response_code, response = await global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/contract-provider/contract/selectContractPositionList',
            json={
                'pageNo': 1,
                'pageSize': 100
            },
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            return [(record['id'], record['contractPairId'], record['quantity']) for record in response['data']['records']]
        else:
            return None

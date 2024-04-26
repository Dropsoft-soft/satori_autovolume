import asyncio
import math
import random
import time
from core.data import SATORI_CONTRACT, USDC_CONTRACT
from core.utils import intToDecimal
from user_data.config import AMOUNT, CHAIN
from .client import WebClient
from loguru import logger
from .request import global_request

class Satori(WebClient):
    def __init__(self, _id: int, private_key: str, chain: str) -> None:
        super().__init__(id=_id, key=private_key, chain=chain)
        self.base_url = f'https://{chain}.satori.finance/'
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US',
            'authorization': '',
            'brand-exchange': f'{chain}',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': f'https://{chain}.satori.finance',
            'pragma': 'no-cache',
            'referer': f'{self.base_url}portfolio/account',
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
        portfolio_account = await self.portfolio_account(4)
        assets = float(portfolio_account['totalAssets'])
        
        if assets == 0:
            logger.info(f'Process deposit')
            status, tx_link = await self.deposit_money()
            if status == 1:
                logger.success(f'Deposit success | {tx_link} \n Sleep 120 sec.')
                await asyncio.sleep(120)
            else:
                logger.error('Deposit not success')
                return
       
        if token is None:
            logger.info(f'can\'t get token for account id: {self.id}')
            return

        trade_pairs_response = await self.get_trade_pairs()

        while True:

            trade_pairs = [(item['symbol'], item['id']) for item in trade_pairs_response]
            pair_id, pair_name = self.get_random_pair(trade_pairs)
            logger.info(f'random pair {pair_id} > {pair_name}')

            amount = await self.get_satori_balance(4)
            # await self.get_all_balance(trade_pairs_response)
            order_opened = await self.open_position(pair_id, amount, pair_name[:3])

            if order_opened is not None:
                sleep_time = round(random.uniform(20, 60), 0)
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

            sleep_time = round(random.uniform(10, 30), 0)
            logger.info(f'Sleep for {sleep_time}')
            await asyncio.sleep(sleep_time)

    async def get_nonce(self):
        response_code, response = await global_request(
            wallet=self.address,
            url=f'{self.base_url}api/auth/auth/generateNonce',
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
            url=f'{self.base_url}api/auth/auth/token',
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
            url=f'{self.base_url}api/contract-provider/contract/getUser',
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            return response['msg']
        else:
            return None

    async def portfolio_account(self, coin_id):
        response_code, response = await global_request(
            wallet=self.address,
            url=f'{self.base_url}api/contract-provider/contract/portfolioAccount',
            json={"coinId": f'{coin_id}', "timeType": 1},
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            return response['data']
        else:
            return None

    async def get_trade_pairs(self):
        response_code, response = await global_request(
            wallet=self.address,
            url=f'{self.base_url}api/contract-provider/contract/contractPairList',
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

    async def get_prise(self, symbol):
        response_code, response = await global_request(
            wallet=self.address,
            url=f'https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USDT',
            proxy=self.proxy,
            headers=self.headers
        )
        return float(response['USDT'])

    async def open_position(self, contract_pair_id, amount, symbol):
        amount = math.floor(amount * 100) / 100
        price = await self.get_prise(symbol)
        quantity = round(amount / price, 2)
        expire_time = await self.get_time()
        expire_time = expire_time + 60244

        message = self.get_message(quantity, self.address, expire_time, contract_pair_id, False, amount)
        message = str(message).replace("'", '"')  # Convert single quotes to double quotes
        message_hash = await self.sign_message(message)
        # client_order_id = '7tD0_yhku_62Py33ySe2F'

        response_code, response = await global_request(
            wallet=self.address,
            url=f'{self.base_url}api/contract-provider/contract/order/openPosition',
            json={
                "contractPairId": contract_pair_id,
                "contractPositionId": 0,
                "isLong": True,
                "isMarket": False,
                "quantity": quantity,
                "signHash": message_hash,
                "originMsg": message,
                "lever": 10,
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
            url=f'{self.base_url}api/third/info/time',
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
            url=f'{self.base_url}api/contract-provider/contract/order/closePosition',
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
            url=f'{self.base_url}api/contract-provider/contract-account/account/{coin_id}',
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
            url=f'{self.base_url}api/contract-provider/contract-current-entrust/selectContractCurrentEntrustList',
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
            url=f'{self.base_url}api/contract-provider/contract/cancelEntrust?id={record_id}',
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
            url=f'{self.base_url}api/contract-provider/contract/selectContractPositionList',
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
        
    async def deposit_money(self):
        amount = intToDecimal(AMOUNT, 6)
        encoded_with_zero = hex(amount)[2:].rjust(64, '0')
        await self.approve(amount, USDC_CONTRACT[CHAIN], SATORI_CONTRACT[CHAIN])
        if CHAIN == 'zksync':
            tx_data = '0x72f66b670000000000000000000000000000000000000000000000000001f929487740450000000000000000000000000000000000000000000000000000018ef0fc5a820000000000000000000000003355df6d4c9c3035724fd0e3914de96a5a83aaf4'+encoded_with_zero
        elif CHAIN == 'linea' or CHAIN == 'scroll':
            tx_data = '0x72f66b670000000000000000000000000000000000000000000000000001d009a603b0450000000000000000000000000000000000000000000000000000018c5f01bfdd000000000000000000000000176211869ca2b568f2a7d4ee941e073a821ee1ff'+encoded_with_zero
        elif CHAIN == 'base':
            tx_data = '0x72f66b670000000000000000000000000000000000000000000000000001fb28fc3180450000000000000000000000000000000000000000000000000000018f10f7963b000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54bda02913'+encoded_with_zero
        else:
            tx_data = ''
        tx = {
            'from': self.address,
            'to': SATORI_CONTRACT[CHAIN],
            'gas': 0,
            'gasPrice': await self.web3.eth.gas_price,
            'nonce': await self.web3.eth.get_transaction_count(self.address),
            'value': 0,
            'data': tx_data,
            'chainId': self.chain_id
        }
        return await self.send_tx(tx)
    #not working
    async def withdraw_money(self, amount):
        timeResponse = int(time.time() * 1000)
        logger.info(f'timerespoinse {timeResponse}')
        sign = '{\"amount\":\"1\",\"address\":\"0x2EDEc0Da3385611C59235fc711faFac5298Cc0CA\",\"assetAddr\":\"0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4\",\"expireTime\":\"1713446800352\"}'
        signed = await self.sign_message(sign)
        payload = {
            "amount":amount,
            "originMsg": sign,
            "signHash": signed,
            "chainId": self.chain_id
        }
        #1713446347112
        #1713446454174000000
        response_code, response = await global_request(
            wallet=self.address,
            url=f'{self.base_url}api/contract-provider/withdraw/ask',
            json=payload,
            proxy=self.proxy,
            headers=self.headers)

        amount = intToDecimal(amount, 6)
        encoded_with_zero = hex(amount)[2:].rjust(64, '0')
        if CHAIN == 'zksync':
            tx_data = '0x83a7abd800000000000000000000000000000000000000000000000018ef14767d38000100000000000000000000000000000000000000000000000000000000662119980000000000000000000000003355df6d4c9c3035724fd0e3914de96a5a83aaf4000000000000000000000000' + self.address[2:] + encoded_with_zero + '0000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000016000000000000000000000000000000000000000000000000000000000000001c00000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000001b000000000000000000000000000000000000000000000000000000000000001c00000000000000000000000000000000000000000000000000000000000000027ee7bb17f703bae0e1ece73319c20bce6e3f2dc331f14bc7e3d6ea14651ae672afaa86f2954db51491270de94119caa1bf8a7b2f37f69dccfe1db8bc7c682c5600000000000000000000000000000000000000000000000000000000000000022c80f3ac5a20c7ee4ba56a82679ae7bc5857092c17ba1c2fdbcf9a2ab648397a24ca8355e97f0c37106afeca7d91a4e7dbb348489400419ef9e6009ac9d4e1f0'
        else:
            tx_data = ''
        tx = {
            'from': self.address,
            'to': SATORI_CONTRACT[CHAIN],
            'gas': 0,
            'gasPrice': await self.web3.eth.gas_price,
            'nonce': await self.web3.eth.get_transaction_count(self.address),
            'value': 0,
            'data': tx_data,
            'chainId': self.chain_id
        }
        return await self.send_tx(tx)

from .client import WebClient
from loguru import logger
from .request import global_request


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
        logger.info(f'start trading for account id: {self.id}')
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

        get_user = await self.get_user()

        portfolio_account = await self.portfolio_account(4)

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

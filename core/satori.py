from .client import WebClient
from loguru import logger

from .helpers import dev_logs
from .request import global_request


# ``` examplt asyncio
# async def get_quotes(from_token: int, to_token: int, amount: int):
#     async with aiohttp.ClientSession() as session:
#         url = "https://starknet.api.avnu.fi/swap/v1/quotes"

#         params = {
#             "sellTokenAddress": hex(from_token),
#             "buyTokenAddress": hex(to_token),
#             "sellAmount": hex(amount),
#             "excludeSources": "Ekubo"
#         }
#         response = await session.get(url=url, params=params)
#         response_data = await response.json()

#         quote_id = response_data[0]["quoteId"]

#         return quote_id
# ```

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
        nonce = self.get_nonce()
        dev_logs(f"nonce result: {nonce}")
        if nonce is None:
            logger.info(f'can\'t get nonce for account id: {self.id}')
            return
        signed_nonce = await self.sign_message(nonce)
        dev_logs(f"sign nonce result: {signed_nonce}")

        token = self.get_token(signed_nonce)

        self.headers['authorization'] = token

        dev_logs(f"authorization: {self.headers['authorization']}")
        if token is None:
            logger.info(f'can\'t get token for account id: {self.id}')
            return

        get_user = self.get_user()
        dev_logs(f"get user: {get_user}")

        portfolio_account = self.portfolio_account(4)
        dev_logs(f"get portfolio_account: {portfolio_account}")

    def get_nonce(self):
        response_code, response = global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/auth/auth/generateNonce',
            json={"address": f"{self.address}"},
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            return response['data']['nonce']
        else:
            return None

    def get_token(self, signed_nonce):
        response_code, response = global_request(
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

    def get_user(self):
        response_code, response = global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/contract-provider/contract/getUser',
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            return response['msg']
        else:
            return None

    def portfolio_account(self, coin_id):
        response_code, response = global_request(
            wallet=self.address,
            url=f'https://zksync.satori.finance/api/contract-provider/contract/portfolioAccount',
            json={"coinId": f'{coin_id}', "timeType": 1},
            proxy=self.proxy,
            headers=self.headers)

        if response_code == 200 and response['error'] is False:
            return response['data']['profitList']
        else:
            return None

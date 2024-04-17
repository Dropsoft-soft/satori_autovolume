from .client import WebClient
from loguru import logger
import aiohttp

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
        logger.info(f'account id: {self.id} address: {self.address}')
    
    async def start_traiding(self):
        logger.info(f'start trading for account id: {self.id}')
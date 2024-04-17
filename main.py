import asyncio
import platform
import sys
from core.utils import WALLETS
from core.__init__ import *
from user_data.config import CHAIN

def get_wallets():
    wallets = [
        {
            "id": _id,
            "key": key,
        } for _id, key in enumerate(WALLETS, start=1)
    ]
    return wallets


if __name__ == "__main__":
    if platform.system() == "Windows" and sys.version_info >= (3, 8, 0):
      asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    wallets = get_wallets()
    
    for wallet in wallets:
        satori = Satori(wallet.get('id'), wallet.get('key'), CHAIN)
        asyncio.run(satori.start_traiding())

import asyncio
import sys
from core.utils import WALLETS, show_dev_info
from core.__init__ import *
from user_data.config import CHAIN
from concurrent.futures import ThreadPoolExecutor

def get_wallets():
    wallets = [
        {
            "id": _id,
            "key": key,
        } for _id, key in enumerate(WALLETS, start=1)
    ]
    return wallets

async def run_module(account_id, key):
    try:
        satori = Satori(account_id, key, CHAIN)
        await satori.start_trading()
    except Exception as e:
        logger.error(e)

def _async_run_module(module, account_id, key):
    asyncio.run(run_module(account_id, key))

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    show_dev_info()
    wallets = get_wallets()

    with ThreadPoolExecutor(max_workers=len(wallets)) as executor:
        for _, account in enumerate(wallets, start=1):
            executor.submit(
                _async_run_module,
                Satori,
                account.get("id"),
                account.get("key")
            )
            time.sleep(random.randint(10, 20))
    
    # for wallet in wallets:
    #     satori = Satori(wallet.get('id'), wallet.get('key'), CHAIN)
    #     asyncio.run(satori.start_trading())

import asyncio
import logging
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.core import repository
from poptimizer.data.adapter import MarketData
from poptimizer.dl import datasets, trainer
from poptimizer.portfolio.adapter import PortfolioData


async def main():
    logging.basicConfig(level=logging.INFO)
    mongo_client = AsyncIOMotorClient("mongodb://localhost:27017", tz_aware=False)

    repo = repository.Repo(client=mongo_client)
    PortfolioData(repo)

    tr = trainer.Trainer(datasets.Builder(MarketData(repo)))

    desc = {
        "batch": {
            "size": 256,
            "feats": {
                "tickers": await PortfolioData(repo).tickers(),
                "last_date": datetime(2022, 12, 2),
                "close": True,
                "div": True,
                "ret": True,
            },
            "days": {
                "history": 160,
                "forecast": 21,
                "test": 250,
            },
        },
        "net": {
            "input": {
                "use_bn": True,
                "out_channels": 8,
            },
            "backbone": {
                "blocks": 1,
                "kernels": 2,
                "channels": 8,
                "out_channels": 8,
            },
            "head": {
                "channels": 8,
                "mixture_size": 3,
            },
        },
        "optimizer": {},
        "scheduler": {"epochs": 2.5},
        "utility": {"risk_tolerance": 0.5},
    }

    await tr.test_model(None, trainer.DLModel.parse_obj(desc))


if __name__ == "__main__":
    asyncio.run(main())

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from currencies.models import CurrencyORM
from database import get_async_session

from .models import ExchangeRateORM
from .schemas import ExchangeRateResponse

router = APIRouter(
    prefix="/exchangeRates",
    tags=["Exchange Rates"]
)


@router.get("", response_model=list[ExchangeRateResponse])
async def get_exchange_rates(session: AsyncSession = Depends(get_async_session)):
    query = select(ExchangeRateORM)
    result = await session.execute(query)
    exchange_rates = result.scalars()
    exchange_rates_dict = [exchange_rate.__dict__.copy() for exchange_rate in exchange_rates]

    for exchange_rate in exchange_rates_dict:
        query = select(CurrencyORM).filter(
            CurrencyORM.id == int(exchange_rate["base_currency_id"]))
        result = await session.execute(query)
        base_currency = result.scalar_one_or_none()

        query = select(CurrencyORM).filter(
            CurrencyORM.id == int(exchange_rate["target_currency_id"]))
        result = await session.execute(query)
        target_currency = result.scalar_one_or_none()

        exchange_rate["base_currency"] = base_currency.__dict__.copy()
        exchange_rate["target_currency"] = target_currency.__dict__.copy()
        exchange_rate["rate"] = round(float(exchange_rate["rate"]), 2)

        del exchange_rate["base_currency_id"]
        del exchange_rate["target_currency_id"]
        del exchange_rate["_sa_instance_state"]
        del exchange_rate["base_currency"]["_sa_instance_state"]
        del exchange_rate["target_currency"]["_sa_instance_state"]

    return exchange_rates_dict


@router.post("", response_model=ExchangeRateResponse)
async def post_exchange_rate(baseCurrencyCode: Annotated[str, Body()],
                             targetCurrencyCode: Annotated[str, Body()],
                             rate: Annotated[float, Body()],
                             session: AsyncSession = Depends(get_async_session)):

    query = select(CurrencyORM).filter(CurrencyORM.code == baseCurrencyCode)
    result = await session.execute(query)
    base_currency = result.scalar_one_or_none()

    query = select(CurrencyORM).filter(CurrencyORM.code == targetCurrencyCode)
    result = await session.execute(query)
    target_currency = result.scalar_one_or_none()

    if base_currency is None or target_currency is None:
        return JSONResponse(
            status_code=404,
            content={"message": "Одна (или обе) валюта из валютной пары не существует в БД"}
        )

    query = select(ExchangeRateORM).filter(ExchangeRateORM.base_currency_id == base_currency.id,
                                           ExchangeRateORM.target_currency_id == target_currency.id)
    result = await session.execute(query)

    if result.scalar_one_or_none() is not None:
        return JSONResponse(status_code=409,
                            content={"message": "Валютная пара с таким кодом уже существует"})

    base_currency_dict = base_currency.__dict__.copy()
    target_currency_dict = target_currency.__dict__.copy()

    exchange_rate_model = ExchangeRateORM(base_currency_id=base_currency.id,
                                          target_currency_id=target_currency.id,
                                          rate=rate)
    session.add(exchange_rate_model)
    await session.flush()
    await session.commit()

    exchange_rate_model_dict = exchange_rate_model.__dict__.copy()

    exchange_rate_model_dict["rate"] = round(float(exchange_rate_model_dict["rate"]), 2)

    del exchange_rate_model_dict["_sa_instance_state"]
    del base_currency_dict["_sa_instance_state"]
    del target_currency_dict["_sa_instance_state"]

    exchange_rate_model_dict.pop("base_currency_id")
    exchange_rate_model_dict.pop("target_currency_id")

    exchange_rate_model_dict["base_currency"] = base_currency_dict
    exchange_rate_model_dict["target_currency"] = target_currency_dict

    return exchange_rate_model_dict


@router.get("/{exchange_pair}", response_model=ExchangeRateResponse)
async def get_exchange_rate(exchange_pair: Annotated[str, Path()],
                            session: AsyncSession = Depends(get_async_session)):
    base_currency_code = exchange_pair[:3]
    target_currency_code = exchange_pair[3:]

    c1 = aliased(CurrencyORM)
    c2 = aliased(CurrencyORM)

    query = select(ExchangeRateORM) \
        .join(c1, ExchangeRateORM.base_currency_id == c1.id) \
        .join(c2, ExchangeRateORM.target_currency_id == c2.id) \
        .filter(c1.code == base_currency_code, c2.code == target_currency_code)

    result = await session.execute(query)

    exchange_rate = result.scalar_one_or_none()

    if exchange_rate is None:
        return JSONResponse(status_code=404,
                            content={"message": "Обменный курс для пары не найден"})

    exchange_rate_dict = exchange_rate.__dict__.copy()
    del exchange_rate_dict["_sa_instance_state"]

    query = select(CurrencyORM).filter(
        CurrencyORM.id == int(exchange_rate_dict["base_currency_id"]))
    result = await session.execute(query)
    base_currency = result.scalar_one_or_none()

    query = select(CurrencyORM).filter(
        CurrencyORM.id == int(exchange_rate_dict["target_currency_id"]))
    result = await session.execute(query)
    target_currency = result.scalar_one_or_none()

    exchange_rate_dict["base_currency"] = base_currency.__dict__.copy()
    del exchange_rate_dict["base_currency"]["_sa_instance_state"]
    del exchange_rate_dict["base_currency_id"]

    exchange_rate_dict["target_currency"] = target_currency.__dict__.copy()
    del exchange_rate_dict["target_currency"]["_sa_instance_state"]
    del exchange_rate_dict["target_currency_id"]

    exchange_rate_dict["rate"] = round(float(exchange_rate_dict["rate"]), 2)

    return exchange_rate_dict


@router.patch("/{exchange_pair}", response_model=ExchangeRateResponse)
async def patch_exchange_rate(exchange_pair: Annotated[str, Path()],
                              rate: Annotated[float, Body()],
                              session: AsyncSession = Depends(get_async_session)):
    base_currency_code = exchange_pair[:3]
    target_currency_code = exchange_pair[3:]

    query = select(CurrencyORM).filter(CurrencyORM.code == base_currency_code)
    result = await session.execute(query)
    base_currency = result.scalar_one_or_none()

    query = select(CurrencyORM).filter(CurrencyORM.code == target_currency_code)
    result = await session.execute(query)
    target_currency = result.scalar_one_or_none()

    if base_currency is None or target_currency is None:
        return JSONResponse(
            status_code=404,
            content={"message": "Валютная пара отсутствует в базе данных"}
        )

    c1 = aliased(CurrencyORM)
    c2 = aliased(CurrencyORM)

    base_currency_dict = base_currency.__dict__.copy()
    target_currency_dict = target_currency.__dict__.copy()

    query = select(ExchangeRateORM) \
        .join(c1, ExchangeRateORM.base_currency_id == c1.id) \
        .join(c2, ExchangeRateORM.target_currency_id == c2.id) \
        .filter(c1.code == base_currency_code, c2.code == target_currency_code)

    result = await session.execute(query)

    exchange_rate = result.scalar_one_or_none()

    if exchange_rate is None:
        return JSONResponse(
            status_code=404,
            content={"message": "Обменный курс для пары не найден"}
        )

    exchange_rate.rate = rate
    await session.flush()
    await session.commit()

    exchange_rate_dict = exchange_rate.__dict__.copy()

    exchange_rate_dict["rate"] = round(float(exchange_rate_dict["rate"]), 2)

    del exchange_rate_dict["_sa_instance_state"]
    del base_currency_dict["_sa_instance_state"]
    del target_currency_dict["_sa_instance_state"]

    exchange_rate_dict.pop("base_currency_id")
    exchange_rate_dict.pop("target_currency_id")

    exchange_rate_dict["base_currency"] = base_currency_dict
    exchange_rate_dict["target_currency"] = target_currency_dict

    return exchange_rate_dict


@router.delete("/{exchange_pair}", response_model=ExchangeRateResponse)
async def delete_currency(exchange_pair: Annotated[str, Path()],
                          session: AsyncSession = Depends(get_async_session)):
    base_currency_code = exchange_pair[:3]
    target_currency_code = exchange_pair[3:]

    c1 = aliased(CurrencyORM)
    c2 = aliased(CurrencyORM)

    query = select(ExchangeRateORM) \
        .join(c1, ExchangeRateORM.base_currency_id == c1.id) \
        .join(c2, ExchangeRateORM.target_currency_id == c2.id) \
        .filter(c1.code == base_currency_code, c2.code == target_currency_code)

    result = await session.execute(query)

    exchange_rate = result.scalar_one_or_none()

    if exchange_rate is None:
        return JSONResponse(status_code=404,
                            content={"message": "Обменный курс для пары не найден"})

    await session.delete(exchange_rate)  # correct deletion?
    await session.commit()

    exchange_rate_dict = exchange_rate.__dict__.copy()
    del exchange_rate_dict["_sa_instance_state"]

    query = select(CurrencyORM).filter(
        CurrencyORM.id == int(exchange_rate_dict["base_currency_id"]))
    result = await session.execute(query)
    base_currency = result.scalar_one_or_none()

    query = select(CurrencyORM).filter(
        CurrencyORM.id == int(exchange_rate_dict["target_currency_id"]))
    result = await session.execute(query)
    target_currency = result.scalar_one_or_none()

    exchange_rate_dict["base_currency"] = base_currency.__dict__.copy()
    del exchange_rate_dict["base_currency"]["_sa_instance_state"]
    del exchange_rate_dict["base_currency_id"]

    exchange_rate_dict["target_currency"] = target_currency.__dict__.copy()
    del exchange_rate_dict["target_currency"]["_sa_instance_state"]
    del exchange_rate_dict["target_currency_id"]

    exchange_rate_dict["rate"] = round(float(exchange_rate_dict["rate"]), 2)

    return exchange_rate_dict

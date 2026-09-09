"""Read/rollback-only native order fences against actual isolated PostgreSQL.

Uses the fully refunded retained fixture 431. It never submits a provider request,
changes stock, dispatches another order, or sends an email.
"""
import asyncio
import json
import hashlib
import hmac
import time
from decimal import Decimal
import httpx
import logging
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from app.commerce_bridge import TENANT, SECRET, CommerceOrder, CommerceFulfilmentEvent, Order, Tenant, async_session_maker
from app.models import Product, OrderItem
from app.database import async_session_maker as native_session_maker
from app.api.v1 import orders as api
from app.services.commerce_order_ownership import commerce_order_id
from app.services.order_fulfillment import OrderFulfillmentService

logging.disable(logging.CRITICAL)

async def main():
    checks = []
    async def protected(db):
        return [await db.scalar(text(f"SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM {table} t")) for table in ['products','product_variants','orders','order_items','print_jobs','commerce_orders','commerce_fulfilment_events']]
    def check(name, ok):
        checks.append({'check': name, 'pass': bool(ok)})
        if not ok:
            raise AssertionError(name)
    async def denied(name, operation):
        try:
            await operation()
            check(name, False)
        except HTTPException as error:
            check(name, error.status_code == 409)
    async with native_session_maker() as db:
        before = await protected(db)
        check("native API regression uses its separate database connection", await db.scalar(text("SELECT current_user")) == "commerce")
        tenant = await db.get(Tenant, TENANT)
        mapping = await db.scalar(select(CommerceOrder).where(CommerceOrder.woo_order_id == 431))
        order = await db.scalar(select(Order).where(Order.id == UUID(mapping.batchivo_order_id)).options(selectinload(Order.items)))
        check('fixture431 is fully refunded and physically delivered', order.payment_status == 'REFUNDED' and order.delivered_at is not None and mapping.effects['refunded_pence'] == 2997)
        check('actual mapping identifies Woo order', await commerce_order_id(db, order) == 431)
        original = order.order_number
        order.order_number = 'A different display number'
        check('mapping remains authoritative after display rename', await commerce_order_id(db, order) == 431)
        order.order_number = original
        check('legacy order without commerce mapping remains native', await commerce_order_id(db, SimpleNamespace(id=uuid4(),order_number='LEGACY-FIXTURE')) is None)
        await denied('missing reserved Woo mapping fails closed', lambda: commerce_order_id(db, SimpleNamespace(id=uuid4(),order_number='WOO-TEST-MISSING')))
        service = OrderFulfillmentService(db, tenant)
        await denied('direct inventory validation cannot bypass ownership', lambda: service.validate_inventory(order))
        await denied('direct deduction cannot consume stock twice', lambda: service.deduct_inventory(order))
        await denied('direct reversal cannot restore dispatched stock', lambda: service.revert_inventory(order))
        await denied('native manual fulfil rejects competing stock writer', lambda: api.fulfill_order(order.id, db=db, tenant=tenant))
        await denied('native cancellation rejects competing terminal writer', lambda: api.cancel_order(order.id, api.CancelOrderRequest(), db=db, tenant=tenant))
        await denied('native refund requires Woo payment workflow', lambda: api.refund_order(order.id, api.RefundOrderRequest(), tenant=tenant, _=None, db=db))
        await denied('native resend does not send a duplicate customer message', lambda: api.resend_order_email(order.id, api.ResendEmailRequest(email_type='confirmation'), db=db, tenant=tenant))
        for field, value in [('status','processing'),('tracking_number','CHANGED'),('tracking_url','https://example.invalid/')]:
            await denied('generic update cannot bypass '+field+' ownership', lambda f=field,v=value: api.update_order(order.id, api.UpdateOrderRequest(**{f:v}), db=db, tenant=tenant))
        await denied('native ship uses durable refund guard', lambda: api.ship_order(order.id, api.ShipOrderRequest(), db=db, tenant=tenant))
        await denied('native delivery uses durable refund guard', lambda: api.deliver_order(order.id, db=db, tenant=tenant))
        # Exercise the unchanged legacy stock path inside a transaction rolled back below.
        product = Product(id=uuid4(), tenant_id=TENANT, sku='OWNERSHIP-'+uuid4().hex, name='Temporary native ownership fixture', units_in_stock=5, is_active=True)
        legacy = Order(id=uuid4(), tenant_id=TENANT, order_number='NATIVE-FIXTURE-'+uuid4().hex, status='processing', customer_email='fixture@example.invalid', customer_name='Fixture', shipping_address_line1='Fixture', shipping_city='Fixture', shipping_postcode='TE1 1ST', shipping_country='United Kingdom', shipping_method='Test', shipping_cost=Decimal('0'), subtotal=Decimal('2'), total=Decimal('2'), currency='GBP', payment_provider='test', payment_status='completed')
        legacy.items = [OrderItem(id=uuid4(), tenant_id=TENANT, product_id=product.id, product_sku=product.sku, product_name=product.name, quantity=2, unit_price=Decimal('1'), total_price=Decimal('2'))]
        db.add_all([product, legacy]); await db.flush()
        check('legacy native inventory validation still works', (await service.validate_inventory(legacy)).success)
        check('legacy native deduction still works', (await service.deduct_inventory(legacy)).success and product.units_in_stock == 3 and legacy.fulfilled_at is not None)
        check('legacy native reversal still works', (await service.revert_inventory(legacy)).success and product.units_in_stock == 5 and legacy.fulfilled_at is None)
        await db.rollback()
        check('all products variants orders items jobs mappings events unchanged', before == await protected(db))
    async with async_session_maker() as db:
        event = await db.scalar(select(CommerceFulfilmentEvent).where(CommerceFulfilmentEvent.woo_order_id == 431, CommerceFulfilmentEvent.version == 1))
        command = {'event_id':event.event_id,'order_id':431,'state':'shipped','tracking_number':event.payload['tracking_number'],'tracking_url':event.payload['tracking_url']}
        raw = json.dumps(command,separators=(',',':')).encode()
        check('retained signed dispatch command identity matches original', hashlib.sha256(raw).hexdigest() == event.command_sha256)
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',timeout=20) as client:
            stamp=str(int(time.time()));signature=hmac.new(SECRET,stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
            response=await client.post('/fulfilment/dispatch',content=raw,headers={'Content-Type':'application/json','X-MF-Timestamp':stamp,'X-MF-Signature':signature})
            check('signed HTTP dispatch still replays retained receipt after refactor',response.status_code==200 and response.json().get('status')=='duplicate')
        check('HTTP replay leaves all protected tables unchanged', before == await protected(db))
    print(json.dumps({'scope':'Actual native API/service calls and isolated PostgreSQL; refunded fixture431, no mocked persistence or payment calls','checks':checks,'failed':sum(not c['pass'] for c in checks)}))

asyncio.run(main())

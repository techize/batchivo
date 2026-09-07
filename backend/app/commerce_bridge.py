"""Isolated WooCommerce acceptance bridge using real Batchivo order/print-job models.

This service deliberately refuses production databases. Promotion requires a reviewed
production adapter release, not removal of this guard during testing.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import hmac
import json
import os
import sys
import time
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Index, Integer, String, Text, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

if os.environ.get('COMMERCE_ISOLATED') != 'true' or 'batchivo_commerce_test' not in os.environ.get('DATABASE_URL',''):
    raise RuntimeError('Commerce acceptance bridge requires an isolated test database')
from app.database import Base, engine, async_session_maker
from app.models import Product, ProductVariant, Tenant, Order, OrderItem, PrintJob, JobStatus
from app.models.base import UUIDMixin, TimestampMixin

TENANT=UUID(os.environ['COMMERCE_TENANT_ID'])
SECRET=os.environ['COMMERCE_BRIDGE_SECRET'].encode()

class CommerceReceipt(Base, UUIDMixin, TimestampMixin):
    __tablename__='commerce_receipts'
    event_id: Mapped[str]=mapped_column(String(64),unique=True)
    body_sha256: Mapped[str]=mapped_column(String(64))
    woo_order_id: Mapped[int]=mapped_column(Integer,index=True)
    outcome: Mapped[str]=mapped_column(String(32))

class CommerceOrder(Base, UUIDMixin, TimestampMixin):
    __tablename__='commerce_orders'
    woo_order_id: Mapped[int]=mapped_column(Integer,unique=True)
    batchivo_order_id: Mapped[str]=mapped_column(String(36))
    version: Mapped[int]=mapped_column(Integer)
    state: Mapped[str]=mapped_column(String(32))
    snapshot: Mapped[dict]=mapped_column(JSONB)
    effects: Mapped[dict]=mapped_column(JSONB,default=dict)

payment_identity_index=Index('commerce_orders_payment_unique', CommerceOrder.snapshot['payment_id'].astext, unique=True)

class Line(BaseModel):
    model_config=ConfigDict(extra='forbid')
    line_id: int=Field(gt=0)
    product_id: UUID
    variant_id: UUID|None=None
    sku: str=Field(min_length=1,max_length=100)
    name: str=Field(min_length=1,max_length=255)
    option: str=''
    quantity: int=Field(gt=0,le=1000)
    total_pence: int=Field(ge=0)

class Event(BaseModel):
    model_config=ConfigDict(extra='forbid')
    event_id: UUID
    order_id: int=Field(gt=0)
    version: int=Field(gt=0)
    state: str
    payment_id: str=Field(min_length=1,max_length=192)
    currency: str='GBP'
    subtotal_pence: int=Field(ge=0)
    shipping_pence: int=Field(ge=0)
    discount_pence: int=Field(ge=0)
    total_pence: int=Field(ge=0)
    lines: list[Line]=Field(min_length=1,max_length=100)
    customer: dict
    shipping: dict
    @model_validator(mode='after')
    def valid(self):
        if self.currency!='GBP' or self.state not in ['processing','completed','cancelled','refunded']:
            raise ValueError('Unsupported currency or state')
        if sum(x.total_pence for x in self.lines)+self.shipping_pence!=self.total_pence:
            raise ValueError('Line/shipping totals do not reconcile')
        return self

app=FastAPI(title='Batchivo isolated commerce acceptance',docs_url=None,redoc_url=None)

@app.get('/health')
async def health():
    async with engine.connect() as conn:await conn.execute(text('SELECT 1'))
    return {'status':'ok','environment':'isolated-test'}

async def verify_payment(event: Event):
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.get('https://connect.squareupsandbox.com/v2/payments/'+event.payment_id,
            headers={'Authorization':'Bearer '+os.environ['SQUARE_SANDBOX_ACCESS_TOKEN'],'Square-Version':'2026-01-22'})
    if r.status_code!=200:raise HTTPException(503,'Square sandbox payment verification unavailable')
    p=r.json()['payment']
    if p['status']!='COMPLETED' or p['amount_money']!={'amount':event.total_pence,'currency':'GBP'}:
        raise HTTPException(409,'Payment status or amount does not match order')
    if event.state=='refunded' and p.get('refunded_money',{}).get('amount',0)!=event.total_pence:
        raise HTTPException(409,'Full refund is not yet verified by Square')

@app.post('/events')
async def receive(request:Request):
    body=await request.body()
    if len(body)>256000:raise HTTPException(413,'Payload too large')
    stamp=request.headers.get('x-mf-timestamp','')
    if not stamp.isdigit() or abs(time.time()-int(stamp))>300:raise HTTPException(401,'Expired event signature')
    expected=hmac.new(SECRET,stamp.encode()+b'.'+body,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,request.headers.get('x-mf-signature','')):raise HTTPException(401,'Invalid event signature')
    try:event=Event.model_validate_json(body)
    except ValueError:raise HTTPException(422,'Invalid order snapshot')
    digest=hashlib.sha256(body).hexdigest()
    async with async_session_maker() as db,db.begin():
        # Payment lock prevents one captured payment being assigned to two orders.
        await db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,1))'),{'key':event.payment_id})
        reused=await db.scalar(select(CommerceOrder).where(CommerceOrder.snapshot['payment_id'].astext==event.payment_id,CommerceOrder.woo_order_id!=event.order_id))
        if reused:raise HTTPException(409,'Payment already belongs to another order')
        # Transaction-scoped lock serializes duplicate/new events for one order.
        await db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':event.order_id})
        prior=await db.scalar(select(CommerceReceipt).where(CommerceReceipt.event_id==str(event.event_id)))
        if prior:
            if prior.body_sha256!=digest:raise HTTPException(409,'Event ID reused with different data')
            return {'status':'duplicate','event_id':str(event.event_id)}
        mapping=await db.scalar(select(CommerceOrder).where(CommerceOrder.woo_order_id==event.order_id).with_for_update())
        if mapping and event.version<=mapping.version:
            db.add(CommerceReceipt(event_id=str(event.event_id),body_sha256=digest,woo_order_id=event.order_id,outcome='stale'))
            return {'status':'stale','event_id':str(event.event_id)}
        if mapping and mapping.state in ['cancelled','refunded'] and event.state in ['processing','completed']:
            raise HTTPException(409,'Cannot reopen terminal order through delayed payment event')
        if mapping:
            # Paid quantities and money cannot be rewritten by a later status event.
            old=mapping.snapshot;new=event.model_dump(mode='json')
            keys=['payment_id','currency','subtotal_pence','shipping_pence','discount_pence','total_pence']
            line_keys=['line_id','product_id','variant_id','sku','quantity','total_pence']
            def identity(lines):return sorted([tuple(str(line.get(k)) for k in line_keys) for line in lines])
            if any(old[k]!=new[k] for k in keys) or identity(old['lines'])!=identity(new['lines']):
                raise HTTPException(409,'Paid order changes require an explicit adjustment workflow')
        await verify_payment(event)
        if not mapping:
            if event.state not in ['processing','completed']:raise HTTPException(409,'Paid order must be reconciled before its terminal event')
            order=Order(tenant_id=TENANT,order_number=f'WOO-TEST-{event.order_id}',status='processing',
                customer_email=event.customer.get('email','test@example.invalid'),customer_name=event.customer.get('name','Test customer'),
                shipping_address_line1=event.shipping.get('address_1',''),shipping_address_line2=event.shipping.get('address_2',''),
                shipping_city=event.shipping.get('city',''),shipping_postcode=event.shipping.get('postcode',''),shipping_country='United Kingdom',
                shipping_method=event.shipping.get('method','Royal Mail'),shipping_cost=Decimal(event.shipping_pence)/100,
                subtotal=Decimal(event.subtotal_pence)/100,total=Decimal(event.total_pence)/100,discount_amount=Decimal(event.discount_pence)/100,
                currency='GBP',payment_provider='square-sandbox',payment_id=event.payment_id,payment_status='COMPLETED',
                confirmation_email_sent=False,internal_notes='Isolated WooCommerce acceptance order. Never dispatch to a real customer.')
            db.add(order);await db.flush();effects={'stock':[],'restored':False}
            for line in sorted(event.lines,key=lambda x:str(x.product_id)):
                product=await db.scalar(select(Product).where(Product.id==line.product_id,Product.tenant_id==TENANT).with_for_update())
                if not product or not product.is_active:raise HTTPException(409,'Unknown or inactive mapped product')
                variant=None
                if line.variant_id:
                    variant=await db.scalar(select(ProductVariant).where(ProductVariant.id==line.variant_id,ProductVariant.product_id==product.id,ProductVariant.tenant_id==TENANT,ProductVariant.is_active.is_(True)).with_for_update())
                    if not variant:raise HTTPException(409,'Invalid mapped variant')
                if line.sku!=(variant.sku if variant else product.sku):raise HTTPException(409,'SKU does not match source mapping')
                pto=variant.fulfilment_type=='print_to_order' if variant else product.print_to_order
                if not pto:
                    stock=variant or product
                    if stock.units_in_stock<line.quantity:raise HTTPException(409,'Insufficient Batchivo test stock')
                    stock.units_in_stock-=line.quantity
                    effects['stock'].append({'product_id':str(product.id),'variant_id':str(variant.id) if variant else None,'quantity':line.quantity})
                db.add(OrderItem(tenant_id=TENANT,order_id=order.id,product_id=product.id,product_sku=line.sku,product_name=(line.name+' '+line.option).strip()[:255],quantity=line.quantity,unit_price=Decimal(line.total_pence)/100/line.quantity,total_price=Decimal(line.total_pence)/100))
                if pto:db.add(PrintJob(tenant_id=TENANT,product_id=product.id,quantity=line.quantity,status=JobStatus.PENDING,reference=f'WOO-TEST-{event.order_id}:{line.line_id}',notes=json.dumps({'source':'woocommerce-test','variant_id':str(line.variant_id) if line.variant_id else None,'sku':line.sku,'option':line.option,'payment_id':event.payment_id})))
            mapping=CommerceOrder(woo_order_id=event.order_id,batchivo_order_id=str(order.id),version=event.version,state=event.state,snapshot=event.model_dump(mode='json'),effects=effects);db.add(mapping)
        else:
            order=await db.get(Order,UUID(mapping.batchivo_order_id));mapping.version=event.version;mapping.state=event.state;mapping.snapshot=event.model_dump(mode='json')
            if event.state in ['cancelled','refunded']:
                jobs=(await db.scalars(select(PrintJob).where(PrintJob.tenant_id==TENANT,PrintJob.reference.like(f'WOO-TEST-{event.order_id}:%')).with_for_update())).all()
                if any(j.status not in [JobStatus.PENDING,JobStatus.QUEUED,JobStatus.CANCELLED] for j in jobs):raise HTTPException(409,'Manufacturing already started; operator review required')
                for job in jobs:job.status=JobStatus.CANCELLED
                effects=dict(mapping.effects)
                if not effects.get('restored'):
                    for effect in effects.get('stock',[]):
                        cls=ProductVariant if effect['variant_id'] else Product
                        key=UUID(effect['variant_id'] or effect['product_id'])
                        stock=await db.scalar(select(cls).where(cls.id==key,cls.tenant_id==TENANT).with_for_update())
                        if not stock:raise HTTPException(409,'Stock mapping requires operator review')
                        stock.units_in_stock+=effect['quantity']
                    effects['restored']=True;mapping.effects=effects
                order.status=event.state
                if event.state=='refunded':order.payment_status='REFUNDED'
        db.add(CommerceReceipt(event_id=str(event.event_id),body_sha256=digest,woo_order_id=event.order_id,outcome='applied'))
    return {'status':'applied','event_id':str(event.event_id),'batchivo_order_id':mapping.batchivo_order_id}

async def seed(file):
    d=json.load(open(file))
    if d['_export']['tenant_id']!=str(TENANT):raise RuntimeError('Wrong source tenant')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(lambda sync: payment_identity_index.create(sync,checkfirst=True))
    async with async_session_maker() as db,db.begin():
        if not await db.get(Tenant,TENANT):db.add(Tenant(id=TENANT,name='Mystmere Forge — isolated commerce test',slug='mystmere-commerce-test',settings={}))
        await db.flush()
        for table in ['designers','categories','products','product_variants']:
            rows=d[table]
            for row in rows:
                row=dict(row)
                if table=='designers':row['notes']=None
                if table=='products':row['packaging_consumable_id']=None
                cols=[c.name for c in Base.metadata.tables[table].columns if c.name in row and not c.computed]
                names=','.join('"'+c+'"' for c in cols)
                # Only insert missing records; reseeding never resets stock or test orders.
                await db.execute(text(f'INSERT INTO {table} ({names}) SELECT {names} FROM json_populate_record(NULL::{table},CAST(:row AS json)) ON CONFLICT(id) DO NOTHING'),{'row':json.dumps(row)})
    print('Isolated Batchivo schema and catalogue seeded; no production customers, credentials or printers copied.')
if __name__=='__main__':asyncio.run(seed(sys.argv[1]))

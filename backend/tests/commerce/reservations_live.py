"""Explicit live isolated-DB/API acceptance; never collected as a mocked unit test."""
import asyncio, hashlib, hmac, json, os, time
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import httpx
from sqlalchemy import select, text, delete
from app.commerce_bridge import CommerceReservation, Product, PrintJob, Order, async_session_maker, TENANT

async def main():
    if os.environ.get('COMMERCE_ISOLATED')!='true':raise RuntimeError('Isolated database only')
    checks=[];owned=[]
    def check(name,passed):
        checks.append({'check':name,'pass':bool(passed)})
        if not passed:raise AssertionError(name)
    async with async_session_maker() as db:
        product=await db.scalar(select(Product).where(Product.tenant_id==TENANT,Product.is_active.is_(True),Product.print_to_order.is_(False),Product.units_in_stock>0,Product.units_in_stock<=500).order_by(Product.units_in_stock).limit(1))
        pto=await db.scalar(select(Product).where(Product.tenant_id==TENANT,Product.is_active.is_(True),Product.print_to_order.is_(True)).limit(1))
        if not product or not pto:raise RuntimeError('Finite and print-to-order catalogue fixtures required')
        before=await db.scalar(text("SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM products t"))
        order_count=await db.scalar(text('SELECT count(*) FROM orders'))
        job_count=await db.scalar(text('SELECT count(*) FROM print_jobs'))
    def payload(p,quantity):
        rid=str(uuid4());owned.append(rid)
        return {'reservation_id':rid,'order_id':900000000+int(uuid4().hex[:7],16),'total_pence':100,'currency':'GBP','lines':[{'line_id':1,'product_id':str(p.id),'variant_id':None,'sku':p.sku,'name':p.name,'quantity':quantity,'total_pence':100}]}
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',timeout=25) as client:
        async def post(path,data,bad=False):
            body=json.dumps(data,separators=(',',':')).encode();stamp=str(int(time.time()))
            signature=hmac.new(os.environ['COMMERCE_BRIDGE_SECRET'].encode(),stamp.encode()+b'.'+body,hashlib.sha256).hexdigest()
            return await client.post(path,content=body,headers={'Content-Type':'application/json','X-MF-Timestamp':stamp,'X-MF-Signature':'0'*64 if bad else signature})
        async def action(data,kind,order=None):return await post('/reservations/action',{'reservation_id':data['reservation_id'],'order_id':order or data['order_id'],'action':kind})
        try:
            a=payload(product,product.units_in_stock);b=payload(product,product.units_in_stock)
            check('unsigned reservation denied',(await post('/reservations',a,True)).status_code==401)
            replies=await asyncio.gather(post('/reservations',a),post('/reservations',b))
            check('two simultaneous requests for all finite stock yield exactly one winner',sorted(r.status_code for r in replies)==[200,409])
            winner=a if replies[0].status_code==200 else b;loser=b if winner is a else a
            check('identical reservation retry is idempotent',(await post('/reservations',winner)).status_code==200)
            changed=json.loads(json.dumps(winner));changed['total_pence']+=1
            check('reservation identity cannot be rewritten',(await post('/reservations',changed)).status_code==409)
            check('foreign order cannot release hold',(await action(winner,'release',winner['order_id']+1)).status_code==404)
            check('release before payment succeeds',(await action(winner,'release')).status_code==200)
            check('release retry is idempotent',(await action(winner,'release')).status_code==200)
            check('released reservation cannot start payment',(await action(winner,'begin_payment')).status_code==409)
            check('released units are available to waiting order',(await post('/reservations',loser)).status_code==200)
            check('begin payment marks durable pending hold',(await action(loser,'begin_payment')).json().get('state')=='payment_pending')
            check('begin payment retry is idempotent',(await action(loser,'begin_payment')).status_code==200)
            async with async_session_maker() as db,db.begin():
                row=await db.scalar(select(CommerceReservation).where(CommerceReservation.reservation_id==loser['reservation_id']))
                row.expires_at=datetime.now(timezone.utc)-timedelta(minutes=1)
            c=payload(product,product.units_in_stock)
            check('in-flight payment does not expire and oversell',(await post('/reservations',c)).status_code==409)
            check('in-flight payment cannot release without reconciliation',(await action(loser,'release')).status_code==409)
            # Test did not invoke Square: remove only this owned synthetic pending hold.
            async with async_session_maker() as db,db.begin():await db.execute(delete(CommerceReservation).where(CommerceReservation.reservation_id==loser['reservation_id']))
            check('next reservation succeeds once fixture hold removed',(await post('/reservations',c)).status_code==200)
            async with async_session_maker() as db,db.begin():
                row=await db.scalar(select(CommerceReservation).where(CommerceReservation.reservation_id==c['reservation_id']))
                row.expires_at=datetime.now(timezone.utc)-timedelta(minutes=1)
            check('expired pre-payment hold cannot begin payment',(await action(c,'begin_payment')).status_code==409)
            check('expired ID cannot be renewed silently',(await post('/reservations',c)).status_code==409)
            d=payload(product,product.units_in_stock)
            check('expired pre-payment hold frees capacity',(await post('/reservations',d)).status_code==200)
            await action(d,'release')
            duplicate=payload(product,product.units_in_stock)
            duplicate['lines'].append({**duplicate['lines'][0],'line_id':2})
            check('multiple basket lines cannot exceed shared stock',(await post('/reservations',duplicate)).status_code==409)
            e=payload(pto,1000);f=payload(pto,1000)
            replies=await asyncio.gather(post('/reservations',e),post('/reservations',f))
            check('print-to-order demand is not limited by physical stock',all(r.status_code==200 for r in replies))
            replacement=payload(pto,1000);replacement['order_id']=e['order_id']
            check('one order cannot hold two active attempts',(await post('/reservations',replacement)).status_code==409)
            async with async_session_maker() as db,db.begin():
                row=await db.scalar(select(CommerceReservation).where(CommerceReservation.reservation_id==e['reservation_id']))
                row.expires_at=datetime.now(timezone.utc)-timedelta(minutes=1)
            check('same order can replace expired pre-payment attempt',(await post('/reservations',replacement)).status_code==200)
            third=payload(pto,1000);third['order_id']=e['order_id']
            check('expired history cannot hide a newer active attempt',(await post('/reservations',third)).status_code==409)
            await action(replacement,'release')
            await action(e,'release');await action(f,'release')
            async with async_session_maker() as db:
                check('reservation tests do not decrement physical stock',before==await db.scalar(text("SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM products t")))
                check('no commerce orders created',order_count==await db.scalar(text('SELECT count(*) FROM orders')))
                check('no manufacturing triggered',job_count==await db.scalar(text('SELECT count(*) FROM print_jobs')))
        finally:
            async with async_session_maker() as db,db.begin():await db.execute(delete(CommerceReservation).where(CommerceReservation.reservation_id.in_(owned)))
    print(json.dumps({'scope':'Live signed HTTP to deployed isolated service and real PostgreSQL; no Square request. Explicit synthetic test holds removed. Checkout/payment commit integration not yet accepted.','checks':checks,'failed':sum(not c['pass'] for c in checks)}))

if __name__=='__main__':asyncio.run(main())

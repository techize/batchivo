"""Native manufacturing and reconciliation for the real browser sandbox order557."""
import asyncio, hashlib, hmac, json, logging, sys, time
from uuid import UUID
import httpx
from sqlalchemy import select, text
from app.commerce_bridge import CommerceOrder, CommerceFulfilmentEvent, Event, Order, PrintJob, JobStatus, Tenant, TENANT, SECRET, async_session_maker, verify_payment
from app.models.printer import Printer
from app.models.printer_connection import PrinterConnection
from app.services.print_queue_service import PrintQueueService
logging.disable(logging.CRITICAL)
ORDER=557
async def main():
 checks=[];stage=sys.argv[1];error=None
 def check(name,value):
  checks.append({'check':name,'pass':bool(value)})
  if not value:raise AssertionError(name)
 async def protected(db):
  return [await db.scalar(text(q)) for q in ["SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM products t","SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM product_variants t","SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM commerce_orders t WHERE woo_order_id<>557","SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM orders t WHERE id<>(SELECT batchivo_order_id::uuid FROM commerce_orders WHERE woo_order_id=557)","SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM print_jobs t WHERE reference NOT LIKE 'WOO-TEST-557:%'"]]
 async with async_session_maker() as db:
  before=await protected(db);mapping=await db.scalar(select(CommerceOrder).where(CommerceOrder.woo_order_id==ORDER))
  check('exact browser fixture with synthetic recipient',mapping and mapping.snapshot['customer']['email']=='native-fulfilment-20260908@example.invalid' and mapping.snapshot['total_pence']==2997)
  check('two distinct paid size variants',len(mapping.snapshot['lines'])==2 and {v['option'] for v in mapping.snapshot['lines']}=={'15cm','25cm'} and all(v['quantity']==1 for v in mapping.snapshot['lines']))
  check('print to order has no finite stock deductions',not mapping.effects['stock'])
  payment=await verify_payment(Event.model_validate(mapping.snapshot));check('independent Square sandbox captured £29.97',payment['status']=='COMPLETED' and payment['amount_money']['amount']==2997 and not payment.get('refund_ids'))
  jobs=(await db.scalars(select(PrintJob).where(PrintJob.tenant_id==TENANT,PrintJob.reference.like('WOO-TEST-557:%')))).all()
  check('two mapped manufacturing jobs retain option and payment',len(jobs)==2 and {json.loads(j.notes)['option'] for j in jobs}=={'15cm','25cm'} and all(j.quantity==1 and json.loads(j.notes)['payment_id']==mapping.snapshot['payment_id'] for j in jobs))
  if stage=='manufacture':
   tenant=await db.get(Tenant,TENANT);service=PrintQueueService(db,tenant)
   printer=await db.scalar(select(Printer).where(Printer.tenant_id==TENANT,Printer.name=='Commerce simulated printer 557'))
   if not printer:printer=Printer(tenant_id=TENANT,name='Commerce simulated printer 557',current_status='idle',is_active=True,notes='Isolated acceptance only. No physical printer connection.');db.add(printer);await db.commit();await db.refresh(printer)
   check('simulated printer has no hardware connection',await db.scalar(select(PrinterConnection).where(PrinterConnection.printer_id==printer.id)) is None)
   for job in jobs:
    current=await service.get_job(job.id)
    if current.status==JobStatus.PENDING:check(job.reference+' native queue',(await service.assign_to_printer(job.id,printer.id)).status==JobStatus.QUEUED)
    current=await service.get_job(job.id)
    if current.status==JobStatus.QUEUED:check(job.reference+' native start',(await service.start_printing(job.id)).status==JobStatus.PRINTING)
    current=await service.get_job(job.id)
    if current.status==JobStatus.PRINTING:check(job.reference+' native complete',(await service.complete_job(job.id)).status==JobStatus.COMPLETED)
   printer.is_active=False;await db.commit();check('simulated printer deactivated',not printer.is_active)
  elif stage in ['shipped','delivered']:
   order=await db.get(Order,UUID(mapping.batchivo_order_id));events=(await db.scalars(select(CommerceFulfilmentEvent).where(CommerceFulfilmentEvent.woo_order_id==ORDER).order_by(CommerceFulfilmentEvent.version))).all()
   check('native order state matches browser action',order.status==stage)
   check('manufacturing completion retained',all(j.status==JobStatus.COMPLETED for j in jobs))
   check('one immutable event per transition',len(events)==(1 if stage=='shipped' else 2) and [e.version for e in events]==list(range(1,len(events)+1)))
   check('tracking retained correctly',order.tracking_number=='TEST-557-NOT-A-PARCEL' and order.tracking_url=='https://test.mystmereforge.co.uk/order-lookup/')
   check('stock effects are not repeated at dispatch',not mapping.effects['stock'] and order.fulfilled_at is not None)
   command={'order_id':ORDER,'state':stage,'tracking_number':order.tracking_number if stage=='shipped' else '', 'tracking_url':order.tracking_url if stage=='shipped' else ''}
   async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',timeout=25) as client:
    async def send(payload,bad=False):
     raw=json.dumps(payload,separators=(',',':')).encode();stamp=str(int(time.time()));sig=hmac.new(SECRET,stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
     return await client.post('/fulfilment/operator',content=raw,headers={'Content-Type':'application/json','X-MF-Timestamp':stamp,'X-MF-Signature':'0'*64 if bad else sig})
    check('unauthenticated operator request denied',(await send(command,True)).status_code==401)
    r=await send(command);stamp=r.headers.get('x-mf-timestamp','');signature=hmac.new(SECRET,stamp.encode()+b'.'+r.content,hashlib.sha256).hexdigest()
    check('operator response signature verified',r.status_code==200 and hmac.compare_digest(signature,r.headers.get('x-mf-signature','')))
    check('identical native action replays durable receipt',r.json().get('ok') and r.json()['result']['status']=='duplicate')
    if stage=='shipped':
     r=await send({**command,'tracking_number':'CHANGED'});check('duplicate cannot rewrite tracking',r.json().get('ok') is False and r.json().get('code')==409)
  else:raise ValueError('Unsupported stage')
  check('all stock other orders and other jobs unchanged',before==await protected(db))
 print(json.dumps({'order_id':ORDER,'stage':stage,'checks':checks,'failed':sum(not c['pass'] for c in checks),'scope':'Real browser sandbox order; actual Square read, native queue, PostgreSQL and signed HTTP; simulated printer only'}))
asyncio.run(main())

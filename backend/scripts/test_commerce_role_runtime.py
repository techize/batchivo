"""Read-only live credential separation and reporting-channel acceptance."""
import asyncio,json,os
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import text
from app.commerce_bridge import async_session_maker, native_engine, TENANT
from app.services.commerce_database import verify_commerce_role
from app.services.commerce_sales_channel import commerce_sales_channel

async def main():
    checks=[]
    def check(name,value):
        checks.append({'check':name,'pass':bool(value)})
        if not value:raise AssertionError(name)
    async with async_session_maker() as db:
        identity=(await db.execute(text('SELECT current_user,session_user'))).one()
        check('actual commerce connection authenticates as dedicated role',tuple(identity)==('mf_commerce_test','mf_commerce_test'))
        channel=await commerce_sales_channel(db,TENANT,os.environ,True)
        check('new paid order assigned to configured storefront channel',await db.scalar(text("SELECT sales_channel_id FROM orders WHERE order_number='WOO-TEST-601'"))==channel)
        for name,config,tenant in [('missing production setting',{},TENANT),('invalid identifier',{'COMMERCE_SALES_CHANNEL_ID':'invalid'},TENANT),('other tenant',os.environ,UUID('00000000-0000-0000-0000-000000000001'))]:
            rejected=False
            try:await commerce_sales_channel(db,tenant,config,False)
            except HTTPException as error:rejected=error.status_code==503
            check(name+' rejected',rejected)
    async with native_engine.connect() as connection:
        rejected=False
        try:await connection.run_sync(verify_commerce_role)
        except RuntimeError:rejected=True
        check('native administrative credential rejected as commerce role',rejected)
        check('native engine retains separate original identity',await connection.scalar(text('SELECT current_user'))=='commerce')
    print(json.dumps({'checks':checks,'failed':0,'scope':'Read-only actual deployed PostgreSQL identities and order601 channel. No production or financial writes.'}))
asyncio.run(main())

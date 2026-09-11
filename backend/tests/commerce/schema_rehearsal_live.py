"""Rehearse additive DDL on real isolated PostgreSQL, rolling back every change."""
import asyncio,importlib.util,json,sys
from uuid import uuid4
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect,text
from app.commerce_bridge import RUNTIME,engine,CommerceReceipt,CommerceOrder,CommerceFulfilmentEvent,CommerceReservation

async def main():
 if not RUNTIME.isolated:raise RuntimeError('Schema rehearsal requires isolated PostgreSQL')
 spec=importlib.util.spec_from_file_location('commerce_schema',sys.argv[1]);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 schema='commerce_rehearsal_'+uuid4().hex
 checks=[]
 def check(name,value):checks.append({'check':name,'pass':bool(value)})
 async with engine.connect() as connection:
  transaction=await connection.begin()
  try:
   await connection.execute(text(f'CREATE SCHEMA {schema}'))
   await connection.execute(text(f'SET LOCAL search_path TO {schema}'))
   def apply(sync):
    with Operations.context(MigrationContext.configure(sync)):module.upgrade()
    inspector=inspect(sync)
    models=[CommerceReceipt,CommerceOrder,CommerceFulfilmentEvent,CommerceReservation]
    check('exactly four additive commerce tables',set(inspector.get_table_names(schema=schema))=={m.__tablename__ for m in models})
    for model in models:
     table=model.__table__;actual=inspector.get_columns(table.name,schema=schema)
     expected={c.name:(str(c.type.compile(dialect=sync.dialect)),c.nullable) for c in table.columns}
     found={c['name']:(str(c['type'].compile(dialect=sync.dialect)),c['nullable']) for c in actual}
     check(table.name+' column types and nullability match ORM',found==expected)
     check(table.name+' primary key matches ORM',inspector.get_pk_constraint(table.name,schema=schema)['constrained_columns']==['id'])
     expected_unique={tuple(c.name for c in constraint.columns) for constraint in table.constraints if constraint.__class__.__name__=='UniqueConstraint'}
     check(table.name+' uniqueness constraints match ORM',{tuple(c['column_names']) for c in inspector.get_unique_constraints(table.name,schema=schema)}==expected_unique)
     found_indexes={i['name']:bool(i['unique']) for i in inspector.get_indexes(table.name,schema=schema) if not i.get('duplicates_constraint')}
     check(table.name+' indexes match ORM',found_indexes=={i.name:bool(i.unique) for i in table.indexes})
   await connection.run_sync(apply)
   refused=False
   try:module.downgrade()
   except RuntimeError:refused=True
   check('destructive ledger downgrade refused',refused)
  finally:await transaction.rollback()
  check('temporary schema fully rolled back',await connection.scalar(text('SELECT NOT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=:schema)'),{'schema':schema}))
 report={'checks':checks,'failed':sum(not c['pass'] for c in checks),'scope':'Actual additive Alembic DDL on isolated PostgreSQL in a temporary schema; transaction rolled back. Production untouched.'}
 print(json.dumps(report))
 if report['failed']:raise SystemExit(1)
asyncio.run(main())

#!/usr/bin/env python3
import asyncio, os
import asyncpg

PG_DSN=os.getenv('PG_DSN','postgresql://exior:exior_local_only@127.0.0.1:5432/exior_contact')
BAD=(
    'request-a-quote','request_a_quote','get-a-quote','get_a_quote','quote',
    'start-a-project','start_a_project','project-brief','project_brief','brief',
    'work-with-us','work_with_us','hire-us','hire_us','get-started','get_started',
    'book-a-call','book_a_call','discovery-call','discovery_call'
)

async def main():
    pool=await asyncpg.create_pool(PG_DSN,min_size=1,max_size=2)
    async with pool.acquire() as c:
        await c.execute("ALTER TABLE outreach_queue ADD COLUMN IF NOT EXISTS qualification_reason TEXT")
        rows=await c.fetch("SELECT company_id,form_url FROM outreach_queue WHERE status='MESSAGE_READY'")
        q=[]
        for r in rows:
            u=(r['form_url'] or '').lower()
            hit=next((x for x in BAD if x in u),None)
            if hit: q.append((r['company_id'],f'wrong_inbound_sales_route:{hit}'))
        if q:
            await c.executemany("UPDATE outreach_queue SET status='QUARANTINED_WRONG_ROUTE',qualification_reason=$2,updated_at=now() WHERE company_id=$1 AND status='MESSAGE_READY'",q)
        print(f'QUARANTINED_WRONG_ROUTE={len(q)}')
        print('READY_REMAINING=',await c.fetchval("SELECT count(*) FROM outreach_queue WHERE status='MESSAGE_READY'"))
    await pool.close()

if __name__=='__main__': asyncio.run(main())
